import os
import sys
import json
import logging # Keep this for basic config if needed, but LogManager handles specifics
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPalette, QColor

# Import the new LogManager
from log_manager import LogManager

# Set Chromium flags to try enabling hardware acceleration
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-gpu-blocklist --enable-gpu-rasterization --enable-zero-copy --use-gl=angle"

# Import the markdown conversion utility AND the CSS string
from models.markdown_utils import markdown_to_html_fragment, DND_CSS
from main_window import MainWindow # Keep this import

# --- Logging Setup (REMOVED) ---
# LOG_FILE = "app.log"
# def setup_logging(): ... (Function removed)
# --- End Logging Setup ---

def main():
    # --- Initialize LogManager FIRST --- 
    LogManager.initialize()
    # ---------------------------------
    
    # Get the app logger after initialization
    app_logger = LogManager.get_app_logger()

    # Try enabling software OpenGL - REMOVED TRY/EXCEPT
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    app_logger.info("Attempting to use software OpenGL.") # Use app_logger

    app = QApplication(sys.argv)

    # Set the Fusion style for a modern look
    app.setStyle("Fusion")

    # Create a dark palette
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    # Adjust disabled colors
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))

    # Apply the dark palette
    app.setPalette(dark_palette)

    window = MainWindow()
    window.show()

    # Log application exit
    exit_code = app.exec_()
    app_logger.info(f"Application exiting with code {exit_code}.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 