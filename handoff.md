# Project Handoff: D&D Helper

**Overall Goal:** To create a real-time D&D assistant that listens to the DM's narration via microphone (currently simulated via file playback), processes the transcript, uses it along with pre-loaded campaign context to query a large language model (Gemini), and displays helpful suggestions or information back to the DM in a styled GUI.

---

**Date:** 2025-04-28 (End of Session)

**Recent Activity (This Session):**

1.  **GUI Implementation (PyQt5):**
    *   Created core GUI files: `src/dms_gui.py` (main execution), `src/main_window.py` (QMainWindow logic).
    *   Used `QWebEngineView` for the main display area to render HTML.
    *   Added basic buttons ("Start", "Stop") and a checkbox ("Show User Speech").
    *   Implemented logic to load initial HTML structure and CSS (`css/dnd_style.css`).
    *   Added test buttons for rendering sample Markdown.
2.  **Logging Overhaul:**
    *   Integrated `LogManager` (`src/log_manager.py`) for centralized logging config.
    *   Replaced most `print` statements with calls to appropriate loggers (`app_logger`, `conv_logger`, `raw_transcript_logger`).
    *   Implemented JSONL format for conversation history (`logs/session.log.jsonl`) capturing USER and ASSISTANT turns.
    *   Implemented separate logging for raw transcription segments (`logs/raw_transcript.log`).
    *   Configured log file archiving.
3.  **Transcription Client Integration & Playback Persistence:**
    *   Integrated `TranscriptionClient` (`src/whisper_live_client/client.py`) with the GUI.
    *   Modified client to accept `start_time` for playback.
    *   Implemented `get_current_playback_position`.
    *   Added logic in `MainWindow` to save the last playback position to `config.json` on stop and load it on start.
4.  **Markdown Rendering:**
    *   Created `src/markdown_utils.py` with `markdown_to_html_fragment`.
    *   Implemented `append_markdown_output` in `MainWindow` to render and display HTML in the `QWebEngineView`.
5.  **Processing Logic Refactoring & Debugging:**
    *   Refactored `_maybe_process_next_input` multiple times to handle chunk processing, gatekeeper logic (now bypassed), and LLM triggering.
    *   Introduced and fixed several `AttributeError` issues related to `TranscriptAccumulator` and method calls.
    *   Adjusted queue handling between `handle_transcription_result` and `_maybe_process_next_input`.

**Current Status:**

*   The application launches, initializes components, and loads configuration/context.
*   Transcription client connects, plays audio from the saved position, and produces transcript chunks via the `TranscriptAccumulator`.
*   Chunks are logged correctly to `raw_transcript.log`.
*   The processing logic (`_maybe_process_next_input`) *is* being triggered for these chunks (logs confirm this).
*   Conversation logging to `session.log.jsonl` appears functional for USER turns.
*   **Core Issue:** Despite chunks being processed, **no text (neither user chunks nor LLM responses) is appearing in the main GUI (`QWebEngineView`)**. The calls to `append_user_speech` and `append_markdown_output` seem to be missing or faulty in the current `_maybe_process_next_input` / `handle_llm_response` flow. The LLM response handling path might also be broken, as no ASSISTANT logs or GUI updates were seen in the last run.
*   The Ollama gatekeeper check is currently bypassed.

**Next Steps (Immediate - For New Session):**

1.  **Debug GUI Updates:**
    *   Trace the execution flow from when a chunk is retrieved in `_maybe_process_next_input` to when `append_user_speech` should be called. Verify it *is* called and the `user_text` is correct.
    *   Trace the flow from `trigger_llm_request` through the `llm_worker_func`, the `llm_response_received.emit`, to `handle_llm_response`. Verify the signal is emitted/received correctly.
    *   Verify `append_markdown_output` is called within `handle_llm_response` and the `response_markdown` is correct.
    *   Inspect the JavaScript logic within `append_user_speech` and `append_markdown_output` for potential errors preventing DOM updates in the `QWebEngineView`.
2.  **Restore Gatekeeper:** Once GUI updates are reliably working, uncomment and test the gatekeeper logic in `_maybe_process_next_input`.
3.  **Continue Checklist:** Proceed with remaining Phase 4 GUI items (styling, etc.).

---

## Previous Handoff (2025-04-27 - End of Session)

**Date:** 2025-04-27

**Recent Activity:**

1.  **Whisper Live Docker Server Setup:**
    *   Resolved issues with running the `ghcr.io/collabora/whisperlive-gpu:latest` Docker container (command-line args, model re-downloads).
    *   Documented the correct `docker run` command (no `--rm`, added `--name`) in `SETUP_GUIDE.md`.
    *   Added instructions for initial run vs. restart (`docker start -ai whisperlive_server`) to prevent model re-downloads.
    *   Created `scripts/start_whisper_server.ps1` to automate starting the container.

2.  **Python Script (`src/dms_assistant.py`) Debugging:**
    *   Fixed a `KeyError: 'accumulated_transcript_chunk'` by updating the placeholder in `prompts/dm_assistant_prompt.md` to `{transcript_chunk}`.
    *   Added logging to display the text chunk sent to the Ollama gatekeeper.

**Current Status:**

*   The `src/dms_assistant.py` script runs past the `KeyError`.
*   The full pipeline (Transcription -> Accumulation -> Gatekeeper Check) is functional.
*   **The main call to the Gemini LLM API remains commented out/skipped** within `src/dms_assistant.py` (see `TODO` block around line 358).
*   The Ollama gatekeeper is successfully classifying chunks and returning 'YES' appropriately.

**Next Steps (Immediate):**

*   Implement the actual call to the Gemini LLM (`chat_session.send_message()`) within the `if gatekeeper_decision == "YES":` block in `src/dms_assistant.py`.
*   Process and display/log the response from the Gemini LLM.
*   Continue working through the `checklist.md` Phase 3 items.

**Running the Project (as of 2025-04-20):**

1.  Python 3.10+, venv, `pip install -r requirements.txt`.
2.  Ensure WhisperLive server is running.
3.  Ensure Ollama server is running on `192.168.0.200:11434` with `mistral:latest`.
4.  Create `.env` with `GOOGLE_API_KEY`.
5.  Run `python src/dms_assistant.py`.

**Future Considerations (as of 2025-04-20):**

*   Argument parsing.
*   Live microphone input.
*   GUI.
*   Gemini API context caching.
*   Gatekeeper refinement.
*   Forced chunk flushing.

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
*   **`/prompts/`**: Contains prompt template files.
    *   `dm_assistant_prompt.md`: The main prompt for the Gemini assistant.
    *   `gatekeeper_prompt.md`: The prompt used by the local Ollama gatekeeper model to classify transcript chunk relevance.
*   `requirements.txt`: Lists Python dependencies. Includes `nltk`, `google-generativeai`, and `ollama`.
*   `checklist.md`: Tracks progress through different project phases.
*   `.env`: Stores the `GOOGLE_API_KEY` (must be created manually).
*   `.gitignore`: Standard git ignore file.
*   `rules.mdc`: Cursor rules for coding conventions (NO try/except blocks!).
*   `test_ollama_connection.py`: Simple script to verify the connection to the Ollama server.

**Next Steps (Immediate):**

The immediate priority is to integrate the Ollama gatekeeper and enable/test the conditional LLM interaction loop:

1.  **Integrate Ollama Gatekeeper:** Modify `src/dms_assistant.py`:
    *   Add Ollama client initialization (connecting to `http://192.168.0.200:11434`).
    *   Load the gatekeeper prompt from `prompts/gatekeeper_prompt.md`.
    *   Inside the main loop, after a transcript chunk is accumulated, call the Ollama client (`mistral:latest` model) with the chunk and the gatekeeper prompt.
    *   Parse the 'YES'/'NO' response from the gatekeeper.
2.  **Conditional LLM Communication:** Modify `src/dms_assistant.py` so that the code sending the `accumulated_chunk` (within the formatted main prompt) to the `chat_session.send_message()` is executed **only if** the gatekeeper responded with 'YES'.
3.  **Display LLM Response:** Add code within the conditional block (after the Gemini call) to print or log the response received from `chat_session.send_message()`.
4.  **Test End-to-End Flow:** Run the script with the gatekeeper and conditional LLM calls enabled. Verify the entire pipeline (Transcription -> Accumulation -> Gatekeeper -> Optional LLM Query -> Response Display) works using the test audio file. Check that the gatekeeper correctly filters chunks and Gemini is only called when expected.
5.  **(Post-Testing) Refine Prompts/Chunking/Gatekeeper:** Based on the observed results, potentially adjust:
    *   The main prompt template (`prompts/dm_assistant_prompt.md`).
    *   The gatekeeper prompt (`prompts/gatekeeper_prompt.md`).
    *   The `TranscriptAccumulator` settings (`MIN_SENTENCES_PER_CHUNK`, `MIN_WORDS_PER_CHUNK`).
    *   The gatekeeper model or its parameters (`temperature`, etc.) if needed.

**Running the Project:**

1.  Ensure Python 3.10+ is installed.
2.  Create and activate a virtual environment (e.g., `python -m venv .venv`, `source .venv/bin/activate` or `.\\.venv\\Scripts\\activate`).
3.  Install dependencies: `pip install -r requirements.txt`.
4.  Ensure the WhisperLive server is running locally (or adjust server address in `dms_assistant.py`).
5.  **Ensure the Ollama server is running** on `192.168.0.200:11434` and the `mistral:latest` model is available.
6.  Create a `.env` file in the project root with your `GOOGLE_API_KEY=YOUR_API_KEY_HERE`.
7.  The NLTK 'punkt' data should download automatically on the first run if needed.
8.  Run the main script: `python src/dms_assistant.py`. (Currently uses hardcoded paths for config and audio).

**Future Considerations (from `checklist.md`):**

*   Implement argument parsing for audio file path and Ollama host.
*   Add live microphone input mode.
*   Develop a GUI.
*   Investigate Gemini API context caching.
*   Refine the local Ollama gatekeeper's effectiveness and explore alternatives if needed.
*   Implement forced chunk flushing via keyword/button. 