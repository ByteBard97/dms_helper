import logging
from PyQt5.QtCore import QObject, pyqtSignal

# Project Imports (adjust as needed)
from config_manager import ConfigManager
from log_manager import LogManager

class AudioController(QObject):
    """
    Manages audio input source selection and related state (like playback position).
    Does NOT directly handle transcription client lifecycle or audio playback itself,
    but provides configuration and state needed by other components.
    """
    # Define signals
    source_changed = pyqtSignal(str) # Emitted when the audio source changes via the UI

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initializes the AudioController.

        Args:
            config_manager: The application's ConfigManager instance.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.config = config_manager
        self.app_logger = LogManager.get_app_logger()

        # Load initial state from config
        self._current_source = self.config.get("audio_settings.input_source", "File")
        self.app_logger.info(f"AudioController initialized. Initial source: {self._current_source}")

    @property
    def current_source(self) -> str:
        """Gets the currently selected audio source ('File' or 'Microphone')."""
        return self._current_source

    def set_audio_source(self, new_source: str, is_transcription_active: bool):
        """
        Sets the audio source if it has changed and saves it to config.
        Emits source_changed signal. Logs a warning if changed while active.

        Args:
            new_source: The new source ('File' or 'Microphone').
            is_transcription_active: Boolean indicating if transcription is currently running.
        """
        if new_source != self._current_source:
            self._current_source = new_source
            self.config.set("audio_settings.input_source", new_source)
            # Save config immediately (handle potential errors if necessary, though rules discourage try/except)
            self.config.save()
            self.app_logger.info(f"Audio input source changed to: {new_source} (saved)")
            self.source_changed.emit(new_source) # Emit signal

            if is_transcription_active:
                self.app_logger.warning("Audio source changed while transcription is active. Stop/Start required to apply change.")
        else:
            self.app_logger.debug(f"Audio source attempted set to '{new_source}', but it's already the current source.")

    def get_last_playback_position(self) -> float:
        """Gets the last saved playback position from config."""
        # Read directly from config when needed
        start_playback_time = self.config.get("audio_settings.last_playback_position", 0.0)
        self.app_logger.debug(f"Retrieved last playback position: {start_playback_time:.2f} seconds")
        return start_playback_time

    def save_last_playback_position(self, position_seconds: float):
        """Saves the given playback position to config."""
        # Write directly to config
        self.config.set("audio_settings.last_playback_position", position_seconds)
        self.config.save() # Consider if saving immediately is always desired
        self.app_logger.info(f"Saved playback position {position_seconds:.2f} to config.") 