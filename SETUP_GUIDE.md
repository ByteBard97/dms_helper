# Project Setup Guide

This document provides instructions for setting up the necessary external servers and dependencies for the DMS Helper project.

## Whisper Live Transcription Server (Docker GPU)

**Goal:** Run the Whisper Live transcription server locally using Docker and leverage the GPU for faster processing.

**Prerequisites:**

*   Docker Desktop installed and running.
*   NVIDIA GPU with appropriate drivers installed.
*   NVIDIA Container Toolkit installed and configured for Docker. (Refer to NVIDIA documentation for setup).

**Steps:**

1.  **Ensure No Conflicting Container is Running:**
    *   Open a terminal or PowerShell.
    *   Check for existing `whisperlive-gpu` containers:
        ```bash
        docker ps --filter ancestor=ghcr.io/collabora/whisperlive-gpu:latest
        ```
    *   If any container is listed, stop it using its ID:
        ```bash
        docker stop <container_id>
        ```

2.  **Run the Whisper Live GPU Container:**
    *   In the same terminal, run the following command **the first time**:
        ```bash
        docker run -it --gpus all -p 9090:9090 --name whisperlive_server ghcr.io/collabora/whisperlive-gpu:latest
        ```
    *   Flags explanation:
        *   `-it`: Run interactively (attach terminal, show output).
        *   `--gpus all`: Make all available GPUs accessible to the container (requires NVIDIA Container Toolkit).
        *   `-p 9090:9090`: Map port 9090 on your host machine to port 9090 inside the container.
        *   `--name whisperlive_server`: Assigns a fixed name to the container for easier management.
        *   `ghcr.io/collabora/whisperlive-gpu:latest`: The specific Docker image to use.
    *   **Note:** The first time you run this, it will download the Whisper model files, which may take several minutes.

3.  **Stopping the Server:**
    *   To stop the server, go back to the terminal where it's running and press `Ctrl+C`. The container will stop but will *not* be removed.

4.  **Restarting the Server (After First Run):**
    *   Open a terminal or PowerShell.
    *   Start the existing container:
        ```bash
        docker start -ai whisperlive_server
        ```
    *   Flags explanation:
        *   `start`: Command to start a stopped container.
        *   `-a`: Attach `STDOUT`/`STDERR` and forward signals.
        *   `-i`: Attach `STDIN`.
    *   This will reuse the container with the already downloaded model, making startup much faster.
    *   To stop it again, use `Ctrl+C`.

5.  **Cleanup (Optional):**
    *   If you want to completely remove the container (e.g., to force a fresh download or update), first ensure it's stopped, then run:
        ```bash
        docker rm whisperlive_server
        ```

## Ollama Gatekeeper Server (LAN Setup)

**Goal:** Run an efficient LLM (Mistral 7B) locally on a separate Linux machine to act as a "gatekeeper" for transcript chunks, accessible over the local network.

**Prerequisites:**

*   Dedicated Linux machine (e.g., with RTX 5080 w/ 16GB+ VRAM).
*   NVIDIA Drivers installed and working on the Linux machine.
*   (Recommended) Compatible CUDA Toolkit installed system-wide on the Linux machine.
*   Client machine (e.g., with RTX 4070) on the same local network.

**Steps:**

1.  **Install Ollama (on Linux Server):**
    *   Use the official installation script in the terminal:
        ```bash
        curl -fsSL https://ollama.com/install.sh | sh
        ```
    *   This installs the `ollama` command-line tool and usually sets up a systemd service (`ollama.service`) to run the server in the background.

2.  **Download the Gatekeeper Model (on Linux Server):**
    *   Choose an appropriate model. We selected `mistral:latest` (Mistral 7B Instruct, Q4_0 quantization) as a good balance of capability and efficiency for ~16GB VRAM.
    *   Pull the model using the Ollama CLI:
        ```bash
        ollama pull mistral:latest
        ```
        *(Alternatively, pull a specific quantization like 8-bit: `ollama pull mistral:q8_0`)*

3.  **Configure Ollama for LAN Access (on Linux Server):**
    *   Edit the systemd service override file to allow network connections:
        ```bash
        sudo systemctl edit ollama.service
        ```
    *   Add the following lines in the editor that opens:
        ```ini
        [Service]
        Environment="OLLAMA_HOST=0.0.0.0"
        ```
    *   Save the file and exit the editor. This typically creates/modifies `/etc/systemd/system/ollama.service.d/override.conf`.
    *   Reload the systemd configuration:
        ```bash
        sudo systemctl daemon-reload
        ```
    *   Restart the Ollama service to apply the changes:
        ```bash
        sudo systemctl restart ollama.service
        ```

4.  **Verify Server Setup (on Linux Server):**
    *   Check the service status:
        ```bash
        sudo systemctl status ollama.service
        ```
        *(Ensure it shows "active (running)" and the override file is loaded).*
    *   Test local API access:
        ```bash
        curl http://localhost:11434/api/tags
        ```
        *(Should return JSON listing the pulled models).*
    *   Find the server's local IP address:
        ```bash
        ip addr show
        ```
        *(Note the `inet` address of the active network interface, e.g., `192.168.0.200`).*

5.  **Client Machine Setup (Your DMS Helper Machine):**
    *   On the machine running the main Python project (`dms_assistant.py`):
        *   Activate the project's Python virtual environment (e.g., `.venv\Scripts\activate`).
        *   Ensure the Ollama Python library is installed:
            ```bash
            pip install ollama
            ```
        *   In the Python code (`src/dms_assistant.py`), configure the client to use the Linux server's IP address. Update the `OLLAMA_HOST` constant:
            ```python
            # Example (replace with the actual IP from Step 4)
            OLLAMA_HOST = "http://192.168.0.200:11434" 
            ```
        *   The code already initializes the client using this constant:
            ```python
            ollama_client = ollama.Client(host=OLLAMA_HOST)
            ```
        *   The code uses `ollama_client.generate(...)` to send requests, specifying the desired model name (e.g., `model='mistral:latest'`). 