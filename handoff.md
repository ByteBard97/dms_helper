# Project Handoff: D&D Helper

**Date:** 2025-04-20

**Overall Goal:** To create a real-time D&D assistant that listens to the DM's narration via microphone (currently simulated via file playback), processes the transcript, uses it along with pre-loaded campaign context to query a large language model (Gemini), and displays helpful suggestions or information back to the DM.

**Current Status:**

*   **Phase:** We are actively working on **Phase 3: Integration & Interaction** (see `checklist.md`).
*   **Recent Progress:**
    *   The core application script (`src/dms_assistant.py`) is set up.
    *   Context loading from campaign files (`source_materials/`) via `context_loader.py` is implemented and working.
    *   The Gemini LLM (`google.generativeai`) is initialized and starts a chat session with the loaded context.
    *   Transcription input via file playback (`src/whisper_live_client/client.py`) is integrated. It uses a queue to send transcript segments to the main application.
    *   **Transcript Accumulation (`src/transcript_accumulator.py`) has been significantly reworked and is now functional:**
        *   It uses `nltk` for robust sentence boundary detection.
        *   It accumulates text based on *completed* segments from the transcription client.
        *   It chunks the transcript based on a minimum sentence count (3) AND a minimum word count (50).
    *   The most recent commit (`fea88c2`) integrates NLTK and fixes the transcript chunking issues.
*   **Current State:** The pipeline successfully transcribes the audio file, accumulates the transcript into meaningful chunks using NLTK, and logs these chunks along with the formatted prompt template. However, **the chunks are NOT yet being sent to the Gemini LLM API, and no LLM responses are being displayed.** The LLM call is currently commented out/skipped in `src/dms_assistant.py` for testing purposes.

**Project Structure & Key Files:**

*   **`/src/`**: Main Python source code.
    *   `dms_assistant.py`: The main application entry point and processing loop. Coordinates other components.
    *   `transcript_accumulator.py`: Class responsible for buffering transcript segments and creating meaningful chunks using NLTK.
    *   `context_loader.py`: Handles loading and combining context files specified in the campaign config.
    *   `convert_adventure_pdf.py`: Utility script (Phase 2) to convert source PDFs to Markdown using `marker-pdf`.
    *   `whisper_live_client/`: Vendored/modified client library for interacting with the WhisperLive transcription server.
        *   `client.py`: Contains `TranscriptionClient` and the core WebSocket communication logic.
        *   `utils.py`: Helper functions for the client.
*   **`/source_materials/`**: Contains campaign-specific context files.
    *   `*/<campaign_name>.json`: Campaign configuration file (e.g., `ceres_group/ceres_odyssey.json`) listing context files.
    *   `*.md`, `*.txt`: Markdown and text files containing adventure details, PC info, world lore, etc.
    *   `*.pdf`: Original source PDFs (used by `convert_adventure_pdf.py`).
    *   `*.wav`, `*.flac`: Audio files for transcription (playback testing). Currently using `recording_of_dm_resampled.wav`.
*   **`/logs/`**: Directory where detailed session logs are saved (raw transcript, prompts, responses, combined session).
*   **`/prompts/`**: Contains prompt template files (e.g., `dm_assistant_prompt.md`).
*   `requirements.txt`: Lists Python dependencies. Includes `nltk`.
*   `checklist.md`: Tracks progress through different project phases.
*   `.env`: Stores the `GOOGLE_API_KEY` (must be created manually).
*   `.gitignore`: Standard git ignore file.
*   `rules.mdc`: Cursor rules for coding conventions (NO try/except blocks!).

**Next Steps (Immediate):**

The immediate priority is to enable and test the LLM interaction loop:

1.  **Enable LLM Communication:** Modify `src/dms_assistant.py` to uncomment/add the code that sends the `accumulated_chunk` (within the formatted prompt) to the initialized `chat_session.send_message()`.
2.  **Display LLM Response:** Add code within the loop to print or log the response received from `chat_session.send_message()`.
3.  **Test End-to-End Flow:** Run the script with the LLM calls enabled and verify the entire pipeline (Transcription -> Accumulation -> LLM Query -> Response Display) works using the test audio file.
4.  **(Post-Testing) Refine Prompts/Chunking:** Based on the observed LLM responses, potentially adjust the prompt template (`prompts/dm_assistant_prompt.md`) or the `TranscriptAccumulator` settings (`MIN_SENTENCES_PER_CHUNK`, `MIN_WORDS_PER_CHUNK`) if needed.

**Running the Project:**

1.  Ensure Python 3.10+ is installed.
2.  Create and activate a virtual environment (e.g., `python -m venv .venv`, `source .venv/bin/activate` or `.\.venv\Scripts\activate`).
3.  Install dependencies: `pip install -r requirements.txt`.
4.  Ensure the WhisperLive server is running locally (or adjust server address in `dms_assistant.py`).
5.  Create a `.env` file in the project root with your `GOOGLE_API_KEY=YOUR_API_KEY_HERE`.
6.  The NLTK 'punkt' data should download automatically on the first run if needed.
7.  Run the main script: `python src/dms_assistant.py`. (Currently uses hardcoded paths for config and audio).

**Future Considerations (from `checklist.md`):**

*   Implement argument parsing for audio file path.
*   Add live microphone input mode.
*   Develop a GUI.
*   Investigate Gemini API context caching.
*   Implement local LLM/classifier pre-filter for cost optimization.
*   Implement forced chunk flushing via keyword/button. 