import re
import logging
from typing import Optional, List, Dict, Any

# Constants moved here as they are specific to the accumulator logic
MIN_SENTENCES_PER_CHUNK = 3
MAX_SENTENCES_PER_CHUNK = 10
# Optional: Add a word count check as well?
MIN_WORDS_PER_CHUNK = 20 # Example minimum word count

class TranscriptAccumulator:
    """Accumulates completed transcript segments and yields chunks based on sentence/word count."""
    def __init__(self, min_sentences=MIN_SENTENCES_PER_CHUNK,
                 max_sentences=MAX_SENTENCES_PER_CHUNK,
                 min_words=MIN_WORDS_PER_CHUNK):
        self.buffer = "" # Buffer for accumulating *completed* text
        self.last_processed_end_time = 0.0 # Track end time of last committed segment
        self.min_sentences = min_sentences
        self.max_sentences = max_sentences
        self.min_words = min_words
        # Simple regex to split potential sentences, keeping delimiters
        self.sentence_split_pattern = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s')
        logging.debug("TranscriptAccumulator initialized.")

    def _get_word_count(self, text: str) -> int:
        """Helper to count words in a string."""
        return len(text.split())

    def add_segments(self, segments: List[Dict[str, Any]]) -> Optional[str]:
        """Adds completed segments from the list and returns a chunk if criteria met."""
        newly_completed_text = ""

        for seg in segments:
            # Check if segment is completed and hasn't been processed before
            # Use end time to prevent reprocessing slightly shifted segments
            is_completed = seg.get("completed", False)
            end_time = float(seg.get("end", 0.0))
            segment_text = seg.get("text", "").strip()

            # Process if completed, has text, and ends after the last processed segment
            if is_completed and segment_text and end_time > self.last_processed_end_time:
                logging.debug(f"Accumulator: Adding completed segment ending at {end_time:.2f}: '{segment_text[:50]}...'")
                # Append with a space if needed
                if newly_completed_text:
                    newly_completed_text += " "
                newly_completed_text += segment_text
                # Update the end time tracker to the end of this segment
                self.last_processed_end_time = end_time
            elif not is_completed and segment_text:
                 logging.debug(f"Accumulator: Skipping non-completed segment: '{segment_text[:50]}...'")

        # Append newly completed text to the main buffer
        if newly_completed_text:
             if self.buffer and not newly_completed_text.startswith(' '):
                 self.buffer += " "
             self.buffer += newly_completed_text
             logging.debug(f"Accumulator: Buffer updated. Current length: {len(self.buffer)}, Word count: {self._get_word_count(self.buffer)}")

        # Check if buffer meets criteria for yielding a chunk
        potential_sentences = self.sentence_split_pattern.split(self.buffer)
        sentences = [s for s in potential_sentences if s and s.strip()]
        num_sentences = len(sentences)
        num_words = self._get_word_count(self.buffer)

        chunk_ready = False
        if num_sentences >= self.min_sentences:
            chunk_ready = True
            logging.debug(f"Accumulator: Met sentence threshold ({num_sentences}/{self.min_sentences}).")

        if chunk_ready:
            # Determine sentence count for the chunk (max_sentences limit)
            num_sentences_in_chunk = min(num_sentences, self.max_sentences)

            # Take the required number of sentences
            chunk_sentences = sentences[:num_sentences_in_chunk]
            # Join them to form the chunk, adding back the necessary space
            chunk = " ".join(chunk_sentences)

            # Determine the remaining sentences
            remaining_sentences = sentences[num_sentences_in_chunk:]
            # Reconstruct the buffer from the remaining sentences
            self.buffer = " ".join(remaining_sentences)

            logging.debug(f"Accumulator: Yielding chunk ({num_sentences_in_chunk} sentences, {self._get_word_count(chunk)} words): '{chunk[:50]}...'")
            logging.debug(f"Accumulator: Remaining buffer: '{self.buffer[:50]}...'")
            return chunk

        # Criteria not met, return None
        return None

    def flush(self) -> Optional[str]:
        """Returns any remaining text in the buffer and clears it."""
        remaining_text = self.buffer.strip()
        self.buffer = ""
        self.last_processed_end_time = 0.0 # Reset time tracker on flush
        if remaining_text:
            logging.debug(f"Accumulator: Flushing remaining buffer ({self._get_word_count(remaining_text)} words): '{remaining_text[:50]}...'")
            return remaining_text
        logging.debug("Accumulator: Flush called, buffer was empty.")
        return None 