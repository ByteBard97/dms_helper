import sys
import json # Import json library
import queue # Import queue instead of deque
import threading # Added for LLM worker
import time      # Added for LLM worker simulation (will be removed)
import os        # Added for API key
from dotenv import load_dotenv # Added for API key
import google.generativeai as genai # Added for Gemini
import ollama # Added for gatekeeper
from pathlib import Path # Added for prompt file path
from typing import List, Dict, Any

# Import the markdown conversion utility AND the CSS string
from markdown_utils import markdown_to_html_fragment, DND_CSS 

# Project imports (Ensure these are accessible)
from context_loader import load_and_combine_context # Assuming context needed
from transcript_accumulator import TranscriptAccumulator # Added
from config_manager import ConfigManager # Import the new manager
# Import the transcription client directly - ImportError will propagate if missing
from whisper_live_client.client import TranscriptionClient

# Constants are now managed by ConfigManager

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QHBoxLayout, QLabel, QTextEdit, QSizePolicy, QCheckBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl, QMetaObject, Q_ARG, pyqtSignal, QObject
from PyQt5 import QtCore # Add missing import
from PyQt5.QtGui import QPalette, QColor

class MainWindow(QMainWindow):
    # Define custom signals
    transcription_received = pyqtSignal(list)
    llm_response_received = pyqtSignal(str) # Signal for LLM response
    
    def __init__(self):
        super().__init__()

        # Initialize Config Manager FIRST
        self.config = ConfigManager() 

        self.setWindowTitle("D&D Helper Assistant")
        # Set an initial size; can be adjusted later
        self.setGeometry(100, 100, 800, 600)  

        # LLM, Gatekeeper, Accumulator and State Initialization
        self.chat_session = None
        self.ollama_client = None
        self.gatekeeper_prompt_template = None
        self.main_prompt_template = None # Add main template reference
        self.accumulator = TranscriptAccumulator() # Initialize accumulator
        self.initialize_llm_and_gatekeeper()
        
        # --- Separate Queues --- 
        self.segment_queue = queue.Queue() # For TranscriptionClient -> Monitor Thread
        self.chunk_queue = queue.Queue()   # For Handler -> Processing Logic
        # -----------------------
        
        self.is_llm_processing = False 
        # Load initial checkbox state from config
        self.show_user_speech = self.config.get("ui_settings.show_user_speech", True)
        
        # Transcription client and thread references
        self.transcription_client = None
        self.transcription_thread = None
        self.queue_monitor_stop_event = threading.Event()
        self.queue_monitor_thread = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Output Display Area (Now QWebEngineView) ---
        self.output_display = QWebEngineView()
        # self.output_display.setReadOnly(True) # Not applicable to QWebEngineView
        self.output_display.settings().setAttribute(
            self.output_display.settings().WebAttribute.WebGLEnabled, False
        ) # Disable WebGL for slightly less resource usage if not needed
        self.output_display.settings().setAttribute(
            self.output_display.settings().WebAttribute.PluginsEnabled, False
        ) # Disable plugins
        # self.output_display.setOpenExternalLinks(True) # Default behavior for web view

        # --- Load Initial HTML Structure with CSS --- 
        # Note: background color now handled by CSS within body/html
        self.initial_html_structure = """
<!DOCTYPE html>
<html>
<head>
<meta charset=\"UTF-8\">
<link rel=\"stylesheet\" href=\"css/dnd_style.css\">
</head>
<body>
    <h1>D&D Assistant Log</h1> 
    <p>Suggestions will appear below...</p>
    <hr>
</body>
</html>
"""
        # Use setHtml with a base URL (important for resolving relative paths if any)
        self.output_display.setHtml(self.initial_html_structure, baseUrl=QUrl("file:///"))
        # --------------------------------------------
        
        self.main_layout.addWidget(self.output_display)

        # --- Button Layout ---
        self.button_layout = QHBoxLayout() # Horizontal layout for buttons

        # Placeholder buttons
        self.start_button = QPushButton("Start Listening")
        self.stop_button = QPushButton("Stop Listening")
        
        # Test button for rendering
        self.test_render_button = QPushButton("Test Render")
        self.test_render_button.clicked.connect(self.test_markdown_render)

        # Add a new button for appending second markdown
        self.append_second_button = QPushButton("Append Second Markdown")
        self.append_second_button.clicked.connect(self.append_second_markdown)

        self.user_speech_checkbox = QCheckBox("Show User Speech")
        self.user_speech_checkbox.setChecked(self.show_user_speech)
        self.user_speech_checkbox.stateChanged.connect(self.on_user_speech_checkbox_changed)

        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addStretch() # Add spacer
        self.button_layout.addWidget(self.test_render_button)
        self.button_layout.addWidget(self.append_second_button)
        self.button_layout.addWidget(self.user_speech_checkbox)
        
        # Add button layout to main layout
        self.main_layout.addLayout(self.button_layout)

        # Connect signals to slots (implement actual functions later)
        # self.start_button.clicked.connect(self.start_listening)
        # self.stop_button.clicked.connect(self.stop_listening)

        # Connect the start button
        self.start_button.clicked.connect(self.start_audio_processing)
        # Initially disable the stop button
        self.stop_button.setEnabled(False)

        # Connect the custom signal to the handler slot
        self.transcription_received.connect(self.handle_transcription_result)
        self.llm_response_received.connect(self.handle_llm_response) # Connect LLM signal
        # ----------------------------------------------

    def initialize_llm_and_gatekeeper(self):
        """Initializes LLMs, loads prompts, and accumulator."""
        print("Initializing Systems from Config...")
        
        # Get paths from config, resolving relative to project root
        project_root = Path(__file__).parent.parent # Assuming main_window.py is in src/
        gatekeeper_prompt_path_str = self.config.get("paths.gatekeeper_prompt", "prompts/gatekeeper_prompt.md")
        main_prompt_path_str = self.config.get("paths.main_prompt", "prompts/dm_assistant_prompt.md")
        campaign_config_path_str = self.config.get("paths.campaign_config", "source_materials/default_campaign.json")
        
        gatekeeper_prompt_path = project_root / gatekeeper_prompt_path_str
        main_prompt_path = project_root / main_prompt_path_str
        campaign_config_path = project_root / campaign_config_path_str
        
        # Load Main Prompt Template
        if main_prompt_path.is_file():
            self.main_prompt_template = main_prompt_path.read_text(encoding="utf-8")
            print("Main prompt template loaded.")
        else:
            print(f"ERROR: Main prompt file not found: {main_prompt_path}")
            self.main_prompt_template = "{transcript_chunk}" 
            print("Warning: Using fallback main prompt.")

        # Load Gatekeeper Prompt
        if gatekeeper_prompt_path.is_file():
            self.gatekeeper_prompt_template = gatekeeper_prompt_path.read_text(encoding="utf-8")
            print("Gatekeeper prompt loaded.")
        else:
            print(f"ERROR: Gatekeeper prompt file not found: {gatekeeper_prompt_path}")
            self.gatekeeper_prompt_template = "Context: {accumulated_chunk}... Respond ONLY YES or NO."
            print("Warning: Using fallback gatekeeper prompt.")
            
        # Initialize Ollama Client
        ollama_host = self.config.get("servers.ollama_host", "http://localhost:11434")
        self.ollama_client = ollama.Client(host=ollama_host)
        print(f"Ollama client initialized for host: {ollama_host}")
        
        # Initialize Gemini LLM
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("ERROR: Google API Key not found...")
            self.chat_session = None
            return 

        llm_model_name = self.config.get("general.llm_model_name", "gemini-1.5-flash")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(llm_model_name)
        
        initial_context = load_and_combine_context(str(campaign_config_path)) # Pass absolute path string
        if not initial_context:
            print(f"Warning: Failed to load context from {campaign_config_path}. Using fallback.")
            initial_context = "No initial context provided."
            
        initial_history = [
            {'role': 'user', 'parts': [initial_context]},
            {'role': 'model', 'parts': ["Okay, context loaded."]}
        ]
        self.chat_session = model.start_chat(history=initial_history)
        print(f"LLM chat session started with model: {llm_model_name}")

    def append_markdown_output(self, md_text: str):
        """Converts Markdown text to HTML fragment and appends it to the web view."""
        html_fragment = markdown_to_html_fragment(md_text)
        
        # --- DEBUG: Print the generated HTML fragment (can keep for now) ---
        print("--- Generated HTML Fragment ---")
        print(html_fragment)
        print("-------------------------------")
        # ---------------------------------------------
        
        # Safely encode the HTML fragment as a JSON string
        safe_html_fragment = json.dumps(html_fragment)

        # --- Logic to append fragment to QWebEngineView --- 
        script = f"""
        var body = document.body;
        var newContent = document.createElement('div'); 
        // Assign the JSON string (which is already correctly escaped for JS)
        newContent.innerHTML = {safe_html_fragment};
        // Append all children of the new div to the body
        while (newContent.firstChild) {{
            body.appendChild(newContent.firstChild);
        }}
        window.scrollTo(0, document.body.scrollHeight);
        """
        self.output_display.page().runJavaScript(script)

    def test_markdown_render(self):
        """Callback for the test render button."""
        # Updated sample markdown with HTML for stat block
        sample_markdown = """# Session Notes: The Whispering Caves

## Party Members
*   **Gimli Stonehand** - *Dwarf Fighter* (Level 5) - Currently low on HP!
*   *Elara Meadowlight* - **Elf Ranger** (Level 5) - Used `Hunter's Mark` last turn.
*   [Zaltar the Mysterious](https://example.com/character/zaltar) - Human Wizard (Level 5) - Preparing *Fireball*.

---

## Location: Cave Entrance Chamber

The air hangs heavy with the smell of damp earth and something vaguely metallic. Water drips intermittently from stalactites, echoing in the vast chamber.

> *"Proceed with caution, friends. I sense a presence... ancient and watchful."* - Zaltar

### Notable Features:
1.  A crumbling stone altar covered in faded runes.
2.  A narrow stream flowing from a crack in the western wall.
3.  Piles of bones (mostly goblinoid) scattered near the northern passage.

**Possible Actions:**
- Investigate the altar (`DC 14 Investigation` to decipher runes).
- Follow the stream (`DC 12 Stealth` to avoid notice).
- Check the bones (`DC 10 Medicine` to determine cause of death).

## Encounter: Goblin Patrol

Suddenly, guttural shouts echo from the northern passage! Three goblins emerge, wielding crude scimitars and hide shields.

<div class="stat-block">
  <div class="stat-block-title">Goblin (Simplified)</div>
  <div class="stat-block-line"><span class="stat-block-property">Armor Class:</span> <span class="stat-block-value">15</span></div>
  <div class="stat-block-line"><span class="stat-block-property">Hit Points:</span> <span class="stat-block-value">7</span></div>
  <div class="stat-block-line"><span class="stat-block-property">Speed:</span> <span class="stat-block-value">30ft</span></div>
  <div class="stat-block-line"><span class="stat-block-property">Actions:</span> <span class="stat-block-value">Scimitar, Shortbow</span></div>
</div>

Roll initiative!

---

## Altar Investigation

Gimli carefully examines the altar. The runes seem to depict a ritual sequence.

### Ritual Steps (Deciphered):
1.  Place the **Iron Key** upon the central glyph.
2.  Anoint the key with **three drops** of fresh blood.
3.  Chant the incantation: "*Ignis revelare secreta*".
4.  The altar is expected to reveal a hidden passage.

---

## Nearby Fungi Patch

Elara spots a patch of glowing fungi near the stream.
*   **Violet Fungi:** Pulsating gently, possibly poisonous.
*   **Blue Caps:** Known for their use in healing salves.
*   **Shriekers:** Appear dormant, but could alert nearby creatures if disturbed.

---

## Goblin Loot Table (Example)

| d6 Roll | Item Found                    | Value (gp) | Notes                       |
| :------ | :---------------------------- | :--------- | :-------------------------- |
| 1-2     | Rusty Scimitar                | 1          | Barely serviceable          |
| 3       | Pouch with `2d4` copper pieces | <1         | Smells faintly of goblin   |
| 4       | Half-eaten rat jerky        | 0          | Questionable edibility    |
| 5       | A single shiny button         | 0          | Seems oddly out of place    |
| 6       | Crude map drawn on hide       | 5          | Shows nearby tunnels        |

---

*Remember to check light sources and marching order.*"""
        self.append_markdown_output(sample_markdown)

    # Implement the callback for the new button
    def append_second_markdown(self):
        second_markdown = """# Interlude: The Forgotten Shrine\n\n## New Discovery\nThe party stumbles upon a hidden shrine, its walls covered in ancient glyphs.\n\n> *A faint humming fills the air, and the temperature drops.*\n\n### Shrine Features\n- A cracked obsidian altar\n- Flickering blue flames\n- Mysterious runes that glow when touched\n\n**Possible Actions:**\n- Attempt to decipher the runes (`DC 15 Arcana`).\n- Offer a sacrifice on the altar.\n- Search for hidden compartments.\n\n## Encounter: Animated Statues\nTwo stone statues animate and block the exit!\n\n| Name           | AC | HP | Attack         |\n| -------------- | -- | -- | ------------- |\n| Stone Guardian | 17 | 30 | Slam (+5, 2d6+3) |\n| Stone Guardian | 17 | 30 | Slam (+5, 2d6+3) |\n\n*The battle begins anew...*\n"""
        self.append_markdown_output(second_markdown)

    def on_user_speech_checkbox_changed(self, state):
        """Handles checkbox state change and saves it to config."""
        self.show_user_speech = self.user_speech_checkbox.isChecked()
        print(f"Show User Speech set to: {self.show_user_speech}")
        # Save the new state to config
        self.config.set("ui_settings.show_user_speech", self.show_user_speech)

    # Add the new method for appending user speech
    def append_user_speech(self, user_text: str):
        """Appends formatted user speech to the web view if the checkbox is checked."""
        if not self.show_user_speech:
            return # Do nothing if checkbox is unchecked

        # Format the user speech (e.g., in a <pre> tag or a styled div)
        # Using a <pre> tag for simple, monospace, preformatted text
        # Or use a div with a class for more styling control via CSS
        # formatted_text = f'<div class="user-speech">{user_text}</div>'
        formatted_text = f'<pre class="user-speech">USER: {user_text}</pre>'
        
        safe_html_fragment = json.dumps(formatted_text)
        
        # --- Logic to append fragment to QWebEngineView --- 
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

    # Placeholder methods for button actions
    # def start_listening(self):
    #     print("Start button clicked (Not implemented)")
    #     # Logic to start transcription/pipeline

    # def stop_listening(self):
    #     print("Stop button clicked (Not implemented)")
    #     # Logic to stop transcription/pipeline 

    # --- Handle Transcription Segments --- 
    def handle_transcription_result(self, segments: List[Dict[str, Any]]):
        """Handles segments from signal: accumulates and queues chunks."""
        if not isinstance(segments, list):
             print(f"Warning: handle_transcription_result received non-list data: {type(segments)}")
             return
             
        # Accumulate the segments to form chunks
        accumulated_chunk = self.accumulator.add_segments(segments)

        # If a valid chunk is returned, add it to the CHUNK queue
        if accumulated_chunk:
            print(f"Accumulator produced chunk, adding to CHUNK queue: {accumulated_chunk[:80]}...")
            self.chunk_queue.put(accumulated_chunk) # Put chunk in chunk_queue
            self._maybe_process_next_input()
    # --- End Transcription Handling --- 

    def _maybe_process_next_input(self):
        """Checks CHUNK queue, displays user chunk, runs gatekeeper..."""
        if not self.chunk_queue.empty() and not self.is_llm_processing:
            # Get the accumulated chunk from the CHUNK queue
            chunk_to_process = self.chunk_queue.get()
            print(f"Processing chunk from queue: {chunk_to_process[:80]}...")
            
            # --- Display the user chunk NOW (if toggled) --- 
            self.append_user_speech(chunk_to_process) 
            # -----------------------------------------------
            
            # --- Gatekeeper Check --- 
            if not self.ollama_client or not self.gatekeeper_prompt_template:
                print("Warning: Ollama gatekeeper not ready. Skipping...")
                self.trigger_llm_request(chunk_to_process) # Pass the chunk 
                return
            
            gatekeeper_prompt_formatted = self.gatekeeper_prompt_template.format(accumulated_chunk=chunk_to_process)
            # ... (rest of gatekeeper logic sending gatekeeper_prompt_formatted)
            # ... if gatekeeper says YES:
            #         self.trigger_llm_request(chunk_to_process) # Pass the original chunk
            # ... else:
            #         self._maybe_process_next_input()
            print("--- Sending to Gatekeeper --- ")
            print(gatekeeper_prompt_formatted)
            print("-----------------------------")
            gatekeeper_model = self.config.get("general.gatekeeper_model", "mistral:latest")
            start_time = time.time()
            response = self.ollama_client.generate(
                model=gatekeeper_model,
                prompt=gatekeeper_prompt_formatted,
                stream=False,
                options={"temperature": 0.2}
            )
            end_time = time.time()
            duration = end_time - start_time
            gatekeeper_decision_raw = response.get("response", "").strip()
            gatekeeper_decision = gatekeeper_decision_raw.upper()
            print(f"--- Gatekeeper Response ({duration:.2f}s) --- ")
            print(gatekeeper_decision_raw)
            print(f"Decision: {gatekeeper_decision}")
            print("---------------------------------")
            if gatekeeper_decision == "YES":
                 print("Gatekeeper approved. Triggering main LLM.")
                 self.trigger_llm_request(chunk_to_process) # Pass the chunk
            else:
                 print("Gatekeeper rejected or response unclear. Skipping main LLM.")
                 self._maybe_process_next_input() # Check queue again
        else:
            # ... (handle queue empty or LLM busy)
            if self.chunk_queue.empty():
                print("Queue empty, nothing to process.")
            elif self.is_llm_processing:
                print("LLM is busy, waiting to process queue.")

    # --- Assumed method that handles the LLM response (connected via signal) ---
    # !!! IMPORTANT: Replace 'handle_llm_response' if your actual method name is different !!!
    def handle_llm_response(self, response_markdown: str):
        """Handles the LLM response signal: displays, resets flag, checks CHUNK queue."""
        print("Received MAIN LLM response signal.") 
        self.append_markdown_output(response_markdown)
        self.is_llm_processing = False # Reset flag AFTER processing response
        print("LLM processing finished. Checking CHUNK queue...")
        self._maybe_process_next_input() # Check for more queued input
    # --- End Assumed Method ---

    # --- Placeholder for the method that triggers the LLM request --- 
    # You should replace this with your actual implementation
    def trigger_llm_request(self, chunk_text: str):
        """Formats prompt and starts LLM worker thread which emits signal."""
        # Set flag FIRST, before checking session
        self.is_llm_processing = True 
        
        if not self.chat_session or not self.main_prompt_template:
            print("ERROR: LLM session or prompt template not ready.")
            self.is_llm_processing = False 
            self._maybe_process_next_input()
            return
        
        # Format the prompt using the loaded template
        formatted_prompt = self.main_prompt_template.format(transcript_chunk=chunk_text)
        print(f"Starting MAIN LLM worker thread...") 
        
        def llm_worker_func(prompt_to_send):
            response_text = "Error: LLM call failed."
            # Call Gemini directly, no try/except
            print(f"MAIN LLM Thread: Sending formatted prompt...")
            gemini_response = self.chat_session.send_message(prompt_to_send)
            if hasattr(gemini_response, 'text'):
                response_text = gemini_response.text
            else:
                response_text = f"Error: Unexpected LLM response format: {gemini_response}"
                print(f"MAIN LLM Thread: Error - {response_text}") # Log specific format error
            
            # --- Emit signal --- 
            print(f"MAIN LLM Thread: Emitting response signal...")
            self.llm_response_received.emit(response_text)
            # -------------------
            
        worker_thread = threading.Thread(target=llm_worker_func, args=(formatted_prompt,))
        worker_thread.start()

    def start_audio_processing(self):
        """Initializes and starts the transcription client and monitoring thread."""
        if self.transcription_thread and self.transcription_thread.is_alive():
            print("Transcription already running.")
            return

        # Get config values (as before)
        project_root = Path(__file__).parent.parent
        input_audio_path_str = self.config.get("paths.input_audio", "default_audio.wav")
        input_audio_path = str(project_root / input_audio_path_str)
        transcription_host = self.config.get("servers.transcription_host", "localhost")
        transcription_port = self.config.get("servers.transcription_port", 9090)
        
        print(f"Initializing transcription client for file: {input_audio_path}")
        if not os.path.exists(input_audio_path):
            print(f"ERROR: Input audio file not found at {input_audio_path}")
            return
            
        # --- Clear the SEGMENT queue --- 
        print("Clearing any previous SEGMENT queue data...")
        while not self.segment_queue.empty():
            try: self.segment_queue.get_nowait()
            except queue.Empty: break
        # ------------------------------
        # --- Clear the CHUNK queue too --- 
        print("Clearing any previous CHUNK queue data...")
        while not self.chunk_queue.empty():
             try: self.chunk_queue.get_nowait()
             except queue.Empty: break
        # -------------------------------

        # --- FIX: Mute playback based on config --- 
        mute_setting = self.config.get("general.mute_playback", True)
        wrapper_args = {"mute_audio_playback": mute_setting}
        print(f"Mute playback setting: {mute_setting}") # Log the setting being used
        # -----------------------------------------

        client_args = { 
             "output_queue": self.segment_queue, # Use SEGMENT queue
             "lang": None, "translate": False, "model": "large-v3", "use_vad": True, "log_transcription": False 
        }
        self.transcription_client = TranscriptionClient(
            host=transcription_host,
            port=transcription_port,
            **client_args,
            **wrapper_args 
        )
        print("Transcription client initialized.")

        # Start the client logic (audio playback/sending) in its thread
        print(f"Starting transcription client thread for file: {input_audio_path}")
        self.transcription_thread = threading.Thread(
            target=self.transcription_client, 
            args=(input_audio_path,),
            daemon=True
        )
        # --- NEW: Add a queue monitoring thread --- 
        self.queue_monitor_stop_event = threading.Event() # Signal to stop monitor
        self.queue_monitor_thread = threading.Thread(
            target=self._monitor_transcription_queue,
            daemon=True
        )
        # ------------------------------------------
        
        self.transcription_thread.start()
        self.queue_monitor_thread.start() # Start the monitor thread too
        print("Transcription and queue monitor threads started.")

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _monitor_transcription_queue(self):
        """Monitors the SEGMENT queue, emits transcription_received signal."""
        print("SEGMENT queue monitor thread started.")
        while not self.queue_monitor_stop_event.is_set():
            try:
                # Get data from SEGMENT queue
                data = self.segment_queue.get(block=True, timeout=0.5)
                if data is None: break
                
                # --- Type Check --- 
                if isinstance(data, list):
                    # Only emit if it's a list (expected segments)
                    self.transcription_received.emit(data)
                else:
                    # Log unexpected data type received from transcription client queue
                    print(f"Warning: Received non-list data type from segment_queue: {type(data)}. Value: {str(data)[:100]}")
                # ----------------
                
            except queue.Empty: continue
        print("SEGMENT queue monitor thread finished.")

    def stop_audio_processing(self):
        print("Stop button clicked - Stopping transcription...")
        
        # 1. Signal the monitor thread to stop
        if hasattr(self, 'queue_monitor_stop_event'):
             self.queue_monitor_stop_event.set()
             print("Queue monitor stop signal sent.")
        
        # 2. Signal the transcription client to stop (NEEDS IMPLEMENTATION in client)
        # This is the hard part - the client library might not have a clean stop method.
        # For now, we might have to rely on closing the connection or just joining the thread.
        if self.transcription_client and hasattr(self.transcription_client, 'stop'):
             print("Attempting to call client stop method...")
             self.transcription_client.stop() # Hypothetical stop method
        elif self.transcription_client and hasattr(self.transcription_client.client, 'close_websocket'):
             print("Attempting to close client websocket...")
             self.transcription_client.client.close_websocket()
        else:
             print("Warning: No clean stop method found for transcription client.")

        # 3. Join threads (with timeout)
        if self.transcription_thread and self.transcription_thread.is_alive():
            print("Waiting for transcription thread to join...")
            self.transcription_thread.join(timeout=2.0)
            if self.transcription_thread.is_alive():
                print("Warning: Transcription thread did not join cleanly.")
            else:
                print("Transcription thread joined.")
        
        if hasattr(self, 'queue_monitor_thread') and self.queue_monitor_thread.is_alive():
            print("Waiting for queue monitor thread to join...")
            self.queue_monitor_thread.join(timeout=1.0)
            if self.queue_monitor_thread.is_alive():
                print("Warning: Queue monitor thread did not join cleanly.")
            else:
                 print("Queue monitor thread joined.")
        
        # 4. Clean up resources
        self.transcription_client = None
        self.transcription_thread = None
        self.queue_monitor_thread = None # Clear reference
        # Clear the queue again
        while not self.segment_queue.empty():
            try: self.segment_queue.get_nowait() 
            except queue.Empty: break
        while not self.chunk_queue.empty():
            try: self.chunk_queue.get_nowait() 
            except queue.Empty: break
        print("Resources cleaned up.")

        # 5. Update UI state
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        print("Transcription stopped.")

# Need to import QtCore for invokeMethod
from PyQt5.QtCore import Qt, QUrl, QMetaObject, Q_ARG

# Ensure handle_llm_response is decorated or correctly registered if needed for invokeMethod,
# but direct method name string usually works for simple cases.
# def handle_llm_response(self, response_markdown: str):
#     ... (existing implementation is fine) ...
        