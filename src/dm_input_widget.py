#!/usr/bin/env python3
"""Self-contained widget for manual Dungeon-Master input.

Provides a multi-line :class:`QTextEdit` with an adjacent *Send* button that
emits the entered text when submitted.  The widget exposes a
:pydata:`~DMInputWidget.prompt_submitted` signal and a
:meth:`~DMInputWidget.set_processing` helper to reflect LLM busy/idle state.
"""
from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QTextEdit, QPushButton, QHBoxLayout, QSizePolicy
from PyQt5.QtCore import pyqtSignal, Qt, QEvent

__all__ = ["DMInputWidget"]


class _InputEdit(QTextEdit):
    """QTextEdit that captures *Enter* / *Shift-Enter* behaviour."""

    return_pressed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # Accept multi-line input by default; Enter will be captured manually.

    def eventFilter(self, obj, event):  # noqa: D401
        return super().eventFilter(obj, event)

    # Override key press to map Enter to submission when Shift not held.
    def keyPressEvent(self, event):  # noqa: D401
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                # Insert newline normally
                super().keyPressEvent(event)
            else:
                # Emit submission and *do not* insert newline
                self.return_pressed.emit()
            return  # Avoid default handling
        super().keyPressEvent(event)


class DMInputWidget(QWidget):
    """Manual DM input field + Send button UI component."""

    prompt_submitted = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.text_edit = _InputEdit()
        self.text_edit.setPlaceholderText("Enter custom DM prompt …")
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.text_edit.setFixedHeight(48)  # two text lines approx

        self.send_button = QPushButton("SEND")
        self.send_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.send_button.clicked.connect(self._submit)

        # Wire Enter key in text_edit to submission
        self.text_edit.return_pressed.connect(self._submit)

        layout.addWidget(self.text_edit)
        layout.addWidget(self.send_button)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def set_processing(self, is_processing: bool) -> None:  # noqa: D401
        """Enable/disable UI based on LLM busy flag."""
        if is_processing:
            self.send_button.setText("BUSY")
            self.send_button.setEnabled(False)
            self.text_edit.setEnabled(False)
        else:
            self.send_button.setText("SEND")
            self.send_button.setEnabled(True)
            self.text_edit.setEnabled(True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _submit(self):  # noqa: D401
        text = self.text_edit.toPlainText().strip()
        if not text:
            return
        self.prompt_submitted.emit(text)
        self.text_edit.clear() 