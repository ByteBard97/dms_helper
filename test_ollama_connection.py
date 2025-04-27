"""
Simple script to test the connection to the Ollama server.
Usage: python test_ollama_connection.py
"""

import ollama
import logging

# --- Configuration ---
# Make sure this matches the host and port where your Ollama server is running
# This was provided by the user in an earlier code snippet.
OLLAMA_HOST = "http://192.168.0.200:11434"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Test Function ---
def test_ollama_connection():
    """Attempts to connect to the Ollama server and list models."""
    logging.info(f"Attempting to connect to Ollama server at: {OLLAMA_HOST}")

    # Using ollama.Client directly as recommended
    client = ollama.Client(host=OLLAMA_HOST)

    # According to the Ollama Python library documentation,
    # list() is a simple way to check if the server is reachable and responding.
    # We don't need try/except per project rules. If it fails, it will raise an exception.
    logging.info("Sending request to list models...")
    response = client.list() # This will raise ollama.RequestError if connection fails
    logging.info("Successfully connected to Ollama server.")
    logging.info("Available models:")
    if response and isinstance(response.get('models'), list):
        if not response['models']:
             logging.warning("No models listed by the server.")
        for model in response['models']:
             # --- Debugging lines (can keep or remove) ---
             logging.info(f"Found model entry: {model}")
             logging.info(f"Type of model entry: {type(model)}")
             # --- CORRECTED line using attribute access ---
             model_name = model.model
             modified_time = model.modified_at # Also use attribute access here
             logging.info(f"- Name: {model_name} (Modified: {modified_time})") # Use the variables
    else:
        logging.warning(f"Models list not found or not a list in response. Response: {response}")

    logging.info("Ollama connection test successful!")
    # ... rest of the script ...


# --- Main Execution ---
if __name__ == "__main__":
    test_ollama_connection() 