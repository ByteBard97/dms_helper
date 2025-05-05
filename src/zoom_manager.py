#!/usr/bin/env python3
"""zoom_manager.py

Centralised helper that manages global font scaling ("zoom") for the GUI.

The manager adjusts Qt's application-wide default QFont so that *all* standard
widgets repaint at the requested size. It also synchronises PyQt5 components
that do **not** respect the global font (e.g. QWebEngineView) via additional
callbacks.

Rules respected:
- No try/except blocks are used.
- Uses Python 3.10+ type hints.
- Keeps file under 300 LOC (very small).
"""
from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QFont

from config_manager import ConfigManager


class ZoomManager(QObject):
    """Singleton-style helper that exposes zoom_in / zoom_out / reset_zoom.

    Parameters
    ----------
    config : ConfigManager
        Reference to the global configuration so the current zoom step can be
        persisted under the ``ui_settings.font_step`` key.
    output_widget : QWebEngineView
        The *LLM output* view that requires explicit zoom control via
        ``setZoomFactor`` because it renders HTML independently from Qt's font
        system.
    """

    fontChanged: pyqtSignal = pyqtSignal(QFont)  # emitted after every apply()

    _MIN_STEP = -5  # reasonable lower bound (5pt smaller)
    _MAX_STEP = 10  # reasonable upper bound (10pt larger)

    def __init__(self, config: ConfigManager, output_widget: QWebEngineView):
        super().__init__()
        self._cfg = config
        self._output = output_widget

        app_font = QApplication.instance().font()
        self._base_pt_size: int = app_font.pointSize()
        self._step: int = int(self._cfg.get("ui_settings.font_step", 0) or 0)

        # Clamp any out-of-range persisted value then apply immediately.
        if self._step < self._MIN_STEP:
            self._step = self._MIN_STEP
        if self._step > self._MAX_STEP:
            self._step = self._MAX_STEP

        self._apply()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def zoom_in(self) -> None:
        """Increase font size by one step."""
        self._nudge(+1)

    def zoom_out(self) -> None:
        """Decrease font size by one step."""
        self._nudge(-1)

    def reset_zoom(self) -> None:
        """Reset to the *base* application font size (step == 0)."""
        self._set_step(0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _nudge(self, delta: int) -> None:
        self._set_step(self._step + delta)

    def _set_step(self, new_step: int) -> None:
        if new_step < self._MIN_STEP:
            new_step = self._MIN_STEP
        if new_step > self._MAX_STEP:
            new_step = self._MAX_STEP
        if new_step == self._step:
            return  # no change
        self._step = new_step
        # Persist setting immediately.
        self._cfg.set("ui_settings.font_step", self._step)
        self._apply()

    def _apply(self) -> None:
        """Recompute sizes and propagate to widgets."""
        new_pt_size: int = self._base_pt_size + self._step
        # Update application-wide default font.
        font: QFont = QApplication.instance().font()
        font.setPointSize(new_pt_size)
        QApplication.instance().setFont(font)

        # Sync QWebEngineView zoom (scales *everything* inside the page).
        factor: float = new_pt_size / self._base_pt_size
        self._output.setZoomFactor(factor)

        # Notify any custom listeners.
        self.fontChanged.emit(font) 