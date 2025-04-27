"""
Main application script for the DMS Helper.

Coordinates transcription input, context loading, LLM interaction,
and displays results.
"""

import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import datetime # Added for timestamping logs
import sys # Added to potentially access client methods
import queue       # Added for transcript queue
import threading   # Added for transcription thread
import signal      # Added for graceful shutdown
import re # Added for sentence splitting
import ollama      # Added for gatekeeper LLM

# Project imports (ensure these paths are correct relative to src/)
from context_loader import load_and_combine_context
# Make sure whisper_live_client path is correct
# Assumes client is in a sibling directory or installed
try:
    from whisper_live_client.client import TranscriptionClient
except ImportError:
    logging.error("Failed to import TranscriptionClient. Make sure whisper_live_client is installed or accessible.")
    # Depending on structure, might need sys.path manipulation if it's local
    # import sys
    # sys.path.append(str(Path(__file__).parent.parent)) # Example if client is in project root
    # from whisper_live_client.client import TranscriptionClient
    # For now, exit if import fails after trying default path
    sys.exit(1)

import google.generativeai as genai
from dotenv import load_dotenv
import os
from transcript_accumulator import TranscriptAccumulator # Added import

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - CONSOLE - %(message)s')

# --- Constants --- (Can be moved to a config file later)
LLM_MODEL_NAME = 'gemini-1.5-flash' # Or the preview model we tested
TRANSCRIPTION_SERVER_HOST = "localhost"
TRANSCRIPTION_SERVER_PORT = 9090
# Add constants for transcript accumulation strategy?
PROMPT_TEMPLATE_FILE = Path(__file__).parent.parent / "prompts/dm_assistant_prompt.md" # Path relative to this script
GATEKEEPER_PROMPT_FILE = Path(__file__).parent.parent / "prompts/gatekeeper_prompt.md"
LOG_DIRECTORY = Path(__file__).parent.parent / "logs"
ASSISTANT_NEEDS_MORE_CONTEXT = "ASSISTANT_NEEDS_MORE_CONTEXT"
# Ollama Gatekeeper Config
OLLAMA_HOST = "http://192.168.0.200:11434" # Host from user confirmation
GATEKEEPER_MODEL = "mistral:latest"        # Model specified by user
GATEKEEPER_TIMEOUT_SECONDS = 30           # Timeout for gatekeeper request

# --- Global Shutdown Flag ---
# Using threading.Event for thread-safe signaling
shutdown_requested = threading.Event()

# --- Signal Handler ---
def sigint_handler(signum, frame):
    """Sets the shutdown flag upon receiving SIGINT (Ctrl+C)."""
    logging.info("SIGINT received, requesting shutdown...")
    shutdown_requested.set()

def setup_file_loggers(timestamp: str):
    """Sets up file handlers for detailed logging."""
    LOG_DIRECTORY.mkdir(exist_ok=True)

    log_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Logger for raw transcript
    raw_transcript_logger = logging.getLogger('raw_transcript')
    raw_transcript_logger.setLevel(logging.DEBUG) # Log everything passed to it
    raw_handler = logging.FileHandler(LOG_DIRECTORY / f"raw_transcript_{timestamp}.log", encoding='utf-8')
    raw_handler.setFormatter(log_formatter)
    raw_transcript_logger.addHandler(raw_handler)
    raw_transcript_logger.propagate = False # Don't send to root logger/console

    # Logger for prompts sent
    prompts_logger = logging.getLogger('prompts_sent')
    prompts_logger.setLevel(logging.DEBUG)
    prompts_handler = logging.FileHandler(LOG_DIRECTORY / f"prompts_sent_{timestamp}.log", encoding='utf-8')
    prompts_handler.setFormatter(log_formatter)
    prompts_logger.addHandler(prompts_handler)
    prompts_logger.propagate = False

    # Logger for responses received
    responses_logger = logging.getLogger('responses_received')
    responses_logger.setLevel(logging.DEBUG)
    responses_handler = logging.FileHandler(LOG_DIRECTORY / f"responses_received_{timestamp}.log", encoding='utf-8')
    responses_handler.setFormatter(log_formatter)
    responses_logger.addHandler(responses_handler)
    responses_logger.propagate = False

    # Logger for combined session log
    combined_logger = logging.getLogger('combined_session')
    combined_logger.setLevel(logging.DEBUG)
    combined_handler = logging.FileHandler(LOG_DIRECTORY / f"combined_session_{timestamp}.log", encoding='utf-8')
    # Slightly different format for combined log to show source
    combined_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    combined_handler.setFormatter(combined_formatter)
    combined_logger.addHandler(combined_handler)
    combined_logger.propagate = False # Keep separate from console

    logging.info(f"Detailed logs will be saved in: {LOG_DIRECTORY}")
    return raw_transcript_logger, prompts_logger, responses_logger, combined_logger

def load_prompt_template(file_path: Path) -> Optional[str]:
    """Loads the prompt template from a file."""
    if not file_path.is_file():
        logging.error(f"Prompt template file not found: {file_path}")
        return None
    try:
        # We are reading the whole file, no need for try/except for file read errors based on rules
        prompt_template = file_path.read_text(encoding="utf-8")
        logging.info(f"Prompt template loaded from {file_path}")
        return prompt_template
    # Base Exception is too broad, but needed if file_path.read_text raises non-IO errors
    # Revisit if specific exceptions from read_text can be identified.
    # Per rules, avoiding specific Exception types like IOError.
    except Exception as e:
        logging.error(f"Failed to read prompt template file {file_path}: {e}")
        return None

def initialize_llm(api_key: str) -> Optional[genai.GenerativeModel]:
    """Configures the Gemini API and initializes the generative model."""
    if not api_key:
        logging.error("Google API Key is missing.")
        return None
    genai.configure(api_key=api_key)
    logging.info("Gemini API configured.")
    logging.info(f"Initializing LLM model: {LLM_MODEL_NAME}")
    model = genai.GenerativeModel(LLM_MODEL_NAME)
    logging.info("LLM model initialized.")
    return model

def initialize_ollama_client(host: str) -> Optional[ollama.Client]:
    """Initializes the Ollama client."""
    logging.info(f"Initializing Ollama client for host: {host}")
    # No try/except per project rules. If connection fails, it will raise an exception.
    client = ollama.Client(host=host)
    # We could potentially do a client.list() here to confirm connection
    # but it adds latency. Let's rely on the first generate call to fail if needed.
    # Alternatively, run test_ollama_connection.py separately before starting.
    logging.info("Ollama client initialized.")
    return client

def initialize_transcription_client(output_queue: Optional[queue.Queue] = None, input_audio_path: Optional[str] = None) -> Optional[TranscriptionClient]:
    """
    Initializes the WhisperLive transcription client.
    Always connects to the server, audio source handled later.
    Passes the output_queue to the underlying Client instance.
    """
    # Always use the configured host and port for the WebSocket connection
    host = TRANSCRIPTION_SERVER_HOST
    port = TRANSCRIPTION_SERVER_PORT

    # Common arguments for the underlying Client
    client_args = {
        "lang": None, # Use None for multilingual large-v3 model
        "translate": False,
        "model": "large-v3", # Changed to largest model
        "use_vad": True,
        "output_queue": output_queue,
        "log_transcription": False # Disable internal console logging
    }
    # Arguments specific to TranscriptionClient wrapper (not passed to Client directly)
    wrapper_args = {
        "mute_audio_playback": True # Mute playback for file mode by default
        # Add other TranscriptionClient __init__ specific args (save_output_recording etc.)
    }

    if input_audio_path:
        logging.info(f"Initializing transcription client for file playback: {input_audio_path}")
    else:
        logging.info(f"Initializing transcription client for live input at ws://{host}:{port}")
        wrapper_args["mute_audio_playback"] = False # Ensure playback is NOT muted for live mic

    try:
        client = TranscriptionClient(
            host=host,
            port=port,
            **client_args, # Pass args intended for base Client
            **wrapper_args # Pass args intended for TranscriptionClient wrapper
        )
        logging.info("Transcription client initialized.")
        return client
    except Exception as e:
        logging.error(f"Error initializing transcription client: {e}", exc_info=True)
        return None

def run_assistant():
    """Main loop for the DMS Assistant."""
    run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Archive existing logs --- (Added)
    archive_dir = LOG_DIRECTORY / "archive"
    # Ensure the archive directory exists
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_count = 0
    # Check if LOG_DIRECTORY itself exists before trying to list its contents
    if LOG_DIRECTORY.exists() and LOG_DIRECTORY.is_dir():
        for log_file in LOG_DIRECTORY.glob("*.log"):
            if log_file.is_file(): # Ensure it's a file, not a directory
                archive_target = archive_dir / log_file.name
                # Avoid moving already archived files or directories (though glob shouldn't catch dirs)
                if archive_target.exists():
                    logging.warning(f"Skipping move: {log_file.name} already exists in archive.")
                    continue
                try:
                    log_file.rename(archive_target)
                    archived_count += 1
                except OSError as e:
                    # Log error but continue script (as per no hard fail rule for non-critical ops like this)
                    logging.error(f"Could not move log file {log_file.name} to archive: {e}")
    if archived_count > 0:
        logging.info(f"Archived {archived_count} previous log file(s) to {archive_dir}")
    # --- End of Archive Logic --- (Added)

    raw_transcript_logger, prompts_logger, responses_logger, combined_logger = setup_file_loggers(run_timestamp)

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, sigint_handler)

    # --- Use Hardcoded Paths --- (Instead of parameters)
    campaign_config_path = str(Path("source_materials/ceres_group/ceres_odyssey.json").resolve())
    input_audio_file = str(Path("source_materials/recording_of_dm_resampled.wav").resolve())

    logging.info(f"Starting DMS Assistant Run: {run_timestamp}")
    # Log the hardcoded paths being used
    logging.info(f"Using Campaign Config: {campaign_config_path}")
    logging.info(f"Using Input Audio File: {input_audio_file}")

    # 0. Load Prompt Templates
    logging.info("Loading main prompt template...")
    main_prompt_template = load_prompt_template(PROMPT_TEMPLATE_FILE)
    if not main_prompt_template:
        return # Error logged in load_prompt_template

    logging.info("Loading gatekeeper prompt template...")
    gatekeeper_prompt_template = load_prompt_template(GATEKEEPER_PROMPT_FILE)
    if not gatekeeper_prompt_template:
        return # Error logged in load_prompt_template

    # 1. Load Context
    logging.info("Loading context...")
    initial_context = load_and_combine_context(campaign_config_path)
    if not initial_context:
        logging.error("Failed to load initial context. Exiting.")
        return
    logging.info(f"Context loaded ({len(initial_context)} characters).")
    # Log initial context only to combined log for reference if needed
    combined_logger.info(f"INITIAL_CONTEXT_LOADED: {len(initial_context)} chars")

    # 2. Initialize LLM
    logging.info("Initializing LLM...")
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    llm_model = initialize_llm(api_key)
    if not llm_model:
        # Error logged in initialize_llm
        return

    # 3. Initialize Ollama Client (Gatekeeper)
    logging.info("Initializing Ollama client (Gatekeeper)...")
    ollama_client = initialize_ollama_client(host=OLLAMA_HOST)
    if not ollama_client:
        # Error should be logged in initialize_ollama_client if it fails
        # If initialization itself fails (e.g., bad host string format),
        # an exception will halt the program per rules.
        # We only reach here if init returned None (which it currently doesn't, but defensively)
        logging.error("Failed to initialize Ollama client. Exiting.")
        return
    combined_logger.info("OLLAMA_CLIENT_INITIALIZED")

    # 4. Start LLM Chat Session (Gemini)
    logging.info("Starting LLM chat session with context...")
    initial_history = [
        {'role': 'user', 'parts': [initial_context]},
        {'role': 'model', 'parts': ["Okay, I have loaded the context. I am ready to assist based on the DM's narration."]}
    ]
    chat_session = llm_model.start_chat(history=initial_history)
    logging.info("LLM chat session started.")
    combined_logger.info("LLM_SESSION_STARTED")

    # 5. Initialize Transcription Client & Queue
    logging.info("Initializing transcription client...")
    transcript_queue = queue.Queue()
    transcription_client = initialize_transcription_client(output_queue=transcript_queue, input_audio_path=input_audio_file)
    if not transcription_client:
        logging.error("Failed to initialize transcription client. Exiting.")
        return
    combined_logger.info("TRANSCRIPTION_CLIENT_INITIALIZED")

    # 6. Start Transcription Thread
    transcription_thread = None
    if input_audio_file:
        logging.info(f"Starting transcription thread for file: {input_audio_file}")
        transcription_thread = threading.Thread(
            target=transcription_client,
            args=(input_audio_file,),
            daemon=True
        )
        transcription_thread.start()
        combined_logger.info(f"TRANSCRIPTION_THREAD_STARTED: {input_audio_file}")
    else:
        # TODO: Implement live microphone handling here later
        logging.error("Live microphone input not yet implemented. Please provide --input-audio-file.")
        combined_logger.error("LIVE_MODE_NOT_IMPLEMENTED")
        return # Exit if no file and live not ready

    # --- 7. Main Processing Loop ---
    logging.info("Starting main processing loop...")
    accumulator = TranscriptAccumulator() # Instantiate the accumulator (KEEP THIS)
    processed_final_chunk = False # Flag to track if final chunk was processed (KEEP THIS)

    try: # Use finally for guaranteed cleanup
        while not shutdown_requested.is_set():
            try:
                segment = transcript_queue.get(block=True, timeout=0.5)
                if segment is None:
                    logging.info("Received sentinel, ending transcription processing.")
                    combined_logger.info("TRANSCRIPT_SENTINEL_RECEIVED")
                    break

                # Process Transcript Segment
                raw_transcript_logger.debug(segment)
                combined_logger.debug(f"TRANSCRIPT_SEGMENT: {segment}")

                # Accumulate & Check for Chunk
                accumulated_chunk = accumulator.add_segments(segment) # Use accumulator. Renamed method call.

                if accumulated_chunk:
                    logging.info(f"Accumulated chunk ready ({len(accumulated_chunk)} chars). Sending to gatekeeper...")
                    logging.info(f"Gatekeeper Input Text:\n---\n{accumulated_chunk}\n---")
                    combined_logger.info(f"GATEKEEPER_INPUT_CHUNK: {accumulated_chunk}")

                    # --- Call Ollama Gatekeeper --- (NO TRY/EXCEPT BLOCK)
                    gatekeeper_prompt_formatted = gatekeeper_prompt_template.format(accumulated_chunk=accumulated_chunk)

                    # Log the prompt being sent to the gatekeeper
                    # prompts_logger.debug(f"GATEKEEPER_PROMPT: {gatekeeper_prompt_formatted}") # Maybe too verbose for prompts log?
                    combined_logger.debug(f"GATEKEEPER_PROMPT_SENT (model: {GATEKEEPER_MODEL})")

                    # Call Ollama - if this fails (network error, server down), an exception will halt execution per rules
                    start_time = time.time()
                    response = ollama_client.generate(
                        model=GATEKEEPER_MODEL,
                        prompt=gatekeeper_prompt_formatted,
                        stream=False,
                        options={"temperature": 0.2} # Lower temperature for deterministic YES/NO
                    )
                    end_time = time.time()
                    duration = end_time - start_time

                    gatekeeper_decision_raw = response.get("response", "").strip()
                    gatekeeper_decision = gatekeeper_decision_raw.upper()

                    # Log gatekeeper response and decision
                    # responses_logger.debug(f"GATEKEEPER_RESPONSE: {gatekeeper_decision_raw}") # Maybe too verbose?
                    logging.info(f"Gatekeeper raw response: '{gatekeeper_decision_raw}' ({duration:.2f}s)")
                    logging.info(f"Gatekeeper decision: {gatekeeper_decision}")
                    combined_logger.info(f"GATEKEEPER_DECISION: {gatekeeper_decision} (Raw: '{gatekeeper_decision_raw}', Duration: {duration:.2f}s)")

                    # --- Check Gatekeeper Decision --- (Simplified logic)
                    if gatekeeper_decision == "YES":
                        logging.info("Gatekeeper approved. Preparing to call main LLM (Gemini)...")
                        combined_logger.info("GATEKEEPER_APPROVED_PROCEEDING_TO_GEMINI")

                        # Format the main prompt for Gemini
                        main_prompt_formatted = main_prompt_template.format(transcript_chunk=accumulated_chunk)

                        # Log the prompt being sent to Gemini
                        prompts_logger.info(f"GEMINI_PROMPT (using chunk approved by gatekeeper):\n{main_prompt_formatted}\n-------------------------")
                        combined_logger.info("GEMINI_PROMPT_SENT")

                        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                        # === SEND TO GEMINI LLM ===
                        # Send the formatted prompt to the Gemini chat session
                        # No try/except block per project rules. Let errors propagate.
                        gemini_response = chat_session.send_message(main_prompt_formatted)

                        # Log the response
                        logging.info(f"Gemini Raw Response: {gemini_response}") # Log the whole object for debug if needed
                        if hasattr(gemini_response, 'text'):
                            response_text = gemini_response.text
                            logging.info(f"Gemini Response Text: {response_text}")
                            responses_logger.info(f"GEMINI_RESPONSE: {response_text}")
                            combined_logger.info(f"GEMINI_RESPONSE_RECEIVED: {response_text}")

                            # Display response to user (console for now)
                            print("\n--- Assistant Suggestion ---")
                            print(response_text)
                            print("--------------------------\n")
                        else:
                            # Handle cases where the response might not have a simple .text attribute
                            # (e.g., blocked prompt, other API errors structured differently)
                            logging.warning(f"Gemini response did not contain expected text attribute. Response: {gemini_response}")
                            combined_logger.warning(f"GEMINI_RESPONSE_UNEXPECTED_FORMAT: {gemini_response}")
                            print("\n--- Assistant: Received unexpected response format from LLM ---\n")

                        # logging.warning("*** Gemini API call is currently skipped/not implemented! ***") # Placeholder REMOVED
                        # combined_logger.warning("GEMINI_CALL_SKIPPED (Not Implemented)") # Placeholder REMOVED
                        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

                    elif gatekeeper_decision == "NO":
                        logging.info("Gatekeeper rejected. Skipping main LLM call.")
                        combined_logger.info("GATEKEEPER_REJECTED_SKIPPING_GEMINI")
                    else:
                        # Handle unclear response - log warning, skip Gemini call for safety/cost
                        logging.warning(f"Gatekeeper response unclear ('{gatekeeper_decision_raw}'). Skipping main LLM call.")
                        combined_logger.warning(f"GATEKEEPER_UNCLEAR_SKIPPING_GEMINI (Raw: '{gatekeeper_decision_raw}')")

            except queue.Empty:
                # Timeout occurred, check if transcription thread is done
                if transcription_thread and not transcription_thread.is_alive() and transcript_queue.empty():
                    logging.info("Transcription thread finished and queue is empty. Exiting loop.")
                    combined_logger.info("TRANSCRIPTION_THREAD_DONE_QUEUE_EMPTY")
                    break
                # Otherwise, just loop again to wait for more segments or shutdown signal
                continue

        # Process Final Chunk (After loop exit) (KEEP THIS BLOCK)
        if not shutdown_requested.is_set():
            final_chunk = accumulator.flush()
            if final_chunk:
                processed_final_chunk = True
                logging.info("Processing final chunk from buffer...")
                combined_logger.debug(f"FINAL_CHUNK: {final_chunk}")
                # --- PRINT FOR DEBUG ---
                print("-"*20 + " FINAL CHUNK " + "-"*20)
                print(final_chunk)
                print("-"*53)
                # ---------------------

                # Format Prompt (KEEP THIS)
                formatted_prompt = main_prompt_template.format(transcript_chunk=final_chunk)
                prompts_logger.debug(formatted_prompt)
                combined_logger.debug(f"PROMPT_SENT_FINAL: {formatted_prompt}")

                # LLM Call Skipped (KEEP THIS)
                logging.info("[TESTING] Final LLM Call Skipped.")
            else:
                logging.info("No final chunk to process from buffer.")

        # Loop End logging (KEEP THIS)
        if shutdown_requested.is_set():
            logging.info("Shutdown requested, exiting main loop.")
            combined_logger.info("SHUTDOWN_REQUESTED_EXITING_LOOP")
        else:
            logging.info("Finished processing transcript stream normally.")
            combined_logger.info("TRANSCRIPT_STREAM_ENDED_NORMALLY")

    finally:
        # --- 8. Cleanup ---
        logging.info("Initiating cleanup...")
        combined_logger.info("CLEANUP_STARTED")

        # Ensure transcription thread is finished
        if transcription_thread and transcription_thread.is_alive():
            logging.info("Waiting for transcription thread to complete...")
            # Signal the client thread to stop? (Might need modification in client)
            # For now, just join with timeout
            transcription_thread.join(timeout=5.0)
            if transcription_thread.is_alive():
                logging.warning("Transcription thread did not exit cleanly after join timeout.")
                combined_logger.warning("TRANSCRIPTION_THREAD_JOIN_TIMEOUT")
            else:
                 logging.info("Transcription thread joined.")
                 combined_logger.info("TRANSCRIPTION_THREAD_JOINED")

        # Close client connection (if method exists and is safe)
        if transcription_client:
            logging.info("Attempting to close transcription client...")
            try:
                # Check if close method exists, call it if safe
                # Assuming transcription_client wraps a single client instance accessible via .client
                if hasattr(transcription_client, 'client') and hasattr(transcription_client.client, 'close_websocket'):
                     transcription_client.client.close_websocket()
                     logging.info("Transcription client websocket closed.")
                     combined_logger.info("TRANSCRIPTION_CLIENT_WEBSOCKET_CLOSED")
                elif hasattr(transcription_client, 'close_all_clients'): # Fallback if structure changed
                     transcription_client.close_all_clients()
                     logging.info("Transcription client (via close_all_clients) closed.")
                     combined_logger.info("TRANSCRIPTION_CLIENT_ALL_CLOSED")
                else:
                     logging.warning("Could not find appropriate method to close transcription client.")
            except Exception as e:
                logging.warning(f"Error during transcription client cleanup: {e}")
                combined_logger.warning(f"TRANSCRIPTION_CLIENT_CLEANUP_ERROR: {e}")

        logging.info("DMS Assistant finished.")
        combined_logger.info("ASSISTANT_RUN_FINISHED")


if __name__ == "__main__":
    # Removed argparse setup

    # --- Basic File Checks (Optional but good practice) ---
    campaign_path_obj = Path("source_materials/ceres_group/ceres_odyssey.json")
    audio_path_obj = Path("source_materials/recording_of_dm_resampled.wav")

    if not campaign_path_obj.is_file():
        logging.error(f"Error: Hardcoded campaign configuration file not found at {campaign_path_obj}")
        sys.exit(1)

    if not audio_path_obj.is_file():
        logging.error(f"Error: Hardcoded input audio file not found at {audio_path_obj}")
        sys.exit(1)

    # Call run_assistant without arguments
    run_assistant() 