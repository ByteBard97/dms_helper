# D&D Helper Project Overview

This document explains the high-level architecture, key modules, and directory layout of the **D&D Helper** project as of the latest refactor set (Task #29 – modular widgets **and** Task #28 – streaming LLM output).

---
## Goal
The application listens to a Dungeon Master's speech, transcribes it in near real-time via **Whisper Live**, then leverages **Ollama** (gatekeeper) and **Google Gemini** to generate context-aware suggestions that are rendered in a PyQt-based GUI.

---
## How to Run
1. Start the external servers (see `SETUP_GUIDE.md`)
   • Whisper Live (Docker)
   • Ollama (gatekeeper model pulled)
2. Activate the virtual environment: `venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (POSIX).
3. Launch the GUI: `python src/dms_gui.py`  
   `run_dms_helper.bat` can be used as a one-click helper.

> **Why `dms_gui.py`?**  The entry-point simply initialises logging & palette then instantiates **`MainWindow`**.  Keeping the bootstrap tiny allows the heavy logic to live inside the main modules which are hot-reloaded more often during development.

---
## Current Architecture Overview
```
┌─────────────┐   streamed chunks   ┌────────────────────┐
│ WhisperLive │ ───────────────▶   │ TranscriptAccumulator │
└─────────────┘                    └────────────┬───────┘
                                                │ finalised sentence
                                                ▼
                                           ┌──────────────┐
                                           │  LLMChain    │
                                           │ (Gatekeeper +│
                                           │   Gemini)    │
                                           └────────┬─────┘
                                                    │ markdown
                                                    ▼
                                           ┌─────────────────┐
                                           │ LLMOutputWidget │
                                           └─────────────────┘
```
*Speech → Transcription → Accumulation → Gatekeeper check → Gemini prompt → Streaming markdown → GUI*

---
## Core GUI Files
| Path | Purpose |
|------|---------|
| **`src/dms_gui.py`** | Entry-point: sets dark theme, initialises `LogManager`, shows `MainWindow`. |
| **`src/main_window.py`** | Orchestrator: glues controllers ↔ widgets, routes high-level signals, owns the top-level splitter. |
| **`src/llm_output_widget.py`** | `LLMOutputWidget(QWebEngineView)`. Renders assistant messages, supports streaming via JS injection, loads `templates/chat_template.html.tpl`. |
| **`src/user_speech_widget.py`** | `UserSpeechWidget(QTextEdit)`. Shows settled & hypothesis transcription with configurable font size / visibility toggle. |
| **`src/controls_widget.py`** | Bottom control bar. Groups audio/transcription/LLM param controls, DM-action panel, and manual prompt entry (`DMInputWidget`). Exposes high-level signals so `MainWindow` doesn't need to know about individual buttons. |
| **`src/dm_input_widget.py`** | Single-line prompt entry used inside `ControlsWidget` for ad-hoc DM commands. |
| **`src/dm_action_panel.py`** | Grid of quick-access buttons for common DM actions (treasure, NPC dialogue, etc.). |

### Controllers / Back-end Helpers
| Path | Description |
|------|-------------|
| **`src/llm_controller.py`** | Handles Gatekeeper → Gemini workflow, including *streaming* support (Task #28). Emits `stream_started`, `response_chunk_received`, `stream_finished`, plus `processing_started/finished`. |
| **`src/transcription_controller.py`** | Wraps Whisper client & accumulator, exposes signals for hypothesis/final text. |
| **`src/audio_controller.py`** | Manages audio source selection (file vs. mic) & persists choice in `config.json`. |
| **`src/log_manager.py`** | Centralised logging setup; creates structured log files per run. |
| **`src/config_manager.py`** | Reads/writes **`config.json`**, provides typed getters/setters. |

### Utilities & Support
* `src/context_loader.py` – Combines campaign context files for LLM prompts.  
* `src/markdown_utils.py` – Converts markdown → HTML (with `css/dnd_style.css`).
* `src/templates/chat_template.html.tpl` – Base HTML shell loaded by `LLMOutputWidget`.

---
## Key Data / Config Directories
| Dir | Contents |
|-----|----------|
| **`source_materials/`** | Campaign-specific context files and reference audio. |
| **`prompts/`** | Markdown prompt templates for Gatekeeper / Gemini. |
| **`logs/`** | Runtime logs; archived per session in `logs/archive/`. |
| **`css/`** | `dnd_style.css` – global D&D-flavoured styling. |
| **`tasks/`** | Taskmaster task files (`task_###.txt`, `tasks.json`). |

---
## External Services
* **Whisper Live** – Docker container for low-latency transcription.
* **Ollama** – Hosts the Gatekeeper model (e.g., `mistral`).
* **Google Gemini** – Cloud LLM for creative responses.

API keys are loaded from `.env` (see `requirements.md`).

---
## Recent Refactors (Task #29)
* Split giant `MainWindow` logic into **three reusable widgets** listed above.
* Moved inline HTML to `src/templates/chat_template.html.tpl` and styled via CSS.
* Added `ControlsWidget.set_controls_enabled` helper for centralised enable/disable logic.
* Audio source combo box now initialises from config to preserve *File* playback choice.
* Added configurable font size for transcription pane (`ui_settings.speech_font_size`).
* Legacy code preserved under `src/old/` for reference.
* Implemented real-time streaming of Gemini responses to the GUI via new signals in `LLMController` and JS updates in `LLMOutputWidget` (Task #28).

---
## Planned / Pending Work
* **Task #28 – Streaming Gemini Output** (in progress): leverage the new streaming signals in `LLMController` and dynamic DOM updates in `LLMOutputWidget` for real-time token display.
* Bottom control layout fine-tuning to align with the design spec (left column + 50%-width prompt under speech pane).

---
*Last updated: 2025-05-04 