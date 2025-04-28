import sys
import json # Import json library
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QHBoxLayout, QLabel, QTextEdit, QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPalette, QColor

# Import the markdown conversion utility AND the CSS string
from markdown_utils import markdown_to_html_fragment, DND_CSS 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("D&D Helper Assistant")
        # Set an initial size; can be adjusted later
        self.setGeometry(100, 100, 800, 600)  

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
        self.start_button = QPushButton("Start Listening (Placeholder)")
        self.stop_button = QPushButton("Stop Listening (Placeholder)")
        
        # Test button for rendering
        self.test_render_button = QPushButton("Test Render")
        self.test_render_button.clicked.connect(self.test_markdown_render)

        # Add a new button for appending second markdown
        self.append_second_button = QPushButton("Append Second Markdown")
        self.append_second_button.clicked.connect(self.append_second_markdown)

        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addStretch() # Add spacer
        self.button_layout.addWidget(self.test_render_button)
        self.button_layout.addWidget(self.append_second_button)
        
        # Add button layout to main layout
        self.main_layout.addLayout(self.button_layout)

        # Connect signals to slots (implement actual functions later)
        # self.start_button.clicked.connect(self.start_listening)
        # self.stop_button.clicked.connect(self.stop_listening)

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
        # Use the JSON-encoded string in JavaScript
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
        # --------------------------------------------------

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

    # Placeholder methods for button actions
    # def start_listening(self):
    #     print("Start button clicked (Not implemented)")
    #     # Logic to start transcription/pipeline

    # def stop_listening(self):
    #     print("Stop button clicked (Not implemented)")
    #     # Logic to stop transcription/pipeline 