#!/usr/bin/env python3
"""Composite widget housing *all* bottom-panel controls.

This initial skeleton merely groups child controls logically; detailed wiring of
signals/slots will be completed in later subtasks (29.2+).
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QSizePolicy,
)
from PyQt5.QtCore import pyqtSignal, Qt

from config_manager import ConfigManager
from .dm_action_panel import DMActionPanel
from .dm_input_widget import DMInputWidget  # local import to avoid cycles

__all__ = ["ControlsWidget"]


class ControlsWidget(QWidget):
    """Encapsulates audio source controls *and* DM action panel.

    For now, it exposes bare child attributes so the main window can connect
    existing controller signals.  Future subtasks will move those connections
    into this class.
    """

    # ------------------------------------------------------------------
    # Outgoing signals
    # ------------------------------------------------------------------
    audio_action_requested = pyqtSignal(str)
    dm_action_requested = pyqtSignal(str, dict)
    transcription_settings_changed = pyqtSignal(dict)
    llm_params_changed = pyqtSignal(dict)
    flush_requested = pyqtSignal()
    show_user_speech_toggled = pyqtSignal(bool)

    def __init__(self, config_manager: ConfigManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.config = config_manager

        # ------------------------------------------------------------------
        # Layout scaffold replicating existing structure
        # ------------------------------------------------------------------
        root_layout = QHBoxLayout(self)
        self.setLayout(root_layout)

        # Left-hand audio/transcription controls.
        left_layout = QVBoxLayout()
        # Give left and right columns equal stretch so they roughly split 50/50
        root_layout.addLayout(left_layout, 1)

        # Right-hand DM manual input widget
        self.dm_input_widget = DMInputWidget()

        # We'll create a container to hold the DM panel and prompt entry stacked
        right_container = QVBoxLayout()
        root_layout.addLayout(right_container, 1)

        # Audio row.
        audio_row = QHBoxLayout()
        self.audio_source_label = QLabel("Audio Source:")
        self.audio_source_combobox = QComboBox()
        # Populate and set initial selection based on config
        self.audio_source_combobox.addItems(["File", "Microphone"])
        initial_source = self.config.get("audio_settings.input_source", "File")
        index = self.audio_source_combobox.findText(initial_source)
        if index != -1:
            self.audio_source_combobox.setCurrentIndex(index)
        self.start_button = QPushButton("Start Listening")
        self.stop_button = QPushButton("Stop Listening")
        self.stop_button.setEnabled(False)
        audio_row.addWidget(self.audio_source_label)
        audio_row.addWidget(self.audio_source_combobox)
        audio_row.addWidget(self.start_button)
        audio_row.addWidget(self.stop_button)
        audio_row.addStretch(1)
        left_layout.addLayout(audio_row)

        # Transcription settings row.
        trans_row = QHBoxLayout()
        self.show_user_speech_checkbox = QCheckBox("Show User Speech")
        self.show_user_speech_checkbox.setChecked(self.config.get("ui_settings.show_user_speech", True))

        self.min_sentences_label = QLabel("Min Sentences:")
        self.min_sentences_spinbox = QSpinBox()
        self.min_sentences_spinbox.setRange(1, 10)

        self.flush_button = QPushButton("Flush Accumulator")

        trans_row.addWidget(self.show_user_speech_checkbox)
        trans_row.addWidget(self.min_sentences_label)
        trans_row.addWidget(self.min_sentences_spinbox)
        trans_row.addWidget(self.flush_button)
        trans_row.addStretch(1)
        left_layout.addLayout(trans_row)

        # Right-hand DM action panel.
        self.dm_action_panel = DMActionPanel()
        self.dm_action_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_container.addWidget(self.dm_input_widget)
        right_container.addWidget(self.dm_action_panel)

        # Expose DMActionPanel widgets directly for convenience during refactor
        for _name in (
            "pc_level_spinbox",
            "quantity_spinbox",
            "generate_npc_button",
            "describe_surroundings_button",
            "generate_encounter_button",
            "suggest_rumor_button",
            "suggest_complication_button",
            "generate_mundane_items_button",
            "generate_loot_button",
            "test_button",
        ):
            setattr(self, _name, getattr(self.dm_action_panel, _name))

        # Expose the custom prompt entry explicitly
        self.custom_prompt_lineedit = self.dm_input_widget

        # ------------------------------------------------------------------
        # Signal wiring
        # ------------------------------------------------------------------

        # Audio actions
        self.audio_source_combobox.currentTextChanged.connect(
            lambda text: self.audio_action_requested.emit(f"source:{text}")
        )
        self.start_button.clicked.connect(lambda: self.audio_action_requested.emit("start"))
        self.stop_button.clicked.connect(lambda: self.audio_action_requested.emit("stop"))

        # Transcription settings
        self.min_sentences_spinbox.valueChanged.connect(
            lambda val: self.transcription_settings_changed.emit({"min_sentences": val})
        )
        self.flush_button.clicked.connect(self.flush_requested)

        # Show-user-speech toggle
        self.show_user_speech_checkbox.stateChanged.connect(
            lambda state: self.show_user_speech_toggled.emit(state == Qt.Checked)
        )

        # LLM param spinboxes inside DMActionPanel
        self.pc_level_spinbox.valueChanged.connect(self._emit_llm_params)
        self.quantity_spinbox.valueChanged.connect(self._emit_llm_params)

        # DM-action buttons
        self.generate_npc_button.clicked.connect(
            lambda: self._emit_dm_action("dm_action_generate_npc.md")
        )
        self.describe_surroundings_button.clicked.connect(
            lambda: self._emit_dm_action("dm_action_describe_surroundings.md")
        )
        self.generate_encounter_button.clicked.connect(
            lambda: self._emit_dm_action("dm_action_generate_encounter.md")
        )
        self.suggest_rumor_button.clicked.connect(
            lambda: self._emit_dm_action("dm_action_suggest_rumor.md")
        )
        self.suggest_complication_button.clicked.connect(
            lambda: self._emit_dm_action("dm_action_suggest_complication.md")
        )
        self.generate_mundane_items_button.clicked.connect(
            lambda: self._emit_dm_action("dm_action_generate_mundane_items.md")
        )
        self.generate_loot_button.clicked.connect(
            lambda: self._emit_dm_action("dm_action_generate_loot.md")
        )
        self.test_button.clicked.connect(
            lambda: self._emit_dm_action("prompts/test_statblock_markdown.md", is_test=True)
        )

    # ------------------------------------------------------------------
    # Helper emitters
    # ------------------------------------------------------------------
    def _emit_llm_params(self) -> None:  # noqa: D401
        params = {
            "pc_level": self.pc_level_spinbox.value(),
            "quantity": self.quantity_spinbox.value(),
        }
        self.llm_params_changed.emit(params)

    def _emit_dm_action(self, prompt_filename: str, *, is_test: bool = False) -> None:  # noqa: D401
        params = {
            "pc_level": self.pc_level_spinbox.value(),
            "quantity": self.quantity_spinbox.value(),
            "is_test": is_test,
        }
        self.dm_action_requested.emit(prompt_filename, params)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_controls_enabled(self, enabled: bool) -> None:  # noqa: D401
        """Enable/disable *all* interactive child widgets."""
        for widget in (
            self.audio_source_combobox,
            self.start_button,
            self.stop_button,
            self.show_user_speech_checkbox,
            self.min_sentences_spinbox,
            self.flush_button,
            self.dm_input_widget,
        ):
            widget.setEnabled(enabled)

        self.dm_action_panel.set_controls_enabled(enabled)

        # ------------------------------------------------------------------
        # Future: read initial values from controllers/config once available
        # ------------------------------------------------------------------ 