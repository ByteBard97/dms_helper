# D&D Helper Assistant - Project Overview

This document provides a high-level overview of the D&D Helper Assistant project structure and functionality.

## Purpose

The application aims to assist Dungeon Masters during live D&D sessions by:
1.  Processing audio input (from a file or live microphone) via real-time transcription.
2.  Accumulating transcribed text into meaningful chunks.
3.  Sending these chunks, along with pre-loaded campaign context, to a Large Language Model (LLM - currently Google Gemini).
4.  Displaying the LLM's suggestions and responses, formatted as Markdown, in a dedicated UI panel.
5.  Providing quick-action buttons for common DM requests (generating NPCs, descriptions, loot, etc.) that leverage the current conversation context.

## Core Modules & Files (`src/`)

*   **`dms_gui.py`**:
    *   The main entry point for the application.
    *   Initializes logging (`LogManager`).
    *   Sets up the PyQt5 application instance.
    *   Applies a dark theme and Fusion style.
    *   Instantiates and shows the `MainWindow`.
    *   Handles the application event loop and clean exit.

*   **`main_window.py` (`MainWindow` class):**
    *   The core class managing the GUI and orchestrating interactions.
    *   **UI Setup:** Creates the main window, layouts (`QVBoxLayout`, `QHBoxLayout`, `QGridLayout`), `QSplitter` for side-by-side panes, `QWebEngineView` for LLM output, `QTextEdit` for user speech, and various control widgets (`QPushButton`, `QComboBox`, `QSpinBox`, `QCheckBox`).
    *   **Initialization:** Loads configuration (`ConfigManager`), initializes the LLM (`initialize_llm_and_gatekeeper`), `TranscriptAccumulator`, audio input source selection, DM action parameters, and queues (`segment_queue`, `chunk_queue`).
    *   **Audio/Transcription Control:** Handles starting (`start_audio_processing`) and stopping (`stop_audio_processing`) the transcription process. Manages the `TranscriptionClient` instance and its worker thread. Includes logic for selecting audio source (File/Microphone) and handling playback position for files.
    *   **Queue Monitoring:** Uses a monitor thread (`_monitor_transcription_queue`) to watch the `segment_queue` from the transcription client.
    *   **Transcription Handling:** Processes received transcription segments (`handle_transcription_result`), logs raw transcripts, updates the intermediate display (`update_user_speech_pane`), and feeds segments to the `TranscriptAccumulator`.
    *   **LLM Interaction:**
        *   Takes finalized chunks from the `chunk_queue` (`_maybe_process_next_input`).
        *   Handles DM quick action button clicks (`on_generate_npc_clicked`, etc.) via the `_trigger_dm_action` helper, loading specific prompts from the `prompts/` directory and formatting them.
        *   Sends formatted prompts/chunks to the LLM via `trigger_llm_request` in a background thread.
        *   Receives LLM responses via signal (`handle_llm_response`), logs them, and renders them.
    *   **Display:** Renders Markdown from the LLM using `markdown_utils` and displays it in the `QWebEngineView` (`append_markdown_output`). Updates the user speech pane with colorization (`update_user_speech_pane`).
    *   **Configuration:** Reads initial settings and saves changes (e.g., audio source, DM action parameters, checkbox states) back to `config.json`.

*   **`config_manager.py` (`ConfigManager` class):**
    *   Handles loading configuration settings from `config.json`.
    *   Provides methods (`get`, `set`) to access and modify settings.
    *   Handles saving updated configuration back to the file.

*   **`log_manager.py` (`LogManager` class):**
    *   Sets up and manages multiple loggers (application, conversation, raw transcript).
    *   Configures file handlers, formatting, and log rotation/archiving.
    *   Provides static methods for accessing logger instances.

*   **`context_loader.py` (`load_and_combine_context` function):**
    *   Reads a campaign configuration JSON file (specified in `config.json`).
    *   Reads the content of all source material files listed within that campaign JSON.
    *   Combines the content into a single string to be used as the initial context for the LLM session.

*   **`transcript_accumulator.py` (`TranscriptAccumulator` class):**
    *   Receives transcription segments.
    *   Uses NLTK for sentence tokenization.
    *   Buffers segments until minimum sentence/word counts are met.
    *   Returns finalized text chunks for LLM processing.
    *   Includes a `flush_buffer` method for manual triggering.

*   **`whisper_live_client/client.py` (`Client`, `TranscriptionTeeClient`, `TranscriptionClient` classes):**
    *   Handles communication with the external `whisper_live_server` via WebSockets.
    *   `Client`: Low-level WebSocket management, sending/receiving messages.
    *   `TranscriptionTeeClient`: Higher-level abstraction using PyAudio for audio I/O (file playback or microphone recording via `record()`), managing audio streams, handling chunking, and potentially multicasting to multiple servers (though used for one here). Tracks file playback position.
    *   `TranscriptionClient`: Wrapper around `TranscriptionTeeClient` specifically for a single client connection, used by `MainWindow`.

*   **`markdown_utils.py`:**
    *   Contains `markdown_to_html_fragment` function using the `mistune` library to convert Markdown text to an HTML fragment.
    *   Includes CSS string (`DND_CSS`) for styling the rendered HTML.

*   **`convert_adventure_pdf.py` (Utility Script):**
    *   Uses the `marker-pdf-parser` library to convert PDF files found in `source_materials/` into Markdown files, saving them in the same directory. Requires CUDA.

## Key Data & Configuration Files

*   **`config.json`**: Stores application settings (LLM model, paths, server addresses, UI/audio preferences, DM action defaults).
*   **`prompts/`**: Contains Markdown template files for:
    *   `dm_assistant_prompt.md`: The main prompt wrapping transcribed text chunks.
    *   `gatekeeper_prompt.md`: (Currently bypassed) For potential future use with a local LLM to filter input.
    *   `dm_action_*.md`: Specific prompts for the DM quick action buttons, using `{quantity}` and `{pc_level}` placeholders.
*   **`source_materials/`**: Holds the adventure context files (Markdown, Text). Includes subdirectories for specific campaigns (e.g., `monday/`). Contains campaign configuration JSON files (e.g., `monday_odyssey.json`) that list which source files to load for context.
*   **`logs/`**: Directory where log files (`app.log`, `session.log.jsonl`, `raw_transcript.log`) are stored. Includes `logs_archive/` for rotated logs.
*   **`css/`**: Contains `dnd_style.css` used for styling the Markdown rendered in the `QWebEngineView`.
*   **`start_whisper_server.bat`**: Batch file to simplify starting the Whisper Live Docker container.

## Basic Workflow / Data Flow

1.  **Startup:** `dms_gui.py` -> `LogManager` init -> `MainWindow` init -> `ConfigManager` load -> `initialize_llm_and_gatekeeper` (loads context, starts `ChatSession`).
2.  **Start Listening:** User selects Audio Source -> Clicks "Start Listening" -> `start_audio_processing` -> Initializes `TranscriptionClient` -> Starts client thread (`__call__` which runs `play_file` or `record`) -> Starts `_monitor_transcription_queue` thread.
3.  **Audio Processing:**
    *   `TranscriptionClient` reads audio (file/mic) -> Sends binary data via WebSocket to `whisper_live_server`.
    *   Server transcribes -> Sends segments back via WebSocket.
    *   `Client.on_message` receives segments -> Puts list onto `segment_queue`.
4.  **GUI Handling:**
    *   `_monitor_transcription_queue` gets segments from queue -> Emits `transcription_received` signal.
    *   `handle_transcription_result` slot receives segments -> Logs raw -> Emits `intermediate_transcription_updated` signal (for right pane) -> Calls `accumulator.add_segments`.
    *   `update_user_speech_pane` slot updates right pane display with settled/in-progress text.
5.  **Chunking & LLM Triggering (Transcript):**
    *   `accumulator` returns final chunk -> `handle_transcription_result` puts chunk on `chunk_queue`.
    *   `_maybe_process_next_input` gets chunk -> Appends to `settled_user_text` -> Updates display -> (Bypasses gatekeeper) -> Calls `trigger_llm_request`.
6.  **LLM Triggering (DM Action):**
    *   User clicks DM button -> `on_*_clicked` -> `_trigger_dm_action` -> Loads/formats specific prompt -> Calls `trigger_llm_request`.
7.  **LLM Interaction:**
    *   `trigger_llm_request` starts worker thread -> Calls `chat_session.send_message` (sends new prompt + history).
    *   Worker thread gets response -> Emits `llm_response_received` signal.
    *   `handle_llm_response` slot receives response -> Logs -> Calls `append_markdown_output`.
8.  **Output Rendering:**
    *   `append_markdown_output` calls `markdown_to_html_fragment` -> Runs JavaScript in `QWebEngineView` to append rendered HTML.

## Key Features Implemented

*   GUI framework using PyQt5 and QWebEngineView.
*   Configuration management via `config.json`.
*   Centralized logging.
*   Markdown rendering with custom CSS.
*   Integration with external Whisper Live server for transcription.
*   Audio input selection (File or Microphone).
*   Audio file playback position saving/resuming.
*   Transcription accumulation into sentences/chunks.
*   Integration with Google Gemini LLM via `google-generativeai` SDK.
*   Loading initial adventure context from files.
*   Separate display pane for user speech with settled/in-progress color distinction.
*   Manual flushing of the transcript accumulator.
*   DM Quick Action buttons with parameter inputs (Level, Quantity) and specific prompts. 