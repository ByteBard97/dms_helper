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
    QSplitter, QSpinBox, QGridLayout, QComboBox, QMessageBox # Added QMessageBox for potential error handling
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
# --------------------------------------

# Project Imports
from log_manager import LogManager
from config_manager import ConfigManager
from audio_controller import AudioController
from transcription_controller import TranscriptionController
from llm_controller import LLMController
from markdown_utils import markdown_to_html_fragment

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
        self.setGeometry(100, 100, 1000, 700)

        # Use camelCase for PyQt built-in attributes/methods
        self.centralWidget_ = QWidget() # Note the underscore to avoid potential conflicts if needed, though unlikely here
        self.setCentralWidget(self.centralWidget_)
        self.main_layout = QVBoxLayout(self.centralWidget_)

        # Splitter - CREATE FIRST
        self.splitter = QSplitter(Qt.Horizontal)

        # Left Pane: LLM Output (Web View)
        self.output_display = QWebEngineView()
        # Correct way to access settings and attributes
        settings = self.output_display.settings() # Get settings instance
        settings.setAttribute(settings.WebAttribute.WebGLEnabled, False)
        settings.setAttribute(settings.WebAttribute.PluginsEnabled, False)

        # --- Revert to original initial HTML structure and baseUrl --- 
        initial_html_structure = """
<!DOCTYPE html>
<html>
<head>
<meta charset=\"UTF-8\">
<link rel=\"stylesheet\" href=\"css/dnd_style.css\"> 
</head>
<body>
    <h1>D&D Assistant Log</h1>
    <p>LLM Suggestions will appear here...</p>
    <hr>
</body>
</html>
"""
        # Use original baseUrl approach - assumes execution from project root
        self.output_display.setHtml(initial_html_structure, baseUrl=QUrl("file:///"))
        # -------------------------------------------------------------

        self.splitter.addWidget(self.output_display)

        # Right Pane: User Speech (Text Edit)
        self.user_speech_display = QTextEdit()
        self.user_speech_display.setReadOnly(True)
        self.user_speech_display.setPlaceholderText("Transcribed user speech will appear here...")
        self.splitter.addWidget(self.user_speech_display)

        # --- Add Splitter to Main Layout ---
        self.main_layout.addWidget(self.splitter)

        # Load initial visibility state from config
        self.show_user_speech_state = self.config.get("ui_settings.show_user_speech", True)
        self.user_speech_display.setVisible(self.show_user_speech_state)
        # --- Set initial splitter sizes AFTER splitter and its widgets are added ---
        self.splitter.setSizes([500, 500]) # Initial sizes

        # --- Top Button Layout ---
        self.top_button_layout = QHBoxLayout()

        # --- Add Audio Source Widgets Back ---
        self.audio_source_label = QLabel("Audio Source:")
        self.audio_source_combobox = QComboBox()
        self.audio_source_combobox.addItems(["File", "Microphone"])
        # Set initial value from AudioController state
        self.audio_source_combobox.setCurrentText(self.audio_controller.current_source)
        # -------------------------------------

        # --- Add Start/Stop Buttons Back ---
        self.start_button = QPushButton("Start Listening")
        self.stop_button = QPushButton("Stop Listening")
        self.stop_button.setEnabled(False) # Initially disabled
        # ---------------------------------

        # Show User Speech Checkbox (already exists)
        self.user_speech_checkbox = QCheckBox("Show User Speech")
        self.user_speech_checkbox.setChecked(self.show_user_speech_state)

        # --- Add Min Sentences Spinbox back ---
        self.min_sentences_label = QLabel("Min Sentences:")
        self.min_sentences_spinbox = QSpinBox()
        self.min_sentences_spinbox.setMinimum(1)
        self.min_sentences_spinbox.setMaximum(10)
        # Set initial value from TranscriptionController's accumulator
        self.min_sentences_spinbox.setValue(self.transcription_controller.accumulator.min_sentences)
        # --------------------------------------

        # Flush Button
        self.flush_button = QPushButton("Flush Accumulator")

        # --- Add widgets to top layout in CORRECT order ---
        self.top_button_layout.addWidget(self.audio_source_label)
        self.top_button_layout.addWidget(self.audio_source_combobox)
        self.top_button_layout.addWidget(self.start_button)
        self.top_button_layout.addWidget(self.stop_button)
        self.top_button_layout.addStretch() # Spacer
        self.top_button_layout.addWidget(self.user_speech_checkbox)
        self.top_button_layout.addWidget(self.min_sentences_label)
        self.top_button_layout.addWidget(self.min_sentences_spinbox)
        self.top_button_layout.addWidget(self.flush_button)
        # -----------------------------------------------------

        # --- Add top button layout to main layout AFTER it's populated ---
        self.main_layout.addLayout(self.top_button_layout)
        # --------------------------------------------------

        # --- DM Action Layout ---
        self.dm_action_layout = QGridLayout()

        # --- Parameters - CREATE FIRST ---
        self.pc_level_label = QLabel("PC Level:")
        self.pc_level_spinbox = QSpinBox()
        self.pc_level_spinbox.setRange(1, 20)
        # Set initial value from LLMController state
        self.pc_level_spinbox.setValue(self.llm_controller.pc_level)

        self.action_quantity_label = QLabel("Quantity:")
        self.action_quantity_spinbox = QSpinBox()
        self.action_quantity_spinbox.setRange(1, 10)
        # Set initial value from LLMController state
        self.action_quantity_spinbox.setValue(self.llm_controller.action_quantity)
        # ----------------------------------

        self.dm_action_layout.addWidget(self.pc_level_label, 0, 0)
        self.dm_action_layout.addWidget(self.pc_level_spinbox, 0, 1)
        self.dm_action_layout.addWidget(self.action_quantity_label, 0, 2)
        self.dm_action_layout.addWidget(self.action_quantity_spinbox, 0, 3)
        self.dm_action_layout.setColumnStretch(4, 1)

        # --- Action Buttons - CREATE FIRST ---
        self.generate_npc_button = QPushButton("Gen NPC")
        self.describe_surroundings_button = QPushButton("Describe Env")
        self.generate_encounter_button = QPushButton("Gen Encounter")
        self.suggest_rumor_button = QPushButton("Suggest Rumor")
        self.suggest_complication_button = QPushButton("Suggest Twist")
        self.generate_mundane_items_button = QPushButton("Gen Mundane")
        self.generate_loot_button = QPushButton("Gen Loot")
        # -------------------------------------

        # Add buttons to layout
        self.dm_action_layout.addWidget(self.generate_npc_button, 1, 0)
        self.dm_action_layout.addWidget(self.describe_surroundings_button, 1, 1)
        self.dm_action_layout.addWidget(self.generate_encounter_button, 1, 2)
        self.dm_action_layout.addWidget(self.suggest_rumor_button, 1, 3)
        self.dm_action_layout.addWidget(self.suggest_complication_button, 1, 4)
        self.dm_action_layout.addWidget(self.generate_mundane_items_button, 1, 5)
        self.dm_action_layout.addWidget(self.generate_loot_button, 1, 6)
        self.dm_action_layout.setColumnStretch(7, 1)
        # --- Add DM action layout to main layout AFTER it's populated ---
        self.main_layout.addLayout(self.dm_action_layout)
        # --------------------------------------------------

        # --- Add Status Bar ---
        self.statusBar().showMessage("Ready.")
        # ---------------------

        # --- Connect Signals and Slots ---
        self._connect_signals()
        # ---------------------------------

        # --- Initialize Settled Text ---
        # Could potentially load initial state if needed
        self.settled_user_text = "" # Reset on init
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
            self.update_user_speech_pane,
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

        # 7.  DM action parameter spinboxes → LLMController properties
        self.pc_level_spinbox.valueChanged.connect(lambda val: setattr(self.llm_controller, "pc_level", val))
        self.action_quantity_spinbox.valueChanged.connect(lambda val: setattr(self.llm_controller, "action_quantity", val))

        # 8.  DM-action buttons → trigger corresponding prompt files
        self.generate_npc_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("generate_npc_prompt.md"))
        self.describe_surroundings_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("describe_environment_prompt.md"))
        self.generate_encounter_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("generate_encounter_prompt.md"))
        self.suggest_rumor_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("suggest_rumor_prompt.md"))
        self.suggest_complication_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("suggest_complication_prompt.md"))
        self.generate_mundane_items_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("generate_mundane_items_prompt.md"))
        self.generate_loot_button.clicked.connect(lambda: self.llm_controller.trigger_dm_action("generate_loot_prompt.md"))

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

    def _on_llm_processing_finished(self):
        """Updates UI when LLM finishes."""
        self.app_logger.info("MainWindow: LLM processing finished signal received.")
        self._set_dm_actions_enabled(True)
        # Revert status bar based on transcription state
        is_transcribing = self.transcription_controller.transcription_thread is not None and \
                          self.transcription_controller.transcription_thread.is_alive()
        self.statusBar().showMessage("Listening..." if is_transcribing else "Ready.")

    def _set_dm_actions_enabled(self, enabled: bool):
        # Enable/disable the whole DM-action control section so the user cannot trigger while LLM is busy.
        self.action_quantity_spinbox.setEnabled(enabled)
        self.pc_level_spinbox.setEnabled(enabled)
        for btn in [
            self.generate_npc_button,
            self.describe_surroundings_button,
            self.generate_encounter_button,
            self.suggest_rumor_button,
            self.suggest_complication_button,
            self.generate_mundane_items_button,
            self.generate_loot_button,
        ]:
            btn.setEnabled(enabled)

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
        # Debug log – keep so we can still trace issues if they arise again.
        self.app_logger.debug(
            f"[DEBUG] update_user_speech_pane called – hypothesis length: {len(hypothesis_text)}"
        )

        # Prepare the HTML fragments.  We convert newlines to <br> so that the QTextEdit
        # (set via ``setHtml``) preserves line-breaks correctly.
        settled_html = self.settled_user_text.replace("\n", "<br>")

        separator = "\n\n--- In Progress ---\n" if hypothesis_text else ""
        in_progress_html = f"{separator}{hypothesis_text}".replace("\n", "<br>")

        # Combine into final HTML.  The hypothesis/in-progress portion is grey so it
        # visually contrasts with the settled text.
        final_html = (
            f"<span>{settled_html}</span>"
            f"<span style='color: gray;'>{in_progress_html}</span>"
        )

        # Write to the QTextEdit using setHtml so that the styling is applied.
        self.user_speech_display.setHtml(final_html)

        # Ensure the latest text is visible by scrolling to the bottom.
        self.user_speech_display.verticalScrollBar().setValue(
            self.user_speech_display.verticalScrollBar().maximum()
        )

    def _handle_final_chunk(self, chunk_text: str):
        """
        Handles a finalized chunk from the TranscriptionController.
        Updates the settled text state and triggers the LLMController.
        """
        self.app_logger.debug(f"MainWindow received final chunk: {chunk_text[:80]}...")
        # Append finalized chunk to settled text
        self.settled_user_text += chunk_text + "\n\n" # Add double newline for separation
        # Update the display immediately to show the settled text (without hypothesis)
        self.update_user_speech_pane("")
        # Now trigger the LLM processing
        self.llm_controller.process_final_chunk(chunk_text)

    def handle_llm_response(self, response_markdown: str):
        """Slot called when the LLMController emits a markdown response."""
        self.app_logger.info(f"MainWindow: Received LLM response – length {len(response_markdown)}")

        # Append to conversation log
        assistant_log_entry = {"role": "ASSISTANT", "content": response_markdown}
        self.conv_logger.info(json.dumps(assistant_log_entry))

        # Render in the left-hand web view
        self.append_markdown_output(response_markdown)

        # Once the response is processed, the LLM controller will emit processing_finished
        # which re-enables DM buttons via _on_llm_processing_finished.

    def _show_error_message(self, message: str):
        """Displays an error message (e.g., in status bar or dialog)."""
        self.app_logger.error(f"MainWindow received error signal: {message}")
        # Simple status bar message for now
        self.statusBar().showMessage(f"Error: {message}", 10000) # Show for 10 seconds
        # Re-enable DM actions after error display?
        self._set_dm_actions_enabled(True) # Re-enable actions after error
        # TODO: Consider using QMessageBox for critical errors like missing API keys/prompts
        # if "API Key not found" in message or "prompt file not found" in message:
        #    QMessageBox.critical(self, "Critical Error", message)

    def closeEvent(self, event):
        super().closeEvent(event)

    def _on_user_speech_checkbox_changed(self, state: int):
        """Show/hide the user-speech pane and persist the preference to the config."""
        show = state == Qt.Checked
        self.user_speech_display.setVisible(show)
        self.config.set("ui_settings.show_user_speech", show)
        self.config.save()
        self.app_logger.info(f"'Show User Speech' set to {show}")

    def _on_audio_source_changed(self, selected_source: str):
        """Proxy combo-box changes to the AudioController (persists via that class)."""
        # Determine if transcription is running so AudioController can warn appropriately.
        is_running = (
            self.transcription_controller.transcription_thread is not None
            and self.transcription_controller.transcription_thread.is_alive()
        )
        self.audio_controller.set_audio_source(selected_source, is_running)

    # ---------------------------------------------------------------------
    # Helper for rendering markdown into the QWebEngineView
    # ---------------------------------------------------------------------
    def append_markdown_output(self, md_text: str):
        """Converts markdown to HTML fragment and appends it to the web view."""
        html_fragment = markdown_to_html_fragment(md_text)

        # Encode as JSON string so it can be safely injected via JavaScript
        safe_html_fragment = json.dumps(html_fragment)

        script = f"""
        var body = document.body;
        var newContent = document.createElement('div');
        newContent.innerHTML = {safe_html_fragment};
        while (newContent.firstChild) {{
            body.appendChild(newContent.firstChild);
        }}
        window.scrollTo(0, document.body.scrollHeight);
        """

        self.output_display.page().runJavaScript(script)

# --- Main Execution --- (Entry point) - REMOVED
# def main(): ...
#
# if __name__ == "__main__": ... 