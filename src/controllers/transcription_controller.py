import logging
import queue
import threading
import os
from pathlib import Path
from typing import List, Dict, Any

from PyQt5.QtCore import QObject, pyqtSignal

# Project Imports
from config_manager import ConfigManager
from log_manager import LogManager
from models.transcript_accumulator import TranscriptAccumulator
from controllers.audio_controller import AudioController

# Import client carefully - assuming it's findable
# Handle potential ImportError higher up if needed
from whisper_live_client.client import TranscriptionClient

class TranscriptionController(QObject):
    """
    Manages the transcription process, including the client lifecycle,
    audio processing threads, transcript accumulation, and emitting results.
    """
    # --- Signals ---
    # Emitted with intermediate transcription hypothesis (for live display)
    intermediate_transcription_update = pyqtSignal(str)
    # Emitted when a finalized, accumulated chunk is ready for processing
    final_chunk_ready = pyqtSignal(str)
    # Emitted when transcription process successfully starts
    transcription_started = pyqtSignal()
    # Emitted when transcription process stops (normally or due to error)
    transcription_stopped = pyqtSignal()
    # Emitted on critical error during transcription setup or process
    transcription_error = pyqtSignal(str)

    def __init__(self, config_manager: ConfigManager, audio_controller: AudioController, parent=None):
        """
        Initializes the TranscriptionController.

        Args:
            config_manager: The application's ConfigManager instance.
            audio_controller: The application's AudioController instance.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.config = config_manager
        self.audio_controller = audio_controller
        self.app_logger = LogManager.get_app_logger()
        self.raw_transcript_logger = LogManager.get_raw_transcript_logger()

        # --- Load min_sentences from config ---
        default_min_sentences = 3 # Define a sensible default
        initial_min_sentences = self.config.get("transcription.min_sentences", default_min_sentences)
        # ------------------------------------

        self.accumulator = TranscriptAccumulator(initial_min_sentences) # Pass initial value
        self.segment_queue = queue.Queue() # Queue for raw segments from client thread

        # Client and Thread Management State
        self.transcription_client: TranscriptionClient | None = None
        self.transcription_thread: threading.Thread | None = None
        self.monitor_thread: threading.Thread | None = None
        self.monitor_stop_event = threading.Event()

        # Connect signals from AudioController if needed (optional here)
        # self.audio_controller.source_changed.connect(self.handle_source_change)

        self.app_logger.info("TranscriptionController initialized.")

    def set_min_sentences(self, value: int):
        """Updates the minimum sentences required by the accumulator."""
        if self.accumulator.min_sentences != value: # Only save if changed
            self.accumulator.min_sentences = value
            # --- Save to config ---
            self.config.set("transcription.min_sentences", value)
            self.config.save()
            # --------------------
            self.app_logger.info(f"TranscriptAccumulator min_sentences set to: {value} and saved to config.")
        else:
            self.app_logger.debug(f"TranscriptAccumulator min_sentences already set to: {value}")

    def flush_accumulator(self):
        """
        Forces the accumulator to process its buffer and emit a final chunk if available.
        """
        self.app_logger.info("Flushing accumulator...")
        flushed_text = self.accumulator.flush_buffer()
        if flushed_text:
            self.app_logger.info(f"Flushed text from accumulator (length: {len(flushed_text)}), emitting: {flushed_text[:80]}...")
            self.final_chunk_ready.emit(flushed_text)
        else:
            self.app_logger.info("Flush attempted, but accumulator buffer was empty.")

    def start_transcription(self):
        """Initializes and starts the transcription client and monitoring thread."""
        self.app_logger.info("Attempting to start transcription...")
        # --- Add Debug Logs --- 
        self.app_logger.debug(f"[DEBUG] start_transcription called. Current source: {self.audio_controller.current_source}")
        # ---------------------
        if self.transcription_thread and self.transcription_thread.is_alive():
            self.app_logger.warning("Transcription already running.")
            return

        # --- Configuration Gathering ---
        project_root = Path(__file__).resolve().parents[2]
        input_audio_path_str = self.config.get("paths.input_audio", "default_audio.wav")
        input_audio_path = str(project_root / input_audio_path_str) # Ensure absolute path
        transcription_host = self.config.get("servers.transcription_host", "localhost")
        transcription_port = self.config.get("servers.transcription_port", 9090)
        start_playback_time = self.audio_controller.get_last_playback_position()
        current_source = self.audio_controller.current_source
        mute_setting = self.config.get("general.mute_playback", True)

        # --- Add Debug Log ---
        self.app_logger.debug(f"[DEBUG] Config gathered: source={current_source}, path={input_audio_path if current_source == 'File' else 'N/A'}, start_time={start_playback_time:.2f}s, mute={mute_setting}")
        # ---------------------

        if current_source == "File" and not os.path.exists(input_audio_path):
            error_msg = f"Input audio file not found at {input_audio_path}"
            self.app_logger.error(f"ERROR: {error_msg}")
            self.transcription_error.emit(error_msg)
            return

        # --- Clear Queues ---
        self.app_logger.debug("Clearing segment queue...")
        cleared_count = 0
        while not self.segment_queue.empty():
            # No try block per rules
            self.segment_queue.get_nowait()
            cleared_count += 1
        self.app_logger.debug(f"Cleared {cleared_count} items from segment queue.")

        # --- Initialize Client ---
        client_args = {
             "output_queue": self.segment_queue,
             "lang": None, "translate": False, "model": "large-v3", "use_vad": True, "log_transcription": False
        }
        wrapper_args = {"mute_audio_playback": mute_setting}

        # No try/except block around initialization per rules. If this fails, app should crash.
        self.transcription_client = TranscriptionClient(
            host=transcription_host,
            port=transcription_port,
            **client_args,
            **wrapper_args,
            max_connection_time=18000 # Increase to 5 hours (in seconds)
        )
        self.app_logger.info("Transcription client instance initialized.")

        # --- Create Threads ---
        thread_kwargs = {}
        target_function = self.transcription_client.__call__ # Target the __call__ method

        if current_source == "File":
            self.app_logger.info(f"Configuring transcription thread for file: {input_audio_path} at {start_playback_time:.2f}s")
            thread_kwargs = {'audio': input_audio_path, 'start_time': start_playback_time}
            # --- Add Debug Log ---
            self.app_logger.debug(f"[DEBUG] Thread target: {target_function}, kwargs: {thread_kwargs}")
            # ---------------------
        elif current_source == "Microphone":
             self.app_logger.info("Configuring transcription thread for microphone input.")
             # NO 'audio' kwarg means it will use record()
             thread_kwargs = {}
             # --- Add Debug Log ---
             self.app_logger.debug(f"[DEBUG] Thread target: {target_function}, kwargs: {{}} (Microphone mode)")
             # ---------------------
        else:
             error_msg = f"Invalid audio input source selected: {current_source}"
             self.app_logger.error(error_msg)
             self.transcription_client = None # Clean up potentially created client
             return

        self.transcription_thread = threading.Thread(
            target=target_function,
            kwargs=thread_kwargs,
            daemon=True
        )

        self.monitor_stop_event.clear() # Ensure event is cleared before starting
        self.monitor_thread = threading.Thread(
            target=self._monitor_segment_queue,
            daemon=True
        )

        # --- Start Threads ---
        self.transcription_thread.start()
        self.monitor_thread.start()
        self.app_logger.info("Transcription and queue monitor threads started.")
        # --- Add Debug Log ---
        self.app_logger.debug(f"[DEBUG] Transcription thread ({self.transcription_thread.name}) and Monitor thread ({self.monitor_thread.name}) started.")
        # ---------------------
        self.transcription_started.emit()


    def stop_transcription(self):
        """Stops the transcription client and monitoring thread cleanly."""
        self.app_logger.info("Attempting to stop transcription...")

        # --- Save Playback Position (via AudioController) ---
        current_pos = 0.0
        # Check client exists and has the method before calling
        if self.transcription_client and hasattr(self.transcription_client, 'get_current_playback_position'):
            current_pos = self.transcription_client.get_current_playback_position()
            self.audio_controller.save_last_playback_position(current_pos)
        elif self.transcription_client:
             self.app_logger.warning("Transcription client active but has no get_current_playback_position method.")
        else:
             self.app_logger.debug("Cannot get playback position: transcription client is None.")


        # --- Signal Threads to Stop ---
        # 1. Signal monitor thread to stop via event and queue sentinel
        self.monitor_stop_event.set()
        self.app_logger.info("Queue monitor stop signal sent.")
        # Put sentinel None into queue to unblock the blocking .get() call
        self.segment_queue.put(None)

        # 2. Transcription Client Thread (signal recording loop to stop)
        if self.transcription_client and hasattr(self.transcription_client, 'client'):
             # Check inner client exists too
             if self.transcription_client.client:
                 self.app_logger.info("Setting client.recording = False")
                 self.transcription_client.client.recording = False # Signal internal loop to stop
             else:
                 self.app_logger.warning("Inner client attribute is None, cannot set recording flag.")

             # Attempt clean client shutdown (websocket etc.)
             if hasattr(self.transcription_client, 'stop'):
                 self.app_logger.info("Calling client stop() method...")
                 self.transcription_client.stop() # Assumes stop() is implemented and safe
             elif hasattr(self.transcription_client, 'client') and self.transcription_client.client and hasattr(self.transcription_client.client, 'close_websocket'):
                 self.app_logger.info("Closing client websocket...")
                 self.transcription_client.client.close_websocket() # Assumes close_websocket() is safe
             else:
                 self.app_logger.warning("No clean stop method found for transcription client.")
        else:
             self.app_logger.info("Transcription client is None, nothing to signal for stop.")

        # --- Join Threads ---
        join_timeout = 2.0 # Seconds
        if self.transcription_thread and self.transcription_thread.is_alive():
            self.app_logger.info(f"Waiting up to {join_timeout}s for transcription thread to join...")
            self.transcription_thread.join(timeout=join_timeout)
            if self.transcription_thread.is_alive():
                self.app_logger.warning("Transcription thread did not join cleanly after timeout.")
            else:
                self.app_logger.info("Transcription thread joined.")

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.app_logger.info(f"Waiting up to {join_timeout/2}s for queue monitor thread to join...") # Shorter timeout
            self.monitor_thread.join(timeout=join_timeout / 2)
            if self.monitor_thread.is_alive():
                self.app_logger.warning("Queue monitor thread did not join cleanly after timeout.")
            else:
                 self.app_logger.info("Queue monitor thread joined.")

        # --- Clean Up ---
        self.transcription_client = None
        self.transcription_thread = None
        self.monitor_thread = None
        # Clear queue again
        while not self.segment_queue.empty():
            self.segment_queue.get_nowait()

        self.app_logger.info("Transcription stopped and resources cleaned up.")
        self.transcription_stopped.emit()


    def _monitor_segment_queue(self):
        """
        Target function for the monitor thread.
        Gets raw segments, logs them, emits intermediate updates,
        accumulates segments, and emits final chunks.
        """
        self.app_logger.info("Segment queue monitor thread started.")
        while True:
            # Block until an item is available.  Because we put a sentinel ``None`` into the
            # queue when stopping (see ``stop_transcription``), the thread will always wake
            # up and can terminate gracefully without relying on time-outs or try/except.
            data = self.segment_queue.get()

            # If we receive the sentinel or the stop event is set, exit the loop.
            if data is None or self.monitor_stop_event.is_set():
                self.segment_queue.task_done()
                break

            if data is None: # Should not happen with current client, but good practice
                self.app_logger.info("Received None from segment queue, stopping monitor.")
                break

            if isinstance(data, list):
                # --- Log Raw (Disabled for now) ---
                # self.raw_transcript_logger.info(f"RAW: {data}")

                # --- Emit Intermediate ---
                current_hypothesis = " ".join(seg.get('text', '').strip() for seg in data)
                # --- Add Debug Log before emit ---
                self.app_logger.debug(f"[DEBUG] Monitor thread emitting intermediate_transcription_update: '{current_hypothesis[:100]}...'")
                # ----------------------------------
                # LogManager.get_app_logger().debug(f"Monitor emitting intermediate: {current_hypothesis}")
                self.intermediate_transcription_update.emit(current_hypothesis)

                # --- Accumulate & Emit Final ---
                accumulated_chunk = self.accumulator.add_segments(data)
                if accumulated_chunk:
                    # Compute diagnostics
                    import nltk
                    sentence_count = len(nltk.sent_tokenize(accumulated_chunk))
                    word_count = len(accumulated_chunk.split())
                    self.app_logger.info(
                        f"Accumulator ready. Sentences: {sentence_count}, Words: {word_count}. Emitting chunk: {accumulated_chunk[:80]}..."
                    )
                    self.final_chunk_ready.emit(accumulated_chunk)

            else:
                # Log unexpected data type
                 self.app_logger.warning(f"Received non-list data type from segment_queue: {type(data)}. Value: {str(data)[:100]}")

            self.segment_queue.task_done() # Mark task as done

        self.app_logger.info("Segment queue monitor thread finished.") 