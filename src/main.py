"""
Main entry point for the DMS Helper client application.
Connects to a WhisperLive server, streams microphone audio,
and prints transcriptions using the vendored client library.
"""

import sys
import logging
# Import from the sibling package within src
from whisper_live_client.client import TranscriptionClient 

# --- Configuration (Derived from previous audio_capture.py) ---
SERVER_HOST = "localhost"
SERVER_PORT = 9090
LANGUAGE = "en"          # Language ('en', 'es', etc.) or None for multilingual auto-detect
# TASK = "transcribe"    # Handled by setting translate=False below
MODEL_SIZE = "small.en"  # Whisper model size (e.g., "tiny", "base", "small", "medium", "large-v3")
USE_VAD = True           # Use server-side VAD (with server's default settings)
# --------------------------------------------------------------

# Optional: Configure logging level for the client library
# logging.basicConfig(level=logging.DEBUG) # Uncomment for more verbose logs

def run_whisperlive_client():
    """Initializes and runs the TranscriptionClient for microphone input."""
    print(f"Attempting to connect to WhisperLive server at ws://{SERVER_HOST}:{SERVER_PORT}")
    try:
        client = TranscriptionClient(
            host=SERVER_HOST,
            port=SERVER_PORT,
            lang=LANGUAGE,
            translate=False,     # Set to True to translate to English, False for transcription
            model=MODEL_SIZE,
            use_vad=USE_VAD,
            # --- Optional arguments based on README ---
            # save_output_recording=False,               # Set to True to save audio locally
            # output_recording_filename="./mic_output.wav", # Filename if saving
            # output_transcription_path="./mic_output.srt", # Default srt output path
            # log_transcription=True,                    # Print transcriptions to console
            # max_clients=4,                             # Max clients hint (server might override)
            # max_connection_time=600,                   # Max connection time hint (server might override)
        )
        print("Connection successful. Starting microphone transcription.")
        print("Press Ctrl+C to stop.")

        # This call starts listening to the microphone and blocks until interrupted
        # or the connection closes.
        client()

    except ConnectionRefusedError:
        print(f"\n[ERROR] Connection refused.")
        print(f"Please ensure the WhisperLive server is running on {SERVER_HOST}:{SERVER_PORT}")
        print(f"And that the port is accessible.")
    except KeyboardInterrupt:
        # This exception is expected when stopping with Ctrl+C
        # The client() call should handle its own cleanup internally
        print("\nTranscription stopped by user.")
    except Exception as e:
        # Catch-all for other potential errors during client operation
        print(f"\n[ERROR] An unexpected error occurred: {e}", file=sys.stderr)
        print("Check server logs for more details.")
        # Re-raise as per rules for debugging
        raise

if __name__ == "__main__":
    run_whisperlive_client()
    print("Client application finished.") 