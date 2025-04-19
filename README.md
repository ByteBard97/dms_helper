# D&D Helper

![D&D Logo Placeholder](https://via.placeholder.com/150/000000/FFFFFF?text=D%26D+Helper) <!-- Optional: Add a real logo later -->

A real-time transcription and AI assistance tool for Dungeon Masters running Dungeons & Dragons games.

## Goal

This application listens to the DM's voice during a game session, transcribes it in near real-time using Whisper, and leverages a Large Language Model (LLM) to provide helpful suggestions, descriptions, NPC dialogue ideas, and other details based on pre-loaded context (notes, adventure book, character info).

## Core Technologies

*   Python 3.10+
*   Whisper (via `ufal/whisper_streaming` and `faster-whisper`)
*   Large Language Models (initially Google Gemini API)
*   Real-time Audio Processing (`sounddevice`)
*   GUI (TBD - likely PyQt or Dear PyGui)
*   License: MIT (see `LICENSE` file)

## Features (Planned)

*(Details outlined in `requirements.md`)*

*   Real-time GPU-accelerated transcription of DM's voice.
*   Context-aware LLM suggestions based on user-provided notes.
*   Markdown rendering of LLM output in a simple GUI.
*   Manual and automatic triggering for LLM interaction.

## Setup

*(Instructions will be added here)*

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
3.  Install dependencies (see `requirements.txt` - requires CUDA/cuDNN):
    ```bash
    # Make sure pip is up-to-date in the venv
    python -m pip install --upgrade pip
    # Install vendored library (if necessary - currently whisper_streaming)
    # pip install git+https://github.com/ufal/whisper_streaming # (Doesn't work directly)
    # Instead, clone it into vendor/ (already done)
    # Install requirements
    pip install -r requirements.txt
    ```
4.  Configure API keys (if necessary).

## Usage

*(Instructions will be added here)*

1.  Prepare context files (notes, adventure details, PC info).
2.  Run the main application script.
3.  Select audio input device.
4.  Start the transcription/assistance process.

## Contributing

*(Contribution guidelines can be added later)* 