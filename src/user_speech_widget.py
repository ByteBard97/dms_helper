#!/usr/bin/env python3
"""Widget encapsulating the *right-hand* user-speech transcript pane.

Separating this component from the main window simplifies signal-slot
connections and allows specialised behaviour (e.g., custom formatting of
settled vs. hypothesis text) to be localised here.

It intentionally exposes minimal public API: *set_transcript* for complete
replacement, and *update_transcript* for the common dual-section rendering used
by the existing application.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QTextEdit, QWidget
from PyQt5.QtCore import Qt, pyqtSlot

from config_manager import ConfigManager

__all__ = ["UserSpeechWidget"]


class UserSpeechWidget(QTextEdit):
    """Read-only pane displaying the player's spoken words.

    Parameters
    ----------
    config_manager:
        Shared application configuration for accessing UI preferences
        (e.g., default visibility).
    parent:
        Optional Qt parent.
    """

    def __init__(self, config_manager: ConfigManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.config = config_manager

        # This pane is not editable by the user.
        self.setReadOnly(True)
        self.setPlaceholderText("Transcribed user speech will appear here…")

        # Remember visibility preference from config.
        self.setVisible(self.config.get("ui_settings.show_user_speech", True))

        # Internal cache for settled text.
        self._settled_text: str = ""

        # ------------------------------------------------------------------
        # Typography – make the transcript comfortably readable
        # ------------------------------------------------------------------
        default_size_px = 16  # Logical default if not specified in config
        font_size_px = self.config.get("ui_settings.user_speech_font_size", default_size_px)
        # Apply via Qt style sheet so it cascades to all HTML rendered inside
        self.setStyleSheet(f"font-size: {font_size_px}px;")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def update_display(self, hypothesis_text: str) -> None:
        """Redraw widget to display current transcription state.

        The *settled* portion is stored internally, while *hypothesis_text*
        represents in-progress speech.
        """
        settled_html = self._settled_text.replace("\n", "<br>")
        separator = "\n\n--- In Progress ---\n" if hypothesis_text else ""
        hyp_html = f"{separator}{hypothesis_text}".replace("\n", "<br>")

        final_html = (
            f"<span>{settled_html}</span>"
            f"<span style='color: gray;'>{hyp_html}</span>"
        )
        self.setHtml(final_html)

        # Auto-scroll so latest text is visible.
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def append_settled_chunk(self, chunk: str) -> None:
        """Add a finalised chunk to the settled transcript and refresh."""
        self._settled_text += chunk + "\n\n"
        self.update_display("")

    def clear_transcript(self) -> None:
        """Clear both settled and hypothesis sections."""
        self._settled_text = ""
        self.update_display("")

    # Visibility convenience – allows ControlsWidget to toggle quickly
    def set_visibility(self, visible: bool) -> None:  # noqa: D401
        self.setVisible(visible) 