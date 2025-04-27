# D&D Helper

![D&D Logo Placeholder](https://via.placeholder.com/150/000000/FFFFFF?text=D%26D+Helper) <!-- Optional: Add a real logo later -->

A real-time transcription and AI assistance tool for Dungeon Masters running Dungeons & Dragons games.

## Goal

This application listens to the DM's voice during a game session, transcribes it in near real-time using Whisper, and leverages a Large Language Model (LLM) to provide helpful suggestions, descriptions, NPC dialogue ideas, and other details based on pre-loaded context (notes, adventure book, character info).

## Core Technologies

*   Python 3.10+
*   Whisper (via WhisperLive Docker container using `faster-whisper` backend)
*   Large Language Models (Google Gemini API - `gemini-1.5-flash` currently)
*   Local LLM Gatekeeper (Ollama with `mistral:latest` currently)
*   GUI (Planned: **PyQt6**)
*   License: MIT (see `LICENSE` file)

## Features (Planned)

*(Details outlined in `requirements.md` and `checklist.md`)*

*   Real-time GPU-accelerated transcription of DM's voice (via file playback currently).
*   Context-aware LLM suggestions based on user-provided notes.
*   Local LLM gatekeeper to filter transcript chunks before sending to the cloud LLM.
*   Markdown rendering of LLM output in a simple GUI (Next Step).
*   Manual and automatic triggering for LLM interaction (Future Phase).

## Setup

1.  Clone the repository.
2.  Create and **activate** the Python virtual environment (`.venv`):
    ```bash
    # Create the venv (using your Python 3.10+)
    python -m venv .venv
    # Activate (Windows PowerShell)
    .\.venv\Scripts\Activate.ps1
    # Or Activate (Bash/Git Bash/MacOS)
    # source .venv/bin/activate
    ```
    **Note:** Ensure the virtual environment is active in your terminal for all subsequent steps.
3.  Install dependencies (requires CUDA/cuDNN):
    ```bash
    # Make sure pip is up-to-date in the venv
    python -m pip install --upgrade pip
    # Install requirements
    pip install -r requirements.txt
    ```
4.  **Configure External Servers:**
    *   Set up and run the **WhisperLive Docker container** (using GPU). See `SETUP_GUIDE.md` for details.
    *   Set up and run an **Ollama server** (ideally on a separate machine on the LAN) with the `mistral:latest` model pulled. Configure it for LAN access. See `SETUP_GUIDE.md` for details.
5.  **Configure API Keys:**
    *   Create a `.env` file in the project root.
    *   Add your Google API key: `GOOGLE_API_KEY=YOUR_API_KEY_HERE`
6.  **(First Run Only) NLTK Data:**
    *   The NLTK `punkt` tokenizer data will be downloaded automatically the first time the script requires it.

## Usage

1.  Ensure the WhisperLive Docker container is running.
2.  Ensure the Ollama server is running and accessible (check `OLLAMA_HOST` in `src/dms_assistant.py` if needed).
3.  Prepare context files in `source_materials/` and ensure they are listed in the campaign JSON file (e.g., `source_materials/ceres_group/ceres_odyssey.json`).
4.  Activate the virtual environment (`.venv`).
5.  Run the main application script:
    ```bash
    python src/dms_assistant.py
    ```
6.  The script currently uses hardcoded paths for the campaign config and input audio file.
7.  Transcription will begin, and suggestions from Gemini (filtered by the gatekeeper) will be **printed to the console**. GUI display is the next major feature planned.

## Contributing

*(Contribution guidelines can be added later)* 