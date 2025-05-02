# D&D Helper Project Overview

This document provides a guide to the main files and structure of the D&D Helper project, intended to help developers understand the components after time away.

## Goal

The application listens to a Dungeon Master's voice, transcribes it in near real-time using Whisper, and uses Large Language Models (Ollama Gatekeeper + Cloud LLM like Gemini) to provide context-aware suggestions and assistance during gameplay.

## How to Run

The primary way to launch the application is via the GUI:

1.  Ensure the external Whisper and Ollama servers are running (see `SETUP_GUIDE.md`).
2.  Ensure the Python virtual environment (`.venv`) is activated.
3.  Run the GUI entry point: `python src/dms_gui.py`
4.  Alternatively, use the `run_dms_helper.bat` script, which activates the environment and runs `src/dms_gui.py`.

## Core Application Files (GUI Workflow)

*   **`src/dms_gui.py`**: The main entry point for the GUI application. It initializes the PyQt5 application, sets the style/palette, initializes the `LogManager`, and creates/shows the `MainWindow`.
*   **`src/main_window.py`**: Contains the `MainWindow` class (inherits from `QMainWindow`). This is the largest and most central file for the GUI. It defines the UI layout (using `QWebEngineView` for LLM output, `QTextEdit` for user speech, buttons, etc.), connects UI elements to functions (signals/slots), manages application state (like transcription status, audio source), initializes and interacts with backend components (ConfigManager, LLM, TranscriptionClient, Accumulator), and orchestrates the flow of data between transcription, processing, LLM calls, and UI updates.
*   **`src/config_manager.py`**: Defines the `ConfigManager` class. Responsible for loading settings from `config.json`, providing default values if the file or keys are missing, and saving updated settings back to `config.json`. Used by `MainWindow` and `LogManager`.
*   **`config.json`**: Stores application configuration settings like model names, server addresses, file paths, UI preferences, and the last audio playback position (`audio_settings.last_playback_position`).

## Supporting Modules

*   **`src/log_manager.py`**: Provides a centralized way to configure and access different loggers (application events, conversation history, raw transcript). Reads logging configuration potentially from `config.json`.
*   **`src/whisper_live_client/`**: Directory containing the WebSocket client for interacting with the WhisperLive transcription server.
    *   `client.py`: Defines `Client` (base WebSocket handler) and `TranscriptionClient` (wraps `Client`, handles audio playback from file or microphone input via PyAudio, manages the connection, and puts received transcript segments onto a queue).
    *   `utils.py`: Helper functions specifically for the `whisper_live_client`.
*   **`src/transcript_accumulator.py`**: Defines the `TranscriptAccumulator` class. Takes raw transcript segments (received from the transcription client via a queue), buffers them, and uses logic (like sentence detection via NLTK) to determine when a complete, coherent chunk of speech is ready for processing by the LLMs.
*   **`src/context_loader.py`**: Contains functions to load and combine context from various source files (specified in a campaign JSON file) for the main LLM. Uses `markdown_utils` for processing.
*   **`src/markdown_utils.py`**: Provides functions to convert Markdown text (received from the LLM) into HTML fragments suitable for display in the `QWebEngineView`. Also includes the base CSS (`DND_CSS`) used for styling the output.

## Configuration & Data Files/Folders

*   **`source_materials/`**: Contains subdirectories for different campaigns (e.g., `wednesday/`). Each campaign directory holds the context files (`.txt`, `.md`) for that campaign (adventure text, PC info, summaries) and a JSON file (e.g., `wednesday_campaign.json`) defining which context files belong to the campaign. Also contains the main audio recording file (`recording_of_dm_resampled.wav`).
*   **`logs/`**: Default directory where detailed log files are stored for each run (e.g., `raw_transcript_*.log`, `gemini_context_*.log`, `combined_session_*.log`). Contains an `archive/` subdirectory where logs from previous runs are moved.
*   **`prompts/`**: Stores the text files used as templates for prompting the LLMs (e.g., `dm_assistant_prompt.md`, `gatekeeper_prompt.md`).
*   **`css/`**: Contains CSS files (`dnd_style.css`) used to style the HTML rendered in the `QWebEngineView`.

## Archived Scripts (`src/_archive/`)

These scripts are not part of the main GUI application flow but are kept for reference or potential future use.

*   **`dms_assistant.py`**: A standalone, console-based version of the application core logic. It connects to transcription, loads context, interacts with LLMs, but outputs to the console/logs instead of a GUI. Likely an earlier version or backend test script.
*   **`convert_adventure_pdf.py`**: Utility script likely used to convert PDF adventure modules into Markdown format using the `marker-pdf` library, preparing them as context for the LLM.
*   **`render_md_to_pdf.py`**: Utility script, purpose less clear, possibly for converting Markdown back to PDF.
*   **`llm_test.py`**: Script likely used for directly testing API calls to the LLM services (Gemini, Ollama) independent of the main application flow.
*   **`main.py`**: Original purpose unknown, possibly an older entry point or test script before `dms_gui.py` was established.

## External Dependencies / Setup

*   **WhisperLive Server**: Requires a running instance of the WhisperLive Docker container (GPU recommended). See `SETUP_GUIDE.md`.
*   **Ollama Server**: Requires a running Ollama server (ideally on LAN) with the specified gatekeeper model (e.g., `mistral:latest`) pulled and configured for network access. See `SETUP_GUIDE.md`.
*   **API Keys**: Requires a Google API key for Gemini, configured via a `.env` file in the project root (`GOOGLE_API_KEY=...`).

## Future Plans

*   **GUI File Conversion**: Implement functionality within the GUI (`MainWindow`) to allow users to drag and drop files (starting with PDFs, potentially others like `.txt`, `.md`) directly onto the application. These files should then be processed/converted (e.g., PDF to Markdown using logic potentially adapted from `src/_archive/convert_adventure_pdf.py`) and added to the LLM's context for the current session.

## Other Important Files

*   **`run_dms_helper.bat`**: Batch script to conveniently activate the virtual environment and run the main GUI application (`src/dms_gui.py`).
*   **`requirements.txt`**: Lists the Python package dependencies required for the project. Install using `pip install -r requirements.txt`.
*   **`.env`**: (Not committed to Git) Stores sensitive API keys (like `GOOGLE_API_KEY`).
*   **`README.md`**: General project description, setup, and usage instructions (may need updating to reflect the GUI focus).
*   **`SETUP_GUIDE.md`**: Detailed instructions for setting up the external Whisper and Ollama servers.
*   **`checklist.md` / `requirements.md` / `handoff.md`**: Project planning and status tracking documents. 