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

from PyQt5.QtWidgets import QTextEdit, QWidget, QApplication
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont

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
        # Typography – start with the *application* default font size so that
        # global zoom actions (handled by ZoomManager) can simply adjust the
        # QFont and ask this widget to update.
        # ------------------------------------------------------------------
        # Determine *base* sizes
        default_px: int = 16
        self._base_px: int = self.config.get("ui_settings.user_speech_font_size", default_px)
        self._base_pt: int = QApplication.instance().font().pointSize()

        # Apply initial style based on base_px
        self._apply_font(QApplication.instance().font())

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

    @pyqtSlot(QFont)
    def apply_font(self, font: QFont) -> None:  # noqa: D401
        """Slot: updates the stylesheet to use *font.pointSize()* pixels."""
        self._apply_font(font)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_font(self, font: QFont) -> None:
        """Update CSS pixel size proportionally to the global application font."""
        factor: float = font.pointSize() / self._base_pt if self._base_pt else 1.0
        px: int = max(8, int(round(self._base_px * factor)))
        self.setStyleSheet(f"font-size: {px}px;") 