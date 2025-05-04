import logging
import threading
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import uuid
from markdown_utils import markdown_to_html_fragment

from PyQt5.QtCore import QObject, pyqtSignal
from dotenv import load_dotenv
import google.generativeai as genai
import ollama # Still needed for potential future gatekeeper integration

# Project Imports
from config_manager import ConfigManager
from log_manager import LogManager
from context_loader import load_and_combine_context

class LLMController(QObject):
    """
    Manages interactions with Large Language Models (LLM), including initialization,
    prompt formatting, making requests, handling responses, and specific DM actions.
    """
    # --- Signals ---
    # Emitted when an LLM response is received
    response_received = pyqtSignal(str)
    # Emitted when LLM processing starts/stops
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    # Emitted on critical error during LLM setup or processing
    llm_error = pyqtSignal(str)
    # --- New Streaming Signals ---
    # Unique stream ID for each response
    stream_started = pyqtSignal(str)
    # Emits (stream_id, html_chunk)
    response_chunk_received = pyqtSignal(str, str)
    # Emits (stream_id, final_html)
    stream_finished = pyqtSignal(str, str)

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initializes the LLMController.

        Args:
            config_manager: The application's ConfigManager instance.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.config = config_manager
        self.app_logger = LogManager.get_app_logger()
        self.conv_logger = LogManager.get_conversation_logger()

        # LLM State
        self.chat_session = None
        self.ollama_client = None # Keep for potential future use
        self.gatekeeper_prompt_template = None
        self.main_prompt_template = None
        self.styling_guide_content = None
        self.manual_prompt_template = None
        self.is_processing = False

        # DM Action Parameters (mirrored from MainWindow original)
        self._pc_level = self.config.get("dm_actions.default_pc_level", 5)
        self._action_quantity = self.config.get("dm_actions.default_quantity", 1)

        # Initialization
        self._initialize_llms_and_prompts()

    # --- Properties for DM Action Params ---
    @property
    def pc_level(self) -> int:
        return self._pc_level

    @pc_level.setter
    def pc_level(self, value: int):
        if self._pc_level != value:
            self._pc_level = value
            self.config.set("dm_actions.default_pc_level", value)
            self.config.save() # Save immediately
            self.app_logger.info(f"LLMController: PC Level set to: {value}")

    @property
    def action_quantity(self) -> int:
        return self._action_quantity

    @action_quantity.setter
    def action_quantity(self, value: int):
        if self._action_quantity != value:
            self._action_quantity = value
            self.config.set("dm_actions.default_quantity", value)
            self.config.save() # Save immediately
            self.app_logger.info(f"LLMController: Action Quantity set to: {value}")

    # --- Initialization --- (Extracted from MainWindow original)
    def _initialize_llms_and_prompts(self):
        """Initializes LLMs, loads prompts, styling guide, and potentially past session."""
        self.app_logger.info("Initializing LLM Systems from Config...")

        project_root = Path(__file__).parent.parent
        gatekeeper_prompt_path_str = self.config.get("paths.gatekeeper_prompt", "prompts/gatekeeper_prompt.md")
        main_prompt_path_str = self.config.get("paths.main_prompt", "prompts/dm_assistant_prompt.md")
        campaign_config_path_str = self.config.get("paths.campaign_config", "source_materials/default_campaign.json")
        style_guide_path_str = "prompts/markdown_styling_guide.md"
        manual_prompt_path_str = "prompts/dm_manual_input_prompt.md"

        gatekeeper_prompt_path = project_root / gatekeeper_prompt_path_str
        main_prompt_path = project_root / main_prompt_path_str
        campaign_config_path = project_root / campaign_config_path_str
        style_guide_path = project_root / style_guide_path_str
        manual_prompt_path = project_root / manual_prompt_path_str

        # --- Load Prompts & Style Guide (CRITICAL - No try/except) ---
        if main_prompt_path.is_file():
            self.main_prompt_template = main_prompt_path.read_text(encoding="utf-8")
            self.app_logger.info("Main prompt template loaded.")
        else:
            error_msg = f"Main prompt file not found: {main_prompt_path}. Application cannot continue."
            self.app_logger.critical(f"CRITICAL ERROR: {error_msg}")
            self.llm_error.emit(error_msg) # Emit error signal
            # Cannot proceed without prompt
            return # Or raise an exception if preferred, but rules say no try/except

        if gatekeeper_prompt_path.is_file():
            self.gatekeeper_prompt_template = gatekeeper_prompt_path.read_text(encoding="utf-8")
            self.app_logger.info("Gatekeeper prompt loaded.")
        else:
            # Gatekeeper might be optional? Log warning for now.
            self.app_logger.warning(f"Gatekeeper prompt file not found: {gatekeeper_prompt_path}. Gatekeeper functionality disabled.")
            self.gatekeeper_prompt_template = None

        if style_guide_path.is_file():
            self.styling_guide_content = style_guide_path.read_text(encoding="utf-8")
            self.app_logger.info("Markdown styling guide loaded successfully.")
        else:
            error_msg = f"Markdown styling guide not found at {style_guide_path}. Application cannot continue."
            self.app_logger.critical(f"CRITICAL ERROR: {error_msg}")
            self.styling_guide_content = None
            self.llm_error.emit(error_msg) # Emit error signal
            return # Cannot proceed without style guide

        if manual_prompt_path.is_file():
            self.manual_prompt_template = manual_prompt_path.read_text(encoding="utf-8")
            self.app_logger.info("Manual DM prompt template loaded.")
        else:
            self.app_logger.warning(f"Manual DM prompt template not found at {manual_prompt_path}. Manual queries disabled.")

        # Initialize Ollama Client (Currently Skipped in original - keep logic)
        # ollama_host = self.config.get("servers.ollama_host", "http://localhost:11434")
        # self.ollama_client = ollama.Client(host=ollama_host)
        # self.ollama_client.list() # Verify connection
        self.ollama_client = None
        self.app_logger.info("Ollama client initialization skipped (as per original logic).")

        # --- Load History / Default Context ---
        initial_history = self._load_previous_session_history(LogManager.CONVERSATION_LOG_FILENAME)
        if not initial_history:
            self.app_logger.info("Loading default initial context for LLM.")
            initial_context = load_and_combine_context(str(campaign_config_path))
            if not initial_context:
                self.app_logger.warning(f"Warning: Failed to load context from {campaign_config_path}. Using fallback.")
                initial_context = "No initial context provided."
            else:
                 self.app_logger.info(f"Loaded initial context from {campaign_config_path}")
            initial_history = [
                {'role': 'user', 'parts': [initial_context]},
                {'role': 'model', 'parts': ["Okay, context loaded."]}
            ]

        # --- Initialize Gemini LLM (No try/except) ---
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            error_msg = "Google API Key not found in environment variables."
            self.app_logger.error(f"ERROR: {error_msg}")
            self.chat_session = None
            self.llm_error.emit(error_msg)
            return

        llm_model_name = self.config.get("general.llm_model_name", "gemini-1.5-flash")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(llm_model_name)

        self.chat_session = model.start_chat(history=initial_history)
        self.app_logger.info(f"LLM chat session started with model: {llm_model_name}. History length: {len(initial_history)}")


    def _load_previous_session_history(self, log_filename) -> List[Dict[str, Any]]:
        """Loads chat history from a .jsonl file."""
        initial_history = []
        session_log_file_path = Path(f"{log_filename}.jsonl")
        if session_log_file_path.exists():
            self.app_logger.info(f"Found previous session log: {session_log_file_path}, attempting to load history.")
            # Read file line by line without outer try/except
            with open(session_log_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    stripped_line = line.strip()
                    if not stripped_line: continue # Skip empty lines

                    # Parse JSON without try/except
                    log_entry = json.loads(stripped_line)
                    role = log_entry.get("role")
                    content = log_entry.get("content")

                    if role and content:
                        gemini_role = "model" if role == "assistant" else "user"
                        initial_history.append({'role': gemini_role, 'parts': [content]})
                    else:
                         self.app_logger.warning(f"Skipping invalid log line {line_num} (missing role/content): {stripped_line}")

            if initial_history:
                self.app_logger.info(f"Successfully loaded {len(initial_history)} entries from previous session.")
            else:
                 self.app_logger.info("Previous session log was empty or contained no valid entries.")
        else:
             self.app_logger.info("No previous session log found.")
        return initial_history

    # --- Gatekeeper Logic (Extracted - Currently Bypassed) ---
    def _run_gatekeeper_check(self, text_chunk: str) -> bool:
        """Checks if the text chunk is ready for the main LLM using the gatekeeper."""
        self.app_logger.info("Gatekeeper check is currently BYPASSED.")
        return True # Unconditionally proceed

        # --- Original Gatekeeper Logic --- (Keep for reference)
        # self.app_logger.info("Checking gatekeeper...")
        # if not self.ollama_client or not self.gatekeeper_prompt_template:
        #     self.app_logger.warning("Warning: Ollama gatekeeper client or template not ready. Assuming chunk IS ready.")
        #     return True # Proceed if gatekeeper isn't configured
        #
        # gatekeeper_prompt_formatted = self.gatekeeper_prompt_template.format(accumulated_chunk=text_chunk)
        # self.app_logger.debug(f"Gatekeeper Prompt: {gatekeeper_prompt_formatted[:100]}...")
        # gatekeeper_model = self.config.get("general.gatekeeper_model", "mistral:latest")
        # # No try/except for the generate call
        # response = self.ollama_client.generate(
        #     model=gatekeeper_model,
        #     prompt=gatekeeper_prompt_formatted,
        #     stream=False,
        #     options={"temperature": 0.2}
        # )
        # gatekeeper_decision_raw = response.get("response", "").strip()
        # gatekeeper_decision = gatekeeper_decision_raw.upper()
        # self.app_logger.info(f"Gatekeeper Response - Raw: '{gatekeeper_decision_raw}', Decision: {gatekeeper_decision}")
        # return gatekeeper_decision == "YES"

    # --- Main Processing Logic --- (Slot to connect to TranscriptionController.final_chunk_ready)
    def process_final_chunk(self, chunk_text: str):
        """Processes a finalized text chunk, runs gatekeeper, logs, and triggers LLM if ready."""
        self.app_logger.debug(f"Received final chunk for processing: {chunk_text[:80]}...")
        if self.is_processing:
            self.app_logger.info("LLM is currently processing. Chunk queued implicitly (or needs explicit queue).")
            # TODO: Decide if an explicit queue is needed here if chunks arrive while processing
            return

        # --- Run Gatekeeper --- (Currently bypassed)
        is_ready = self._run_gatekeeper_check(chunk_text)

        if is_ready:
            self.app_logger.info("Proceeding to LLM (Gatekeeper Bypassed or Indicated Ready).")
            # --- Log User Input before sending ---
            user_log_entry = {"role": "USER", "content": chunk_text}
            # No try/except for logging
            log_line = json.dumps(user_log_entry)
            self.conv_logger.info(log_line)
            self.app_logger.info(f"Logged final USER content (len: {len(chunk_text)}) to conversation log.")
            # -------------------------------------
            # Trigger LLM with the finalized chunk
            self._trigger_llm_request_internal(chunk_text)
        else:
             # This branch should not be reached while gatekeeper is bypassed
            self.app_logger.info("Gatekeeper indicates chunk is NOT ready. Accumulating further.")

    # --- LLM Request Triggering --- (Internal method)
    def _trigger_llm_request_internal(self, text_to_send: str, is_dm_action: bool = False):
        """Internal method to format prompt and start the LLM worker thread."""
        if not self.chat_session or not self.main_prompt_template:
            error_msg = "LLM session or main prompt template not ready."
            self.app_logger.error(f"ERROR: {error_msg}")
            self.llm_error.emit(error_msg)
            # Cannot proceed
            return

        self.is_processing = True
        self.processing_started.emit() # Signal processing start

        # --- Format Prompt ---
        # If it's not a DM action, use the main template format
        if not is_dm_action:
            formatted_prompt = self.main_prompt_template.format(transcript_chunk=text_to_send)
        else:
            # For DM actions, the text_to_send is already the formatted prompt
            formatted_prompt = text_to_send

        # --- Append Styling Guide --- 
        if self.styling_guide_content:
            formatted_prompt += "\n\n---\n**Markdown Styling Instructions:**\n" + self.styling_guide_content

        self.app_logger.debug(f"Formatted prompt for LLM: {formatted_prompt[:200]}...")
        self.app_logger.info(f"Starting LLM worker thread...")
        try:
            history_len = len(self.chat_session.history)
            self.app_logger.info(f"Current chat history length before sending: {history_len}")
        except Exception as e:
            # Log warning but continue if history access fails
            self.app_logger.warning(f"Could not determine chat history length: {e}")

        # Generate a unique stream ID for this request
        stream_id = uuid.uuid4().hex[:8]

        # --- Worker Thread --- 
        worker_thread = threading.Thread(
            target=self._llm_worker_func,
            args=(formatted_prompt, stream_id),
            daemon=True
        )
        worker_thread.start()

    # --- LLM Worker Function --- 
    def _llm_worker_func(self, prompt_to_send: str, stream_id: str):
        """Worker function to interact with the LLM API in *streaming* mode."""
        self.app_logger.info(f"LLM Worker [{stream_id}]: Sending formatted prompt (streaming)...")

        # Emit stream_started BEFORE the first chunk arrives so the UI can prepare.
        self.stream_started.emit(stream_id)

        # Critical API call – allow natural exception propagation (no try/except)
        gemini_stream = self.chat_session.send_message(prompt_to_send, stream=True)

        accumulated_markdown = ""
        for chunk in gemini_stream:
            if not hasattr(chunk, "text"):
                self.app_logger.warning(
                    f"LLM Worker [{stream_id}]: Received non-text chunk of type {type(chunk)}; skipping."
                )
                continue
            chunk_text: str = chunk.text
            accumulated_markdown += chunk_text
            # Convert streaming chunk markdown to HTML fragment for immediate display
            html_fragment = markdown_to_html_fragment(chunk_text)
            # Emit chunk to UI
            self.response_chunk_received.emit(stream_id, html_fragment)

        # After streaming completes, convert full markdown to HTML
        final_html = markdown_to_html_fragment(accumulated_markdown)
        self.stream_finished.emit(stream_id, final_html)

        # --- Log Assistant Response ---
        assistant_log_entry = {"role": "ASSISTANT", "content": accumulated_markdown}
        log_line = json.dumps(assistant_log_entry)
        self.conv_logger.info(log_line)
        self.app_logger.info(
            f"Logged ASSISTANT response for stream {stream_id} (len: {len(accumulated_markdown)})."
        )

        # Note: We deliberately do NOT emit the legacy response_received signal to avoid
        # duplicate rendering; the streaming signals already handled UI updates.

        # --- Update State ---
        self.is_processing = False
        self.processing_finished.emit()  # Signal processing end

    # --- DM Action Triggering --- (Public method called by MainWindow/UI)
    def trigger_dm_action(self, prompt_filename: str):
        """Loads, formats, logs, and triggers a specific DM action prompt."""
        self.app_logger.info(f"Attempting to trigger DM action: {prompt_filename}")

        if self.is_processing:
            self.app_logger.warning("Cannot trigger DM action: LLM is already processing.")
            # Optionally emit a signal or return a status to inform UI
            return

        project_root = Path(__file__).parent.parent
        prompt_path = project_root / "prompts" / prompt_filename

        if not prompt_path.is_file():
            error_msg = f"DM action prompt file not found: {prompt_path}"
            self.app_logger.error(error_msg)
            self.llm_error.emit(error_msg)
            return

        # --- Read, Format, Log, Trigger (No try/except) ---
        prompt_template = prompt_path.read_text(encoding="utf-8")
        formatted_action_prompt = prompt_template.format(
            quantity=self.action_quantity, # Use property
            pc_level=self.pc_level        # Use property
        )
        # Note: Styling guide is appended within _trigger_llm_request_internal

        self.app_logger.debug(f"Formatted DM Action Prompt (before style guide): {formatted_action_prompt[:150]}...")

        # --- Log User Request for DM Action ---
        # Combine filename info with the formatted prompt for logging context
        log_content = f"[DM Action Request: {prompt_filename}]\n{formatted_action_prompt}"
        user_log_entry = {"role": "USER", "content": log_content}
        log_line = json.dumps(user_log_entry)
        self.conv_logger.info(log_line)
        self.app_logger.info(f"Logged DM Action USER request to conversation log.")
        # --------------------------------------

        # Trigger internal request, marking it as a DM action
        self._trigger_llm_request_internal(formatted_action_prompt, is_dm_action=True)

    # ------------------------------------------------------------------
    # Public API for manual DM prompts
    # ------------------------------------------------------------------
    def process_manual_dm_prompt(self, raw_text: str) -> None:  # noqa: D401
        """Wrap *raw_text* in the manual prompt template and send to LLM."""
        if not self.manual_prompt_template:
            self.app_logger.error("Manual prompt template not loaded; ignoring manual query.")
            return
        wrapped_prompt = self.manual_prompt_template.replace("{{DM_QUERY}}", raw_text)
        self._trigger_llm_request_internal(wrapped_prompt, is_dm_action=False) 