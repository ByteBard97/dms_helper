import sys
import json # Import json library
import queue # Import queue instead of deque
import threading # Added for LLM worker
import time      # Added for LLM worker simulation (will be removed)
import os        # Added for API key
import logging   # Keep import for potential direct use if needed elsewhere
from dotenv import load_dotenv # Added for API key
import google.generativeai as genai # Added for Gemini
import ollama # Added for gatekeeper
from pathlib import Path # Added for prompt file path
from typing import List, Dict, Any

# Import the LogManager
from log_manager import LogManager

# Get logger instance (REMOVED - Use LogManager static methods)
# logger = logging.getLogger("dms_helper")

# Import the markdown conversion utility AND the CSS string
from markdown_utils import markdown_to_html_fragment, DND_CSS

# Project imports (Ensure these are accessible)
from context_loader import load_and_combine_context # Assuming context needed
from transcript_accumulator import TranscriptAccumulator # Added
from config_manager import ConfigManager # Import the new manager
# Import the transcription client directly - ImportError will propagate if missing
from whisper_live_client.client import TranscriptionClient

# Constants are now managed by ConfigManager

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QHBoxLayout, QLabel, QTextEdit, QSizePolicy, QCheckBox,
    QSplitter, QSpinBox # <<< Added QSpinBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl, QMetaObject, Q_ARG, pyqtSignal, QObject
from PyQt5 import QtCore # Add missing import
from PyQt5.QtGui import QPalette, QColor

class MainWindow(QMainWindow):
    # Define custom signals
    transcription_received = pyqtSignal(list)
    llm_response_received = pyqtSignal(str) # Signal for LLM response
    intermediate_transcription_updated = pyqtSignal(str) # <<< New signal for right pane updates
    
    def __init__(self):
        super().__init__()
        # Get logger instances from LogManager - DO THIS EARLY
        self.app_logger = LogManager.get_app_logger()
        self.conv_logger = LogManager.get_conversation_logger()
        self.raw_transcript_logger = LogManager.get_raw_transcript_logger()
        self.app_logger.info("Initializing MainWindow...") # Use LogManager

        # Initialize Config Manager FIRST
        self.config = ConfigManager() 

        self.setWindowTitle("D&D Helper Assistant")
        self.setGeometry(100, 100, 1000, 700) # Slightly wider default size for side-by-side

        # LLM, Gatekeeper, Accumulator and State Initialization
        self.chat_session = None
        self.ollama_client = None
        self.gatekeeper_prompt_template = None
        self.main_prompt_template = None # Add main template reference
        self.accumulator = TranscriptAccumulator() # Initialize accumulator
        self.initialize_llm_and_gatekeeper()
        
        # --- Separate Queues --- 
        self.segment_queue = queue.Queue() # For TranscriptionClient -> Monitor Thread
        self.chunk_queue = queue.Queue()   # For Handler -> Processing Logic
        # -----------------------
        
        self.is_llm_processing = False 
        # Load initial checkbox state from config
        self.show_user_speech = self.config.get("ui_settings.show_user_speech", True)
        LogManager.get_app_logger().info(f"Initial 'Show User Speech' state: {self.show_user_speech}") # Use LogManager
        
        # Transcription client and thread references
        self.transcription_client = None
        self.transcription_thread = None
        self.queue_monitor_stop_event = threading.Event()
        self.queue_monitor_thread = None

        self.settled_user_text = "" # <<< Add state for settled text

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Splitter for Side-by-Side View ---
        self.splitter = QSplitter(Qt.Horizontal) # Horizontal splitter

        # --- Left Pane: LLM Output Display (QWebEngineView) ---
        self.output_display = QWebEngineView()
        # self.output_display.setReadOnly(True) # Not applicable to QWebEngineView
        self.output_display.settings().setAttribute(
            self.output_display.settings().WebAttribute.WebGLEnabled, False
        ) # Disable WebGL for slightly less resource usage if not needed
        self.output_display.settings().setAttribute(
            self.output_display.settings().WebAttribute.PluginsEnabled, False
        ) # Disable plugins
        # self.output_display.setOpenExternalLinks(True) # Default behavior for web view

        # --- Load Initial HTML Structure with CSS --- 
        # Note: background color now handled by CSS within body/html
        self.initial_html_structure = """
<!DOCTYPE html>
<html>
<head>
<meta charset=\"UTF-8\">
<link rel=\"stylesheet\" href=\"css/dnd_style.css\">
</head>
<body>
    <h1>D&D Assistant Log</h1> 
    <p>LLM Suggestions will appear here...</p>
    <hr>
</body>
</html>
"""
        # Use setHtml with a base URL (important for resolving relative paths if any)
        self.output_display.setHtml(self.initial_html_structure, baseUrl=QUrl("file:///"))
        # --------------------------------------------
        
        self.splitter.addWidget(self.output_display) # Add to splitter (left)

        # --- Right Pane: User Speech Display (QTextEdit) ---
        self.user_speech_display = QTextEdit()
        self.user_speech_display.setReadOnly(True)
        self.user_speech_display.setPlaceholderText("Transcribed user speech will appear here...")
        # Optional: Set font size or style if desired
        # font = self.user_speech_display.font()
        # font.setPointSize(10) 
        # self.user_speech_display.setFont(font)
        self.splitter.addWidget(self.user_speech_display) # Add to splitter (right)

        # --- Add Splitter to Main Layout ---
        self.main_layout.addWidget(self.splitter) 

        # --- Set initial visibility of right pane ---
        self.user_speech_display.setVisible(self.show_user_speech)

        # --- Set initial splitter sizes (e.g., 50/50 or adjust as needed) ---
        # Provide large numbers; Qt will distribute proportionally
        self.splitter.setSizes([500, 500]) 

        # --- Button Layout ---
        self.button_layout = QHBoxLayout() # Horizontal layout for buttons

        # Placeholder buttons
        self.start_button = QPushButton("Start Listening")
        self.stop_button = QPushButton("Stop Listening")
        
        # Test button for rendering
        self.test_render_button = QPushButton("Test Render")
        self.test_render_button.clicked.connect(self.test_markdown_render)

        # Add a new button for appending second markdown
        self.append_second_button = QPushButton("Append Second Markdown")
        self.append_second_button.clicked.connect(self.append_second_markdown)

        # --- Add Flush Accumulator Button ---
        self.flush_button = QPushButton("Flush Accumulator")
        # -----------------------------------

        self.user_speech_checkbox = QCheckBox("Show User Speech")
        self.user_speech_checkbox.setChecked(self.show_user_speech)
        self.user_speech_checkbox.stateChanged.connect(self.on_user_speech_checkbox_changed)

        # --- Add SpinBox for min_sentences ---
        self.min_sentences_label = QLabel("Min Sentences:")
        self.min_sentences_spinbox = QSpinBox()
        self.min_sentences_spinbox.setMinimum(1)
        self.min_sentences_spinbox.setMaximum(10) # Or a higher reasonable value
        # Initialize with the value from the accumulator instance
        self.min_sentences_spinbox.setValue(self.accumulator.min_sentences) 
        # ------------------------------------

        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addStretch() # Add spacer
        self.button_layout.addWidget(self.test_render_button)
        self.button_layout.addWidget(self.append_second_button)
        self.button_layout.addWidget(self.user_speech_checkbox)
        # Add the new widgets to the layout
        self.button_layout.addWidget(self.min_sentences_label)
        self.button_layout.addWidget(self.min_sentences_spinbox)
        self.button_layout.addWidget(self.flush_button) # Add flush button
        
        # Add button layout to main layout
        self.main_layout.addLayout(self.button_layout)

        # Connect signals to slots (implement actual functions later)
        # self.start_button.clicked.connect(self.start_listening)
        # self.stop_button.clicked.connect(self.stop_listening)

        # Connect the start button
        self.start_button.clicked.connect(self.start_audio_processing)
        # Initially disable the stop button
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_audio_processing)

        # Connect the custom signal to the handler slot
        self.transcription_received.connect(self.handle_transcription_result)
        self.llm_response_received.connect(self.handle_llm_response) # Connect LLM signal
        self.intermediate_transcription_updated.connect(self.update_user_speech_pane) # <<< Connect new signal
        # Connect spinbox signal
        self.min_sentences_spinbox.valueChanged.connect(self.on_min_sentences_changed)
        # Connect flush button signal
        self.flush_button.clicked.connect(self.on_flush_accumulator_clicked)
        # ----------------------------------------------

        LogManager.get_app_logger().info("MainWindow initialization complete.") # Use LogManager

    def initialize_llm_and_gatekeeper(self):
        """Initializes LLMs, loads prompts, accumulator, and potentially past session."""
        app_logger = LogManager.get_app_logger()
        app_logger.info("Initializing Systems from Config...")

        # Get paths from config
        project_root = Path(__file__).parent.parent
        gatekeeper_prompt_path_str = self.config.get("paths.gatekeeper_prompt", "prompts/gatekeeper_prompt.md")
        main_prompt_path_str = self.config.get("paths.main_prompt", "prompts/dm_assistant_prompt.md")
        campaign_config_path_str = self.config.get("paths.campaign_config", "source_materials/default_campaign.json")

        gatekeeper_prompt_path = project_root / gatekeeper_prompt_path_str
        main_prompt_path = project_root / main_prompt_path_str
        campaign_config_path = project_root / campaign_config_path_str

        # Load prompts (Main and Gatekeeper)
        if main_prompt_path.is_file():
            self.main_prompt_template = main_prompt_path.read_text(encoding="utf-8")
            app_logger.info("Main prompt template loaded.")
        else:
            app_logger.error(f"ERROR: Main prompt file not found: {main_prompt_path}")
            self.main_prompt_template = "{transcript_chunk}"
            app_logger.warning("Warning: Using fallback main prompt.")

        if gatekeeper_prompt_path.is_file():
            self.gatekeeper_prompt_template = gatekeeper_prompt_path.read_text(encoding="utf-8")
            app_logger.info("Gatekeeper prompt loaded.")
        else:
            app_logger.error(f"ERROR: Gatekeeper prompt file not found: {gatekeeper_prompt_path}")
            self.gatekeeper_prompt_template = "Context: {accumulated_chunk}... Respond ONLY YES or NO."
            app_logger.warning("Warning: Using fallback gatekeeper prompt.")

        # Initialize Ollama Client
        # ollama_host = self.config.get("servers.ollama_host", "http://localhost:11434")
        # try:
        #     self.ollama_client = ollama.Client(host=ollama_host)
        #     self.ollama_client.list() # Verify connection
        #     app_logger.info(f"Ollama client initialized and connection verified for host: {ollama_host}")
        # except Exception as e:
        #     app_logger.error(f"Failed to initialize or connect to Ollama client at {ollama_host}: {e}")
        #     self.ollama_client = None
        self.ollama_client = None # Explicitly set to None since we are skipping init

        # --- Attempt to load previous session history --- 
        initial_history = []
        session_log_file_path = Path(f"{LogManager.CONVERSATION_LOG_FILENAME}.jsonl")
        if session_log_file_path.exists():
            app_logger.info(f"Found previous session log: {session_log_file_path}, attempting to load history.")
            try:
                with open(session_log_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            role = log_entry.get("role")
                            content = log_entry.get("content")
                            if role and content:
                                # Map role for Gemini (user/model)
                                gemini_role = "model" if role == "assistant" else "user"
                                initial_history.append({'role': gemini_role, 'parts': [content]})
                            else:
                                 app_logger.warning(f"Skipping invalid log line (missing role/content): {line.strip()}")
                        except json.JSONDecodeError:
                            app_logger.warning(f"Skipping invalid JSON line: {line.strip()}")
                if initial_history:
                    app_logger.info(f"Successfully loaded {len(initial_history)} entries from previous session.")
                else:
                     app_logger.info("Previous session log was empty or contained no valid entries.")
            except Exception as e:
                app_logger.error(f"Error reading or parsing session log file {session_log_file_path}: {e}", exc_info=True)
                initial_history = [] # Fallback to empty history on error
        else:
             app_logger.info("No previous session log found.")

        # --- If history loading failed or no previous session, load default context --- 
        if not initial_history:
            app_logger.info("Loading default initial context for LLM.")
            initial_context = load_and_combine_context(str(campaign_config_path))
            if not initial_context:
                app_logger.warning(f"Warning: Failed to load context from {campaign_config_path}. Using fallback.")
                initial_context = "No initial context provided."
            else:
                 app_logger.info(f"Loaded initial context from {campaign_config_path}")
            # Default introductory turn
            initial_history = [
                {'role': 'user', 'parts': [initial_context]},
                {'role': 'model', 'parts': ["Okay, context loaded."]}
            ]

        # Initialize Gemini LLM
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            app_logger.error("ERROR: Google API Key not found...")
            self.chat_session = None
            return

        llm_model_name = self.config.get("general.llm_model_name", "gemini-1.5-flash")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(llm_model_name)

        # Start chat session using the prepared initial_history (either loaded or default)
        try:
            self.chat_session = model.start_chat(history=initial_history)
            app_logger.info(f"LLM chat session started with model: {llm_model_name}. History length: {len(initial_history)}")
        except Exception as e:
            app_logger.error(f"ERROR: Failed to start Gemini chat session: {e}", exc_info=True)
            self.chat_session = None

    def append_markdown_output(self, md_text: str):
        """Converts Markdown text to HTML fragment and appends it to the web view."""
        LogManager.get_app_logger().debug("Appending markdown output to display.") # Use LogManager
        html_fragment = markdown_to_html_fragment(md_text)
        
        # --- DEBUG: Print the generated HTML fragment (can keep for now) ---
        LogManager.get_app_logger().debug("--- Generated HTML Fragment ---") # Use LogManager
        LogManager.get_app_logger().debug(html_fragment) # Use LogManager
        LogManager.get_app_logger().debug("-------------------------------") # Use LogManager
        # ---------------------------------------------
        
        # Safely encode the HTML fragment as a JSON string
        safe_html_fragment = json.dumps(html_fragment)

        # --- Logic to append fragment to QWebEngineView --- 
        script = f"""
        var body = document.body;
        var newContent = document.createElement('div'); 
        // Assign the JSON string (which is already correctly escaped for JS)
        newContent.innerHTML = {safe_html_fragment};
        // Append all children of the new div to the body
        while (newContent.firstChild) {{
            body.appendChild(newContent.firstChild);
        }}
        window.scrollTo(0, document.body.scrollHeight);
        """
        self.output_display.page().runJavaScript(script)

    def test_markdown_render(self):
        """Callback for the test render button."""
        LogManager.get_app_logger().info("Test Render button clicked.") # Use LogManager
        # Updated sample markdown with HTML for stat block
        sample_markdown = """# Session Notes: The Whispering Caves

## Party Members
*   **Gimli Stonehand** - *Dwarf Fighter* (Level 5) - Currently low on HP!
*   *Elara Meadowlight* - **Elf Ranger** (Level 5) - Used `Hunter's Mark` last turn.
*   [Zaltar the Mysterious](https://example.com/character/zaltar) - Human Wizard (Level 5) - Preparing *Fireball*.

---

## Location: Cave Entrance Chamber

The air hangs heavy with the smell of damp earth and something vaguely metallic. Water drips intermittently from stalactites, echoing in the vast chamber.

> *"Proceed with caution, friends. I sense a presence... ancient and watchful."* - Zaltar

### Notable Features:
1.  A crumbling stone altar covered in faded runes.
2.  A narrow stream flowing from a crack in the western wall.
3.  Piles of bones (mostly goblinoid) scattered near the northern passage.

**Possible Actions:**
- Investigate the altar (`DC 14 Investigation` to decipher runes).
- Follow the stream (`DC 12 Stealth` to avoid notice).
- Check the bones (`DC 10 Medicine` to determine cause of death).

## Encounter: Goblin Patrol

Suddenly, guttural shouts echo from the northern passage! Three goblins emerge, wielding crude scimitars and hide shields.

<div class="stat-block">
  <div class="stat-block-title">Goblin (Simplified)</div>
  <div class="stat-block-line"><span class="stat-block-property">Armor Class:</span> <span class="stat-block-value">15</span></div>
  <div class="stat-block-line"><span class="stat-block-property">Hit Points:</span> <span class="stat-block-value">7</span></div>
  <div class="stat-block-line"><span class="stat-block-property">Speed:</span> <span class="stat-block-value">30ft</span></div>
  <div class="stat-block-line"><span class="stat-block-property">Actions:</span> <span class="stat-block-value">Scimitar, Shortbow</span></div>
</div>

Roll initiative!

---

## Altar Investigation

Gimli carefully examines the altar. The runes seem to depict a ritual sequence.

### Ritual Steps (Deciphered):
1.  Place the **Iron Key** upon the central glyph.
2.  Anoint the key with **three drops** of fresh blood.
3.  Chant the incantation: "*Ignis revelare secreta*".
4.  The altar is expected to reveal a hidden passage.

---

## Nearby Fungi Patch

Elara spots a patch of glowing fungi near the stream.
*   **Violet Fungi:** Pulsating gently, possibly poisonous.
*   **Blue Caps:** Known for their use in healing salves.
*   **Shriekers:** Appear dormant, but could alert nearby creatures if disturbed.

---

## Goblin Loot Table (Example)

| d6 Roll | Item Found                    | Value (gp) | Notes                       |
| :------ | :---------------------------- | :--------- | :-------------------------- |
| 1-2     | Rusty Scimitar                | 1          | Barely serviceable          |
| 3       | Pouch with `2d4` copper pieces | <1         | Smells faintly of goblin   |
| 4       | Half-eaten rat jerky        | 0          | Questionable edibility    |
| 5       | A single shiny button         | 0          | Seems oddly out of place    |
| 6       | Crude map drawn on hide       | 5          | Shows nearby tunnels        |

---

*Remember to check light sources and marching order.*"""
        self.append_markdown_output(sample_markdown)

    # Implement the callback for the new button
    def append_second_markdown(self):
        LogManager.get_app_logger().info("Append Second Markdown button clicked.") # Use LogManager
        second_markdown = """# Interlude: The Forgotten Shrine\n\n## New Discovery\nThe party stumbles upon a hidden shrine, its walls covered in ancient glyphs.\n\n> *A faint humming fills the air, and the temperature drops.*\n\n### Shrine Features\n- A cracked obsidian altar\n- Flickering blue flames\n- Mysterious runes that glow when touched\n\n**Possible Actions:**\n- Attempt to decipher the runes (`DC 15 Arcana`).\n- Offer a sacrifice on the altar.\n- Search for hidden compartments.\n\n## Encounter: Animated Statues\nTwo stone statues animate and block the exit!\n\n| Name           | AC | HP | Attack         |\n| -------------- | -- | -- | ------------- |\n| Stone Guardian | 17 | 30 | Slam (+5, 2d6+3) |\n| Stone Guardian | 17 | 30 | Slam (+5, 2d6+3) |\n\n*The battle begins anew...*\n"""
        self.append_markdown_output(second_markdown)

    def on_user_speech_checkbox_changed(self, state):
        """Handles the state change of the user speech checkbox."""
        show = state == Qt.Checked
        self.user_speech_display.setVisible(show)
        # Update config and log
        self.config.set("ui_settings.show_user_speech", show)
        self.config.save()
        LogManager.get_app_logger().info(f'\'Show User Speech\' set to {show}')

    def on_min_sentences_changed(self, value: int):
        """Handles changes to the min_sentences spinbox."""
        if self.accumulator:
            self.accumulator.min_sentences = value
            LogManager.get_app_logger().info(f"TranscriptAccumulator min_sentences set to: {value}")
        else:
            LogManager.get_app_logger().warning("Attempted to set min_sentences, but accumulator is not initialized.")

    def on_flush_accumulator_clicked(self):
        """Handles the Flush Accumulator button click."""
        app_logger = LogManager.get_app_logger()
        app_logger.info("'Flush Accumulator' button clicked.")
        if not self.accumulator:
            app_logger.warning("Flush attempted, but accumulator is not initialized.")
            return

        flushed_text = self.accumulator.flush_buffer()

        if flushed_text:
            app_logger.info(f"Flushed text from accumulator (length: {len(flushed_text)}), adding to CHUNK queue: {flushed_text[:80]}...")
            self.chunk_queue.put(flushed_text)
            self._maybe_process_next_input() # Attempt to process immediately
        else:
            app_logger.info("Flush attempted, but accumulator buffer was empty.")

    def update_user_speech_pane(self, hypothesis_text: str):
        """Updates the right pane with settled text (default color) and the current hypothesis (gray)."""
        separator = "\n\n--- In Progress ---\n" if hypothesis_text else ""
        # Construct HTML content with different colors
        # Settled text uses default color, in-progress text is gray
        # Replace newlines with <br> for HTML rendering
        settled_html = self.settled_user_text.replace('\n', '<br>')
        in_progress_html = f"{separator}{hypothesis_text}".replace('\n', '<br>')
        
        # Combine into final HTML.
        final_html = f"<span>{settled_html}</span><span style='color: gray;'>{in_progress_html}</span>"
        
        # Use setHtml instead of setPlainText
        self.user_speech_display.setHtml(final_html)
        
        self.user_speech_display.verticalScrollBar().setValue(
            self.user_speech_display.verticalScrollBar().maximum()
        )

    # Placeholder methods for button actions
    # def start_listening(self):
    #     LogManager.get_app_logger().info("Start button clicked (Not implemented)")
    #     # Logic to start transcription/pipeline

    # def stop_listening(self):
    #     LogManager.get_app_logger().info("Stop button clicked (Not implemented)")
    #     # Logic to stop transcription/pipeline 

    # --- Handle Transcription Segments --- 
    def handle_transcription_result(self, segments: List[Dict[str, Any]]):
        """Handles segments: logs raw, emits intermediate, accumulates, queues final chunks.""" # Updated docstring
        app_logger = LogManager.get_app_logger()
        if not isinstance(segments, list):
             app_logger.warning(f"Warning: handle_transcription_result received non-list data: {type(segments)}")
             return

        # --- Log the raw segments --- 
        raw_logger = LogManager.get_raw_transcript_logger()
        raw_logger.info(f"RAW: {segments}") 

        # --- Emit Intermediate Hypothesis for Display --- 
        current_hypothesis = " ".join(seg.get('text', '').strip() for seg in segments)
        self.intermediate_transcription_updated.emit(current_hypothesis)
        # -----------------------------------------------

        # Accumulate the segments to form final chunks
        accumulated_chunk = self.accumulator.add_segments(segments)

        # If a valid final chunk is returned, add it to the CHUNK queue for LLM processing
        if accumulated_chunk:
            app_logger.info(f"Accumulator produced final chunk, adding to CHUNK queue: {accumulated_chunk[:80]}...")
            self.chunk_queue.put(accumulated_chunk)
            self._maybe_process_next_input()
    # --- End Transcription Handling --- 

    def _maybe_process_next_input(self):
        """Checks CHUNK queue, displays user chunk, runs gatekeeper (bypassed), triggers LLM if ready.""" # Updated docstring
        self.app_logger.debug("Checking if LLM processing can start...")
        if self.is_llm_processing:
            self.app_logger.debug("LLM is currently processing. Skipping.")
            return

        # --- Process from CHUNK queue --- 
        if self.chunk_queue.empty():
            self.app_logger.debug("Chunk queue empty. Nothing to process.")
            return

        # Get the chunk from the queue
        try:
            chunk_to_process = self.chunk_queue.get_nowait() 
            self.app_logger.info(f"Processing final chunk from queue: {chunk_to_process[:80]}...")
            
            # --- Append finalized chunk to settled text and update display --- 
            self.settled_user_text += chunk_to_process + "\n\n" # Add double newline for separation
            # self.user_speech_display.setPlainText(self.settled_user_text) # Update display immediately - OLD
            # Update display using HTML to maintain coloring consistency
            # Replace newlines with <br> for HTML
            settled_html_for_display = self.settled_user_text.replace('\n', '<br>')
            self.user_speech_display.setHtml(f"<span>{settled_html_for_display}</span>") 
            # Ensure the latest settled text is visible
            self.user_speech_display.verticalScrollBar().setValue(
                 self.user_speech_display.verticalScrollBar().maximum()
            )
            # --- Display is handled by intermediate signal now ---
            # self.update_user_speech_pane(chunk_to_process) # <<< REMOVED PREVIOUSLY
            # -------------------------------------------------
        except queue.Empty:
            self.app_logger.debug("Chunk queue became empty unexpectedly.") 
            return

        # --- Temporarily Bypass Gatekeeper --- 
        self.app_logger.info("Gatekeeper check is currently BYPASSED.")
        is_ready = True # Unconditionally proceed
        # --- Original Gatekeeper Logic (Commented Out) ---
        # self.app_logger.info("Checking gatekeeper...")
        # is_ready = False # Default to not ready
        # if not self.ollama_client or not self.gatekeeper_prompt_template:
        #     self.app_logger.warning("Warning: Ollama gatekeeper client or template not ready. Assuming chunk IS ready.")
        #     is_ready = True # Proceed if gatekeeper isn't configured
        # else:
        #     gatekeeper_prompt_formatted = self.gatekeeper_prompt_template.format(accumulated_chunk=accumulated_text)
        #     self.app_logger.debug(f"Gatekeeper Prompt: {gatekeeper_prompt_formatted[:100]}...") 
        #     gatekeeper_model = self.config.get("general.gatekeeper_model", "mistral:latest")
        #     start_time = time.time()
        #     try:
        #         response = self.ollama_client.generate(
        #             model=gatekeeper_model,
        #             prompt=gatekeeper_prompt_formatted,
        #             stream=False,
        #             options={"temperature": 0.2}
        #         )
        #         end_time = time.time()
        #         duration = end_time - start_time
        #         gatekeeper_decision_raw = response.get("response", "").strip()
        #         gatekeeper_decision = gatekeeper_decision_raw.upper()
        #         self.app_logger.info(f"Gatekeeper Response ({duration:.2f}s) - Raw: '{gatekeeper_decision_raw}', Decision: {gatekeeper_decision}") 
        #         if gatekeeper_decision == "YES":
        #             is_ready = True
        #         # else: is_ready remains False (default)
        #     except Exception as e:
        #         self.app_logger.error(f"Error during Ollama gatekeeper call: {e}", exc_info=True)
        #         self.app_logger.warning("Gatekeeper check failed. Assuming chunk IS ready as a fallback.")
        #         is_ready = True # Proceed on gatekeeper error
        # --- End Original Gatekeeper Logic --- 

        if is_ready:
            self.app_logger.info("Proceeding to LLM (Gatekeeper Bypassed or Indicated Ready).") 
            # --- Log User Input before sending --- 
            try:
                user_log_entry = {"role": "USER", "content": chunk_to_process} # Log the finalized chunk
                self.conv_logger.info(json.dumps(user_log_entry))
                self.app_logger.info(f"Logged final USER content (len: {len(chunk_to_process)}) to conversation log.") # Clarified log
            except Exception as log_e:
                self.app_logger.error(f"Failed to log final USER input to conversation log: {log_e}", exc_info=True)
            # -------------------------------------
            # Trigger LLM with the finalized chunk
            self.trigger_llm_request(chunk_to_process) 
        else:
             # This branch should not be reached while gatekeeper is bypassed
            self.app_logger.info("Gatekeeper indicates chunk is NOT ready. Accumulating further.")

    def handle_llm_response(self, response_markdown: str):
        """Handles the received LLM response markdown."""
        self.app_logger.info(f"Received LLM response (length: {len(response_markdown)}). Handling...")
        # --- Log Assistant Response --- 
        try:
            assistant_log_entry = {"role": "ASSISTANT", "content": response_markdown}
            self.conv_logger.info(json.dumps(assistant_log_entry))
            self.app_logger.info(f"Logged ASSISTANT response (len: {len(response_markdown)}) to conversation log.")
        except Exception as log_e:
            self.app_logger.error(f"Failed to log ASSISTANT response to conversation log: {log_e}", exc_info=True)
        # ------------------------------

        self.append_markdown_output(response_markdown) # Append the actual response to the UI
        self.is_llm_processing = False
        self.app_logger.info("LLM processing finished. Ready for next input.")
        # Check immediately if there's more data waiting
        self._maybe_process_next_input() 

    def trigger_llm_request(self, chunk_text: str):
        """Formats prompt and starts LLM worker thread which emits signal."""
        # Set flag FIRST, before checking session
        self.is_llm_processing = True 
        
        if not self.chat_session or not self.main_prompt_template:
            LogManager.get_app_logger().error("ERROR: LLM session or prompt template not ready.") # Use LogManager
            self.is_llm_processing = False 
            self._maybe_process_next_input()
            return
        
        # --- Log the text chunk and history state before sending --- 
        LogManager.get_app_logger().info(f"Text chunk being sent to LLM: '{chunk_text}'")
        try:
            history_len = len(self.chat_session.history)
            LogManager.get_app_logger().info(f"Current chat history length before sending: {history_len}")
        except Exception as e:
            LogManager.get_app_logger().warning(f"Could not determine chat history length: {e}")
        # -----------------------------------------------------------

        # Format the prompt using the loaded template
        formatted_prompt = self.main_prompt_template.format(transcript_chunk=chunk_text)
        LogManager.get_app_logger().debug(f"Formatted prompt for LLM: {formatted_prompt[:200]}...") # Log beginning of prompt
        LogManager.get_app_logger().info(f"Starting MAIN LLM worker thread...")  # Use LogManager
        
        def llm_worker_func(prompt_to_send):
            response_text = "Error: LLM call failed."
            try:
                # Call Gemini directly, no try/except
                LogManager.get_app_logger().info(f"MAIN LLM Thread: Sending formatted prompt...") # Use LogManager
                gemini_response = self.chat_session.send_message(prompt_to_send)
                if hasattr(gemini_response, 'text'):
                    response_text = gemini_response.text
                    LogManager.get_app_logger().info(f"MAIN LLM Thread: Received response text (length: {len(response_text)})." ) # Use LogManager
                else:
                    response_text = f"Error: Unexpected LLM response format: {gemini_response}"
                    LogManager.get_app_logger().error(f"MAIN LLM Thread: Error - {response_text}") # Use LogManager
            except Exception as e:
                LogManager.get_app_logger().error(f"MAIN LLM Thread: Error during Gemini API call: {e}", exc_info=True)
                response_text = f"Error: Exception during LLM call: {e}"
            
            # --- Emit signal --- 
            LogManager.get_app_logger().info(f"MAIN LLM Thread: Emitting response signal...") # Use LogManager
            self.llm_response_received.emit(response_text)
            # -------------------
            
        worker_thread = threading.Thread(target=llm_worker_func, args=(formatted_prompt,))
        worker_thread.daemon = True # Ensure thread exits if main app exits
        worker_thread.start()

    def start_audio_processing(self):
        """Initializes and starts the transcription client and monitoring thread."""
        app_logger = LogManager.get_app_logger()
        app_logger.info("Start Audio Processing button clicked.")
        if self.transcription_thread and self.transcription_thread.is_alive():
            app_logger.warning("Transcription already running.")
            return

        # Get config values
        project_root = Path(__file__).parent.parent
        input_audio_path_str = self.config.get("paths.input_audio", "default_audio.wav")
        input_audio_path = str(project_root / input_audio_path_str)
        transcription_host = self.config.get("servers.transcription_host", "localhost")
        transcription_port = self.config.get("servers.transcription_port", 9090)
        # --- Load last playback position --- 
        start_playback_time = self.config.get("audio_settings.last_playback_position", 0.0)
        app_logger.info(f"Attempting to start playback from: {start_playback_time:.2f} seconds")
        # -----------------------------------

        app_logger.info(f"Initializing transcription client for file: {input_audio_path}")
        if not os.path.exists(input_audio_path):
            app_logger.error(f"ERROR: Input audio file not found at {input_audio_path}")
            return

        # Clear queues
        app_logger.info("Clearing any previous SEGMENT queue data...") # Use LogManager
        cleared_count = 0
        while not self.segment_queue.empty():
            try:
                self.segment_queue.get_nowait()
                cleared_count += 1
            except queue.Empty:
                break
        app_logger.debug(f"Cleared {cleared_count} items from SEGMENT queue.") # Use LogManager
        app_logger.info("Clearing any previous CHUNK queue data...") # Use LogManager
        cleared_count = 0
        while not self.chunk_queue.empty():
             try:
                 self.chunk_queue.get_nowait()
                 cleared_count += 1
             except queue.Empty:
                 break
        app_logger.debug(f"Cleared {cleared_count} items from CHUNK queue.") # Use LogManager

        # Mute setting
        mute_setting = self.config.get("general.mute_playback", True)
        wrapper_args = {"mute_audio_playback": mute_setting}
        app_logger.info(f"Mute playback setting: {mute_setting}")

        client_args = {
             "output_queue": self.segment_queue,
             "lang": None, "translate": False, "model": "large-v3", "use_vad": True, "log_transcription": False
        }
        try:
            # Initialize the client instance
            self.transcription_client = TranscriptionClient(
                host=transcription_host,
                port=transcription_port,
                **client_args,
                **wrapper_args
            )
            app_logger.info("Transcription client instance initialized.")
        except Exception as e:
            app_logger.error(f"Failed to initialize TranscriptionClient: {e}", exc_info=True)
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            return

        # Start the client logic (audio playback/sending) in its thread
        # --- Pass start_time to the client call --- 
        app_logger.info(f"Starting transcription client thread for file: {input_audio_path} at {start_playback_time:.2f}s")
        self.transcription_thread = threading.Thread(
            target=self.transcription_client.__call__, # Target the __call__ method
            kwargs={ # Pass arguments as kwargs
                'audio': input_audio_path,
                'start_time': start_playback_time
            },
            daemon=True
        )
        # -----------------------------------------
        
        # Start monitor thread
        self.queue_monitor_stop_event = threading.Event()
        self.queue_monitor_thread = threading.Thread(
            target=self._monitor_transcription_queue,
            daemon=True
        )

        self.transcription_thread.start()
        self.queue_monitor_thread.start()
        app_logger.info("Transcription and queue monitor threads started.")

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _monitor_transcription_queue(self):
        """Monitors the SEGMENT queue, emits transcription_received signal."""
        LogManager.get_app_logger().info("SEGMENT queue monitor thread started.") # Use LogManager
        while not self.queue_monitor_stop_event.is_set():
            try:
                # Get data from SEGMENT queue
                data = self.segment_queue.get(block=True, timeout=0.5)
                if data is None: break
                
                # --- Type Check --- 
                if isinstance(data, list):
                    # Only emit if it's a list (expected segments)
                    LogManager.get_app_logger().debug(f"Monitor received {len(data)} segments, emitting signal...") # Use LogManager
                    self.transcription_received.emit(data)
                else:
                    # Log unexpected data type received from transcription client queue
                    LogManager.get_app_logger().warning(f"Received non-list data type from segment_queue: {type(data)}. Value: {str(data)[:100]}") # Use LogManager
                # ----------------
                
            except queue.Empty: continue
        LogManager.get_app_logger().info("SEGMENT queue monitor thread finished.") # Use LogManager

    def stop_audio_processing(self):
        # --- IMMEDIATE DEBUG PRINT --- 
        try:
            print("STOP BUTTON PRESSED - stop_audio_processing called", file=sys.stderr)
            sys.stderr.flush() # Ensure it appears immediately
        except Exception as e:
            # Fallback just in case stderr write fails
            print(f"STOP BUTTON PRESSED (stderr write failed: {e})")
        # ---------------------------
        app_logger = LogManager.get_app_logger()
        app_logger.info("Stop button clicked - Stopping transcription...")

        # --- Explicitly signal the client loop to stop --- 
        if self.transcription_client and hasattr(self.transcription_client, 'client') and self.transcription_client.client:
            app_logger.info("Attempting to set client.recording = False")
            try:
                self.transcription_client.client.recording = False
            except Exception as e:
                app_logger.error(f"Error setting client.recording flag: {e}")
        else:
            app_logger.warning("Cannot set client.recording flag: transcription_client or its client attribute is None.")

        # --- Save current playback position BEFORE stopping client --- 
        current_pos = 0.0
        if self.transcription_client:
            try:
                if hasattr(self.transcription_client, 'get_current_playback_position'):
                    current_pos = self.transcription_client.get_current_playback_position()
                    app_logger.info(f"Current playback position: {current_pos:.2f} seconds.")
                    self.config.set("audio_settings.last_playback_position", current_pos)
                    app_logger.info(f"Saved playback position {current_pos:.2f} to config.")
                else:
                    app_logger.warning("Transcription client does not have get_current_playback_position method.")
            except Exception as e:
                app_logger.error(f"Error getting or saving playback position: {e}", exc_info=True)
        else:
            app_logger.warning("Cannot get playback position: transcription client is None.")

        # 1. Signal the monitor thread to stop
        if hasattr(self, 'queue_monitor_stop_event') and self.queue_monitor_stop_event:
            self.queue_monitor_stop_event.set()
            app_logger.info("Queue monitor stop signal sent.")
        else:
             app_logger.warning("Queue monitor stop event not found or already None.")

        # 2. Signal the transcription client to stop (websocket etc.)
        if self.transcription_client:
            if hasattr(self.transcription_client, 'stop'):
                 LogManager.get_app_logger().info("Attempting to call client stop method...") # Use LogManager
                 try:
                      self.transcription_client.stop() # Hypothetical stop method
                 except Exception as e:
                     LogManager.get_app_logger().error(f"Error calling client stop method: {e}", exc_info=True)
            elif hasattr(self.transcription_client, 'client') and hasattr(self.transcription_client.client, 'close_websocket'):
                 LogManager.get_app_logger().info("Attempting to close client websocket...") # Use LogManager
                 try:
                     self.transcription_client.client.close_websocket()
                 except Exception as e:
                     LogManager.get_app_logger().error(f"Error closing client websocket: {e}", exc_info=True)
            else:
                 LogManager.get_app_logger().warning("No clean stop method found for transcription client.") # Use LogManager
        else:
             LogManager.get_app_logger().info("Transcription client is None, nothing to stop.")

        # 3. Join threads (with timeout)
        if self.transcription_thread and self.transcription_thread.is_alive():
            LogManager.get_app_logger().info("Waiting for transcription thread to join...") # Use LogManager
            self.transcription_thread.join(timeout=2.0)
            if self.transcription_thread.is_alive():
                LogManager.get_app_logger().warning("Transcription thread did not join cleanly after timeout.") # Use LogManager
            else:
                LogManager.get_app_logger().info("Transcription thread joined.") # Use LogManager
        
        if self.queue_monitor_thread and self.queue_monitor_thread.is_alive():
            LogManager.get_app_logger().info("Waiting for queue monitor thread to join...") # Use LogManager
            self.queue_monitor_thread.join(timeout=1.0)
            if self.queue_monitor_thread.is_alive():
                LogManager.get_app_logger().warning("Queue monitor thread did not join cleanly after timeout.") # Use LogManager
            else:
                 LogManager.get_app_logger().info("Queue monitor thread joined.") # Use LogManager
        
        # 4. Clean up resources
        self.transcription_client = None
        self.transcription_thread = None
        self.queue_monitor_thread = None # Clear reference
        # Clear the queue again
        while not self.segment_queue.empty():
            try: self.segment_queue.get_nowait() 
            except queue.Empty: break
        while not self.chunk_queue.empty():
            try: self.chunk_queue.get_nowait() 
            except queue.Empty: break
        LogManager.get_app_logger().info("Resources cleaned up.") # Use LogManager

        # 5. Update UI state
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        app_logger.info("Transcription stopped.") # Use LogManager

    def closeEvent(self, event):
        """Ensures background threads are stopped cleanly on window close."""
        self.app_logger.info("Close event triggered. Stopping background processes...")
        self.stop_audio_processing() # Attempt to stop threads gracefully
        # Wait a short moment for threads to potentially finish stopping
        # time.sleep(0.5) 
        super().closeEvent(event) # Call the default handler

# --- Main Execution --- 
def main():
    # Initialize logging BEFORE anything else
    LogManager.initialize()
    logger = LogManager.get_app_logger()
    logger.info("Application starting...")

    app = QApplication(sys.argv)

    # Force dark theme (optional, but good for consistency)
    # ... (dark theme setup) ...

    window = MainWindow()
    window.show()
    logger.info("Main window shown.")

    exit_code = app.exec_()
    logger.info(f"Application exiting with code {exit_code}.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
        