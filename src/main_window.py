#!/usr/bin/env python3
import sys
import json
import logging
from pathlib import Path
# We intentionally avoid wildcard imports; currently no direct use of typing generics here.

# --- Add necessary PyQt5 imports back ---
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QHBoxLayout, QLabel, QTextEdit, QSizePolicy, QCheckBox,
    QSplitter, QSpinBox, QComboBox, QMessageBox, QGridLayout # Added QMessageBox for potential error handling and QGridLayout for DM action buttons
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
# --------------------------------------

# Project Imports
from log_manager import LogManager
from config_manager import ConfigManager
from controllers.audio_controller import AudioController
from controllers.transcription_controller import TranscriptionController
from controllers.llm_controller import LLMController
from controllers.response_processor import convert_markdown_to_html
from controllers.response_processor import extract_statblock_html



# Custom widget grouping DM action controls
# from dm_action_panel import DMActionPanel

# New modular widgets
from views.llm_output_widget import LLMOutputWidget
from views.user_speech_widget import UserSpeechWidget
from views.controls_widget import ControlsWidget

class MainWindow(QMainWindow):
    """
    Main application window acting as an orchestrator for various controllers.
    Sets up the UI and connects signals/slots between controllers and UI elements.
    """
    # Add state for settled user speech text
    settled_user_text: str = ""

    def __init__(self):
        super().__init__()
        # Initialize essential managers FIRST
        # LogManager.initialize() # Initialize should happen once at entry point
        self.config = ConfigManager()
        # --- Initialize logger HERE ---
        self.app_logger = LogManager.get_app_logger()
        self.conv_logger = LogManager.get_conversation_logger()
        # -----------------------------
        self.app_logger.info("Initializing MainWindow Orchestrator...")

        # --- Initialize Controllers EARLY ---
        # Pass necessary dependencies
        self.audio_controller = AudioController(self.config, parent=self)
        self.transcription_controller = TranscriptionController(self.config, self.audio_controller, parent=self)
        self.llm_controller = LLMController(self.config, parent=self)
        # ----------------------------------

        # --- UI Setup (Adapted from main_window_original.py) ---
        self.setWindowTitle("D&D Helper Assistant - Refactored")
        self.setGeometry(100, 100, 1000, 700) # Adjusted default size

        # Use camelCase for PyQt built-in attributes/methods
        self.centralWidget_ = QWidget()
        self.setCentralWidget(self.centralWidget_)
        self.main_layout = QVBoxLayout(self.centralWidget_)

        # --- Instantiate modular widgets ---
        self.output_widget = LLMOutputWidget(self.config, parent=self)
        self.user_speech_widget = UserSpeechWidget(self.config, parent=self)
        self.controls_widget = ControlsWidget(self.config, parent=self)
        # --- Top Section: Splitter for Output and User Speech ---
        self.splitter = QSplitter(Qt.Horizontal)

        # ----- Left Pane already handled by output_widget -----
        self.splitter.addWidget(self.output_widget)

        # ----- Right Pane: User Speech (Text Edit) -----
        self.splitter.addWidget(self.user_speech_widget)
        # Ensure proportional layout (≈60% A / 40% B) on startup
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.show_user_speech_state = self.config.get("ui_settings.show_user_speech", True)
        self.user_speech_widget.set_visibility(self.show_user_speech_state)

        # Configure splitter sizes to an even 50/50 split (pixels here are ratios)
        self.splitter.setSizes([500, 500])

        # Add Splitter to Main Layout - it will take most space
        self.main_layout.addWidget(self.splitter, 1) # Add with stretch factor 1

        # Bottom controls handled by modular ControlsWidget
        self.main_layout.addWidget(self.controls_widget)

        # Expose child widgets for existing signal wiring until refactor complete
        for _name in (
            "start_button",
            "stop_button",
            "audio_source_combobox",
            "show_user_speech_checkbox",
            "min_sentences_spinbox",
            "flush_button",
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
            if hasattr(self.controls_widget, _name):
                setattr(self, _name, getattr(self.controls_widget, _name))

        # Specific alias for legacy name mismatch BEFORE signal connections
        if hasattr(self.controls_widget, "show_user_speech_checkbox"):
            self.user_speech_checkbox = self.controls_widget.show_user_speech_checkbox

        # --- Status Bar ---
        self.statusBar().showMessage("Ready.") # Initialize status bar


        # --- Connect Signals and Slots ---
        self._connect_signals()
        # ---------------------------------

        # --- Initialize Settled Text ---
        # Could potentially load initial state if needed
        self.settled_user_text = "" # Reset on init
        self.user_speech_widget.clear_transcript()
        self.update_user_speech_pane("") # Initial update to clear pane
        # -------------------------------

        self.app_logger.info("MainWindow initialization complete.")

    def _connect_signals(self):
        # --- Add Start/Stop Button Connections ---
        self.start_button.clicked.connect(self.transcription_controller.start_transcription)
        self.stop_button.clicked.connect(self.transcription_controller.stop_transcription)
        # -----------------------------------------

        # --- Connect Transcription State Signals to UI Slots ---
        self.transcription_controller.transcription_started.connect(self._on_transcription_started)
        self.transcription_controller.transcription_stopped.connect(self._on_transcription_stopped)
        self.transcription_controller.transcription_error.connect(self._show_error_message) # Generic error display
        # Additional UI ↔ controller connections missing from the first refactor
        # -------------------------------------------------------------------
        # 1.  Live intermediate transcription to UI (already connected above)
        # 2.  Audio-source combo box change → AudioController
        self.audio_source_combobox.currentTextChanged.connect(self._on_audio_source_changed)

        # 3.  Show-user-speech checkbox toggle → show/hide text edit + persist setting
        self.user_speech_checkbox.stateChanged.connect(self._on_user_speech_checkbox_changed)

        # 4.  Min sentences spinbox → TranscriptionController accumulator parameter
        self.min_sentences_spinbox.valueChanged.connect(self.transcription_controller.set_min_sentences)

        # 5.  Flush accumulator button → TranscriptionController flush method
        self.flush_button.clicked.connect(self.transcription_controller.flush_accumulator)

        # 6.  LLM processing start / finish signals → status-bar & button enable/disable
        self.llm_controller.processing_started.connect(self._on_llm_processing_started)
        self.llm_controller.processing_finished.connect(self._on_llm_processing_finished)
        # --- Connect Intermediate Update Signal (Queued to ensure GUI-thread execution) ---
        self.transcription_controller.intermediate_transcription_update.connect(
            self.user_speech_widget.update_display,
            Qt.QueuedConnection
        )
        # ------------------------------------------------------

        # Transcription Controller -> LLM Controller
        # Connect final_chunk_ready to a method in MainWindow first to update settled text
        self.transcription_controller.final_chunk_ready.connect(
            self._handle_final_chunk,
            Qt.QueuedConnection
        )

        # LLM Controller -> UI Updates
        self.llm_controller.response_received.connect(self.handle_llm_response)
        self.llm_controller.llm_error.connect(self._show_error_message)
        # --- Streaming connections ---
        self.llm_controller.stream_started.connect(self.output_widget.handle_stream_started)
        self.llm_controller.response_chunk_received.connect(self.output_widget.handle_response_chunk_received)
        self.llm_controller.stream_finished.connect(self.output_widget.handle_stream_finished)

        # 7.  DM action parameter spinboxes → LLMController properties
        self.pc_level_spinbox.valueChanged.connect(
            lambda val: setattr(self.llm_controller, "pc_level", val)
        )
        self.quantity_spinbox.valueChanged.connect(
            lambda val: setattr(self.llm_controller, "action_quantity", val)
        )

        # 8.  DM-action buttons → trigger corresponding prompt files
        self.generate_npc_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("dm_action_generate_npc.md"))
        self.describe_surroundings_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("dm_action_describe_surroundings.md"))
        self.generate_encounter_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("dm_action_generate_encounter.md"))
        self.suggest_rumor_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("dm_action_suggest_rumor.md"))
        self.suggest_complication_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("dm_action_suggest_complication.md"))
        self.generate_mundane_items_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("dm_action_generate_mundane_items.md"))
        self.generate_loot_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("dm_action_generate_loot.md"))
        
        # --- Test button now loads and injects sample markdown/HTML ---
        '''
        test_md_file_path = Path("prompts/test_statblock_markdown.md")
        test_markdown_content = ""
        if test_md_file_path.is_file():
            test_markdown_content = test_md_file_path.read_text(encoding="utf-8")
            self.test_button.clicked.connect(lambda: self.handle_llm_response(test_markdown_content))
        else:
            error_msg = f"Test markdown file not found: {test_md_file_path}"
            self.app_logger.error(error_msg)
            # Disable button or connect to error display if file missing
            self.test_button.setToolTip(error_msg)
            self.test_button.setEnabled(False) # Disable if file missing
            # Alternative: connect to a lambda that shows the error
            # self.test_button.clicked.connect(lambda: self._show_error_message(error_msg))
        # ------------------------------------------------------------
        '''
        self.test_button.clicked.connect(lambda: self.inject_sample_statblock())

        # Connect ControlsWidget high-level signals
        cw = self.controls_widget
        cw.audio_action_requested.connect(self._on_audio_action_request)
        cw.dm_action_requested.connect(self._on_dm_action_request)
        cw.transcription_settings_changed.connect(
            lambda d: self.transcription_controller.set_min_sentences(d.get("min_sentences", 1))
        )
        cw.flush_requested.connect(self.transcription_controller.flush_accumulator)
        cw.show_user_speech_toggled.connect(self.user_speech_widget.set_visibility)
        cw.llm_params_changed.connect(self._on_llm_params_changed)

        # Manual DM prompt submission
        cw.dm_input_widget.prompt_submitted.connect(self._on_manual_dm_prompt)

    def _on_transcription_started(self):
        """Updates UI when transcription starts."""
        self.app_logger.info("MainWindow: Transcription started signal received.")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar().showMessage("Listening...")

    def _on_transcription_stopped(self):
        """Updates UI when transcription stops."""
        self.app_logger.info("MainWindow: Transcription stopped signal received.")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.statusBar().showMessage("Ready.")
        # Clear the hypothesis display when stopped
        self.update_user_speech_pane("")

    def _on_llm_processing_started(self):
        """Updates UI (e.g., status bar, disable buttons) when LLM starts."""
        self.app_logger.info("MainWindow: LLM processing started signal received.")
        self._set_dm_actions_enabled(False)
        self.statusBar().showMessage("LLM Processing...")
        # Disable manual DM input widget
        self.controls_widget.dm_input_widget.set_processing(True)

    def _on_llm_processing_finished(self):
        """Updates UI when LLM finishes."""
        self.app_logger.info("MainWindow: LLM processing finished signal received.")
        self._set_dm_actions_enabled(True)
        # Revert status bar based on transcription state
        is_transcribing = self.transcription_controller.transcription_thread is not None and \
                          self.transcription_controller.transcription_thread.is_alive()
        self.statusBar().showMessage("Listening..." if is_transcribing else "Ready.")
        # Re-enable manual DM input widget
        self.controls_widget.dm_input_widget.set_processing(False)

    def _set_dm_actions_enabled(self, enabled: bool):
        # Delegate to ControlsWidget toggler
        self.controls_widget.set_controls_enabled(enabled)

    def update_user_speech_pane(self, hypothesis_text: str):
        """
        Updates the user speech pane with settled text that has already been finalized
        (stored in ``self.settled_user_text``) and the current in-progress hypothesis
        provided as ``hypothesis_text``.
        
        Settled text is rendered using the default text colour, while the hypothesis
        portion (if any) is rendered in grey and separated by a horizontal marker so
        that the DM can clearly distinguish between what has already been spoken and
        what is still being recognised.
        """
        self.user_speech_widget.update_display(hypothesis_text)

    def _handle_final_chunk(self, chunk_text: str):
        """
        Handles a finalized chunk from the TranscriptionController.
        Updates the settled text state and triggers the LLMController.
        """
        self.app_logger.debug(f"MainWindow received final chunk: {chunk_text[:80]}...")
        self.user_speech_widget.append_settled_chunk(chunk_text)
        # Trigger LLM processing
        self.llm_controller.process_final_chunk(chunk_text)

    def handle_llm_response(self, response_markdown: str):
        html = extract_statblock_html(response_markdown)
        if html is None:
            html = convert_markdown_to_html(response_markdown)  # your existing markdown → HTML
        self.output_widget.append_html(html)
        self.conv_logger.info(json.dumps({"role": "ASSISTANT", "content": response_markdown}))

    def inject_sample_statblock(self):
        html = """
    <stat-block>
    <creature-heading>
        <h1>Skeletal Knight</h1>
        <h2>Medium undead, lawful evil</h2>
    </creature-heading>

    <top-stats>
        <property-line><h4>Armor Class</h4><p>18 (chain mail, shield)</p></property-line>
        <property-line><h4>Hit Points</h4><p>67 (9d8 + 27)</p></property-line>
        <property-line><h4>Speed</h4><p>30 ft.</p></property-line>

        <abilities-block data-str="17" data-dex="13" data-con="16"
                        data-int="6" data-wis="10" data-cha="9"></abilities-block>

        <property-line><h4>Challenge</h4><p>4 (1 100 XP)</p></property-line>
    </top-stats>

    <property-block>
        <h4>Undead Fortitude.</h4>
        <p>If damage reduces the knight to 0 hp, it makes a CON save DC 10 or
        half the damage taken, whichever is higher. On a success, it drops
        to 1 hp instead.</p>
    </property-block>
    </stat-block>
    """
        self.output_widget.append_html(html)

        # Once the response is processed, the LLM controller will emit processing_finished
        # which re-enables DM buttons via _on_llm_processing_finished.

    def _show_error_message(self, message: str):
        """Displays an error message (e.g., in status bar or dialog)."""
        self.app_logger.error(f"MainWindow received error signal: {message}")
        # Simple status bar message for now
        self.statusBar().showMessage(f"Error: {message}", 10000) # Show for 10 seconds
        # Re-enable DM actions after error
        self._set_dm_actions_enabled(True) # Re-enable actions after error
        # TODO: Consider using QMessageBox for critical errors like missing API keys/prompts
        # if "API Key not found" in message or "prompt file not found" in message:
        #    QMessageBox.critical(self, "Critical Error", message)

    def closeEvent(self, event):
        super().closeEvent(event)

    def _on_user_speech_checkbox_changed(self, state: int):
        """Show/hide the user-speech pane and persist the preference to the config."""
        show = state == Qt.Checked
        # --- Adjust splitter visibility instead of just the widget ---
        # Find the index of the user speech display in the splitter
        user_speech_widget = self.user_speech_widget
        splitter_index = -1
        for i in range(self.splitter.count()):
            if self.splitter.widget(i) == user_speech_widget:
                splitter_index = i
                break
        
        if splitter_index != -1:
            # Hide/show by setting size to 0 or restoring previous sizes
            if show:
                # Restore sizes (simple approach: equal split or remember last)
                # Let's try restoring to a default split for simplicity
                current_sizes = self.splitter.sizes()
                if sum(current_sizes) > 0 and current_sizes[splitter_index] == 0: # Check if it was hidden
                     # Simple restore: give it some space, e.g., 40% or restore previous non-zero
                     total_width = sum(current_sizes)
                     restore_width = max(100, int(total_width * 0.4)) # Ensure minimum width
                     other_width = total_width - restore_width
                     new_sizes = [0] * self.splitter.count()
                     new_sizes[splitter_index] = restore_width
                     # Distribute remaining width (assuming 2 panes for simplicity)
                     other_index = 1 - splitter_index # Assumes only 2 panes
                     new_sizes[other_index] = other_width
                     self.splitter.setSizes(new_sizes)
                elif sum(current_sizes) == 0: # If splitter somehow has 0 size
                    self.splitter.setSizes([500, 500]) # Fallback to default even split

                self.user_speech_widget.set_visibility(True) # Ensure widget is visible
            else:
                # Hide by setting size to 0
                current_sizes = self.splitter.sizes()
                if sum(current_sizes) > 0 : # Only modify if sizes are non-zero
                    total_width = sum(current_sizes)
                    new_sizes = [0] * self.splitter.count()
                    new_sizes[splitter_index] = 0
                    # Give all width to the other pane (assuming 2 panes)
                    other_index = 1 - splitter_index
                    new_sizes[other_index] = total_width
                    self.splitter.setSizes(new_sizes)
                self.user_speech_widget.set_visibility(False) # Also hide widget just in case

        # Original logic for config saving
        self.config.set("ui_settings.show_user_speech", show)
        self.config.save()
        self.app_logger.info(f"'Show User Speech' set to {show}")
        # ---------------------------------------------------------

    def _on_audio_source_changed(self, selected_source: str):
        """Proxy combo-box changes to the AudioController (persists via that class)."""
        # Determine if transcription is running so AudioController can warn appropriately.
        is_running = (
            self.transcription_controller.transcription_thread is not None
            and self.transcription_controller.transcription_thread.is_alive()
        )
        self.audio_controller.set_audio_source(selected_source, is_running)

    # ---------------------------------------------------------------------
    # New handlers for high-level signals
    # ---------------------------------------------------------------------
    def _on_audio_action_request(self, action: str):  # noqa: D401
        if action == "start":
            self.transcription_controller.start_transcription()
        elif action == "stop":
            self.transcription_controller.stop_transcription()
        elif action.startswith("source:"):
            source = action.split(":", 1)[1]
            self._on_audio_source_changed(source)

    def _on_dm_action_request(self, prompt_filename: str, params: dict):  # noqa: D401
        self.llm_controller.pc_level = params.get("pc_level", self.llm_controller.pc_level)
        self.llm_controller.action_quantity = params.get("quantity", self.llm_controller.action_quantity)
        self.llm_controller.trigger_dm_action(prompt_filename)

    def _on_llm_params_changed(self, params: dict):  # noqa: D401
        self.llm_controller.pc_level = params.get("pc_level", self.llm_controller.pc_level)
        self.llm_controller.action_quantity = params.get("quantity", self.llm_controller.action_quantity)

    def _on_manual_dm_prompt(self, prompt_text: str):
        """Slot called when a manual DM prompt is submitted."""
        self.app_logger.info("Manual DM prompt submitted.")
        self.llm_controller.process_manual_dm_prompt(prompt_text)

# --- Main Execution --- (Entry point) - REMOVED
# def main(): ...
#
# if __name__ == "__main__": ... 