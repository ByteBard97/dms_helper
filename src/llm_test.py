"""
Simple test script for Google Gemini API integration.

1. Loads the API key from the .env file.
2. Performs a basic non-chat generation request.
3. Demonstrates the chat functionality with history persistence.
"""

import os
import logging
from typing import List, Dict, Optional

from dotenv import load_dotenv
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_api_key() -> Optional[str]:
    """Loads the Google API key from the .env file."""
    load_dotenv()
    api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logging.error("GOOGLE_API_KEY not found in environment variables.")
        logging.error("Please ensure you have a .env file in the project root with GOOGLE_API_KEY=YOUR_KEY")
        return None
    logging.info("Google API Key loaded successfully.")
    return api_key

def test_simple_generation(model: genai.GenerativeModel):
    """Tests a single, non-chat generation request."""
    logging.info("--- Testing Simple Generation ---")
    prompt: str = "Explain the concept of 'Alignment' in Dungeons & Dragons in one sentence."
    logging.info(f"Sending prompt: {prompt}")
    # No try block as per rules
    response = model.generate_content(prompt)
    logging.info(f"Received response:")
    logging.info(response.text)
    logging.info("--- Simple Generation Test Complete ---")

def test_chat_conversation(model: genai.GenerativeModel):
    """Tests the chat functionality, demonstrating history persistence."""
    logging.info("--- Testing Chat Conversation ---")
    # Start a new chat. The ChatSession object manages history.
    chat: genai.ChatSession = model.start_chat(history=[])
    logging.info("Chat session started.")

    prompts: List[str] = [
        "What is the basic role of a Dungeon Master in D&D?",
        "How does that differ from a player's role?",
        "Can you give a brief example of a DM describing a scene?"
    ]

    for prompt in prompts:
        logging.info(f"Sending chat message: {prompt}")
        # Sending the message automatically includes history
        response = chat.send_message(prompt)
        logging.info(f"Received response:")
        logging.info(response.text)
        logging.info("-" * 20) # Separator

    logging.info("--- Chat Conversation Test Complete ---")
    logging.info("Final Chat History:")
    for message in chat.history:
        # Ensure parts exist and have text before accessing
        text_content = ""
        if message.parts:
            part_texts = [part.text for part in message.parts if hasattr(part, 'text')]
            text_content = " ".join(part_texts)
        logging.info(f"  {message.role}: {text_content}")


def main():
    """Main function to run the Gemini API tests."""
    api_key: Optional[str] = load_api_key()
    if not api_key:
        return # Error message already logged in load_api_key

    genai.configure(api_key=api_key)
    logging.info("Gemini API configured.")

    # Choose a model - 'gemini-1.5-flash' is often a good balance
    # Other options: 'gemini-pro', 'gemini-1.0-pro', etc.
    # Using the specific preview model requested by the user:
    model_name: str = 'gemini-2.5-flash-preview-04-17'
    logging.info(f"Using model: {model_name}")
    # No try block as per rules
    model: genai.GenerativeModel = genai.GenerativeModel(model_name)

    test_simple_generation(model)
    print("\n" + "="*40 + "\n") # Add visual separation
    test_chat_conversation(model)

if __name__ == "__main__":
    main()
    logging.info("LLM test script finished.") 