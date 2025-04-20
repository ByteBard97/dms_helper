"""
Main application script for the DMS Helper.

Coordinates transcription input, context loading, LLM interaction,
and displays results.
"""

import argparse
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

# Project imports (ensure these paths are correct relative to src/)
from context_loader import load_and_combine_context
from whisper_live_client.client import TranscriptionClient # Assuming this is the correct client
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants --- (Can be moved to a config file later)
LLM_MODEL_NAME = 'gemini-1.5-flash' # Or the preview model we tested
TRANSCRIPTION_SERVER_HOST = "localhost"
TRANSCRIPTION_SERVER_PORT = 9090
# Add constants for transcript accumulation strategy?
PROMPT_TEMPLATE_FILE = Path(__file__).parent.parent / "prompts/dm_assistant_prompt.md" # Path relative to this script

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

def initialize_transcription_client(): # -> Optional[TranscriptionClient]: # Add return type later
    """Initializes and connects to the WhisperLive transcription server."""
    logging.info(f"Attempting to connect to transcription server at ws://{TRANSCRIPTION_SERVER_HOST}:{TRANSCRIPTION_SERVER_PORT}")
    # TODO: Instantiate TranscriptionClient
    # Need to handle potential connection errors here without try block?
    # Maybe the client handles initial connection errors internally?
    # For now, assume connection will succeed or client handles exit/error.
    client = TranscriptionClient(
        host=TRANSCRIPTION_SERVER_HOST,
        port=TRANSCRIPTION_SERVER_PORT,
        lang="en",  # Or make configurable
        translate=False,
        model="small.en", # This might not be needed if server handles it
        use_vad=True
    )
    logging.info("Transcription client initialized (connection pending)...")
    # How do we get text back? Does client have a callback or generator?
    # Need to investigate the TranscriptionClient API.
    return client # Placeholder

def run_assistant(campaign_config_path: str):
    """Main loop for the DMS Assistant."""
    logging.info(f"Starting DMS Assistant with campaign config: {campaign_config_path}")

    # 0. Load Prompt Template
    logging.info("Loading prompt template...")
    prompt_template = load_prompt_template(PROMPT_TEMPLATE_FILE)
    if not prompt_template:
        logging.error("Failed to load prompt template. Exiting.")
        return

    # 1. Load Context
    logging.info("Loading context...")
    initial_context = load_and_combine_context(campaign_config_path)
    if not initial_context:
        logging.error("Failed to load initial context. Exiting.")
        return
    logging.info(f"Context loaded ({len(initial_context)} characters)." )

    # 2. Initialize LLM
    logging.info("Initializing LLM...")
    load_dotenv() # Load GOOGLE_API_KEY from .env
    api_key = os.getenv("GOOGLE_API_KEY")
    llm_model = initialize_llm(api_key)
    if not llm_model:
        logging.error("Failed to initialize LLM. Exiting.")
        return

    # 3. Start LLM Chat Session with Context
    logging.info("Starting LLM chat session with context...")
    # Pass initial context. How does Gemini handle large initial context?
    # Using history for initial context dump as per Gemini examples.
    # Ensure the initial context is formatted correctly for the history.
    # The context loader should ideally return it in a format suitable for this,
    # but for now, assume it's a single string block.
    initial_history = [
        {'role': 'user', 'parts': [initial_context]},
        {'role': 'model', 'parts': ["Okay, I have loaded the context. I am ready to assist based on the DM's narration."]} # Prime the model
    ]
    chat_session = llm_model.start_chat(history=initial_history)
    logging.info("LLM chat session started.")

    # 4. Initialize Transcription Client
    # TODO: How to handle potential connection failure robustly without try block?
    # transcription_client = initialize_transcription_client()
    # if not transcription_client:
    #     logging.error("Failed to initialize transcription client. Exiting.")
    #     return
    logging.warning("Transcription client initialization SKIPPED for now.")

    # 5. Main Loop (Processing Transcript -> LLM -> Output)
    logging.info("Starting main processing loop (Placeholder)...")
    # TODO:
    # - How to receive transcript segments from transcription_client?
    #   (Callback? Generator? Blocking call?)
    # - Implement transcript accumulation logic (buffer, sentence/pause detection).
    #   Target: 3-10 sentences OR significant pause.
    # - Implement prompt formatting (combining instruction + transcript chunk).
    #   Use the loaded `prompt_template` and format it with the chunk.
    # - Send prompt to chat_session.send_message().
    # - Display the LLM response (chat_session.last.text).
    # - Handle graceful shutdown (Ctrl+C).

    # Placeholder loop
    try:
        while True:
            logging.info("Main loop running (replace with actual logic)...")
            # Simulate work / receiving transcript (replace later)
            time.sleep(10)
            # Simulate asking LLM a question (replace later)
            # accumulated_chunk = "This is a sample accumulated transcript chunk." # Replace with real data
            # formatted_prompt = prompt_template.format(accumulated_transcript_chunk=accumulated_chunk)
            # response = chat_session.send_message(formatted_prompt)
            # logging.info(f"LLM Response (placeholder): {response.text}")

    except KeyboardInterrupt:
        logging.info("Shutdown signal received.")

    # 6. Cleanup
    logging.info("Cleaning up resources...")
    # TODO: Close transcription client connection?
    logging.info("DMS Assistant finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the DMS Helper assistant.")
    parser.add_argument("-c", "--campaign", required=True,
                        help="Path to the campaign JSON configuration file (e.g., source_materials/ceres_group/ceres_odyssey.json)")
    # Add other arguments later (e.g., transcription server details, model name?)

    args = parser.parse_args()

    # Basic check for config file existence
    if not Path(args.campaign).is_file():
        print(f"Error: Campaign configuration file not found at {args.campaign}")
    else:
        run_assistant(args.campaign) 