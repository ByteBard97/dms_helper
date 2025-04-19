# D&D Helper - Project Requirements

## 1. Project Goal

To create a desktop application that listens to a Dungeon Master's (DM) voice during a Dungeons & Dragons game, transcribes it in near real-time using Whisper, and feeds the transcription to a Large Language Model (LLM). The LLM will use provided context (DM notes, adventure details, player character information) to generate helpful suggestions, descriptions, NPC dialogue/actions, treasure ideas, and other "dungeon dressing" details to assist the DM during the live game session.

## 2. Core Features

*   **Real-time Audio Input:** Capture audio from a selected microphone input device.
*   **Real-time Transcription:** Transcribe the captured audio stream using a GPU-accelerated Whisper model with low latency (target < 5 seconds, ideally 1-2 seconds). Initially, focus only on the DM's voice.
*   **Context Loading:** Load initial context provided by the user at startup (DM notes, adventure chapters, PC info). Assume static context for the initial version.
*   **LLM Integration:**
    *   Send transcribed text, along with loaded context and conversational history, to an LLM API (starting with Gemini 2.5 Pro).
    *   Design the LLM interaction to be modular, allowing different LLM backends to be swapped in the future.
    *   Maintain conversational context with the LLM to avoid resending static information repeatedly.
*   **LLM Triggering:** Implement multiple methods for triggering LLM generation:
    *   Manual trigger (e.g., button press).
    *   Automatic trigger after a significant pause in speech (using VAD).
    *   Time-based trigger (e.g., every X seconds of speech).
    *   Keyword/phrase trigger (e.g., "Okay assistant, ...").
    *   *Requires experimentation to determine the most effective methods during gameplay.*
*   **Output Display:**
    *   Display the LLM-generated suggestions in a simple Graphical User Interface (GUI).
    *   The GUI should feature a scrolling text area.
    *   Render the LLM output as Markdown for better readability.
*   **Manual LLM Interaction:** Allow the user to pause the real-time processing and manually type questions or instructions to the LLM via the GUI.

## 3. Non-Functional Requirements

*   **Performance:** Prioritize low latency for transcription and LLM response generation (target < 5s total turnaround).
*   **Hardware:** Optimized for running on Windows 10/11 with an NVIDIA GPU (specifically tested with RTX 4070) using CUDA.
*   **Modularity:** Code should be structured to allow swapping components, particularly the LLM backend.
*   **Usability:** The GUI should be simple and clear, providing essential controls (start/stop, manual input) and readable output.

## 4. Technology Stack (Initial Proposal)

*   **Language:** Python (latest stable version)
*   **Audio Input:** `sounddevice` or `pyaudio`
*   **Real-time Transcription:** `ufal/whisper_streaming` (using `faster-whisper` backend with GPU/CUDA)
*   **LLM API Client:** Google Generative AI SDK for Python (`google-generativeai`)
*   **GUI:** `PyQt6` or `PySide6` (Good Markdown support, mature) or `Dear PyGui` (Potentially simpler for real-time updates) - *Decision TBD*.
*   **Markdown Rendering:** Built-in capabilities of the chosen GUI library or a library like `Markdown`.

## 5. Input / Output Formats

*   **Context Input:** Plain text files (.txt) or Markdown files (.md) for DM notes, adventure chapters, and PC information. A simple file structure or naming convention will be needed (e.g., `context/notes.md`, `context/adventure/chapter1.md`, `context/pcs.md`).
*   **Transcription Output (Internal):** String data passed from the transcription module to the LLM interaction module.
*   **LLM Output:** Markdown formatted text displayed in the GUI.

## 6. Future Considerations

*   **Player Transcription:** Add capability to transcribe player voices (requires speaker diarization or separate inputs).
*   **Dynamic Context:** Allow adding/updating context information during a running session.
*   **Advanced GUI:** More sophisticated interface features (e.g., managing multiple suggestion threads, context editing).
*   **Configuration:** Allow users to easily configure model sizes, API keys, audio devices, trigger thresholds, etc.
*   **Alternative LLMs:** Add support for other local or cloud-based LLMs.
*   **Packaging:** Create an executable package for easier distribution. 