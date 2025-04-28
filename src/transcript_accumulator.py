import re
import logging
import nltk # Added for sentence tokenization
from typing import Optional, List, Dict, Any
import sys

# Constants moved here as they are specific to the accumulator logic
MIN_SENTENCES_PER_CHUNK = 3
# MAX_SENTENCES_PER_CHUNK = 10 # Keep this commented for now, focus on min
MIN_WORDS_PER_CHUNK = 50 # Minimum word count

class TranscriptAccumulator:
    """Accumulates completed transcript segments and yields chunks based on sentence/word count using NLTK."""
    def __init__(self, min_sentences=MIN_SENTENCES_PER_CHUNK,
                 # max_sentences=MAX_SENTENCES_PER_CHUNK, # Keep commented
                 min_words=MIN_WORDS_PER_CHUNK):
        # Download NLTK data if needed (ensure 'punkt' and 'punkt_tab' are available)
        try:
            # Check for both resources needed by sent_tokenize
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('tokenizers/punkt_tab') 
        except LookupError:
            logging.info("NLTK 'punkt'/'punkt_tab' tokenizer data not found. Downloading...")
            try:
                nltk.download('punkt')
                nltk.download('punkt_tab') # Also download punkt_tab
                logging.info("NLTK 'punkt' and 'punkt_tab' data downloaded successfully.")
            except Exception as download_e:
                # Catch potential errors during download (network issues, permissions, etc.)
                logging.error(f"Failed to download NLTK data: {download_e}", exc_info=True)
                raise RuntimeError("Failed to download required NLTK data. Cannot continue.") from download_e
        except Exception as e:
            # Catch any other unexpected errors during the find operation
            logging.error(f"An unexpected error occurred checking for NLTK data: {e}", exc_info=True)
            raise RuntimeError("Failed checking for NLTK data.") from e

        self.buffer = [] # Buffer for accumulating *completed* text
        self.last_processed_end_time = 0.0 # Track end time of last committed segment
        self.min_sentences = min_sentences
        # self.max_sentences = max_sentences # Keep commented
        self.min_words = min_words
        self.sentence_count = 0 # Added for sentence count tracking
        # Removed complex sentence split pattern, will use nltk.sent_tokenize
        logging.info(f"TranscriptAccumulator initialized (NLTK, MinSentences: {self.min_sentences}, MinWords: {self.min_words}).")

    def _get_word_count(self, text: str) -> int:
        """Helper to count words in a string."""
        return len(text.split())

    def add_segments(self, segments: List[Dict[str, Any]]) -> Optional[str]:
        """Adds completed segments from the list and returns a chunk if criteria met."""
        newly_completed_text = ""

        # Only process completed segments
        for seg in segments:
            is_completed = seg.get("completed", False)
            end_time = float(seg.get("end", 0.0))
            segment_text = seg.get("text", "").strip()

            # Process if completed, has text, and ends after the last processed segment
            if is_completed and segment_text and end_time > self.last_processed_end_time:
                logging.debug(f"Accumulator: Adding completed segment ending at {end_time:.2f}: '{segment_text[:50]}...'")
                if newly_completed_text:
                    newly_completed_text += " "
                newly_completed_text += segment_text
                self.last_processed_end_time = end_time
                self.buffer.append(segment_text)
                self.sentence_count += 1
            elif not is_completed and segment_text:
                 # Log skipped non-completed segments if desired, but don't add to buffer
                 logging.debug(f"Accumulator: Skipping non-completed segment: '{segment_text[:50]}...'")

        # Append the aggregated completed text to the buffer
        if newly_completed_text:
             if self.buffer and not newly_completed_text.startswith(' '):
                 self.buffer.append(" ")
             self.buffer.append(newly_completed_text)
             logging.debug(f"Accumulator: Buffer updated with completed text. Current length: {len(self.buffer)} items, Word count: {self._get_word_count(' '.join(self.buffer))}")
        else:
            # No new completed segments were added
            return None

        # --- Check if buffer should be processed ---
        if self.sentence_count >= self.min_sentences or len(self.buffer) >= self.min_words: # Check both conditions
            chunk_to_return = " ".join(self.buffer).strip()
            self.buffer = [] # Clear buffer
            self.sentence_count = 0 # Reset sentence count
            return chunk_to_return
        else:
            # Not enough sentences/words yet
            return None

    def flush(self) -> Optional[str]:
        """Returns any remaining text in the buffer and clears it."""
        remaining_text = " ".join(self.buffer).strip()
        self.buffer = [] # Clear buffer
        self.last_processed_end_time = 0.0 # Reset time tracker on flush
        if remaining_text:
            logging.info(f"Accumulator: Flushing remaining buffer ({self._get_word_count(remaining_text)} words): '{remaining_text[:50]}...'")
            return remaining_text
        logging.debug("Accumulator: Flush called, buffer was empty.")
        return None 

    def flush_buffer(self) -> Optional[str]:
        """Forces the accumulator to return its current buffer content and clears it."""
        if not self.buffer:
            return None
        
        chunk_to_return = " ".join(self.buffer).strip()
        self.buffer = [] # Clear buffer
        self.sentence_count = 0 # Reset sentence count
        return chunk_to_return 