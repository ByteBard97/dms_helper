import logging
import sys
import os
from pathlib import Path
import datetime
import json # Added for JSON formatting

# --- JSON Formatter --- 
class JsonFormatter(logging.Formatter):
    """Formats log records as JSON strings."""
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            # Add other standard fields if needed
            # "name": record.name,
        }
        # Add message, which might be pre-formatted JSON string or regular msg
        if isinstance(record.msg, dict):
             log_entry.update(record.msg) # Merge dict directly
        elif isinstance(record.msg, str):
             # Try to parse if it looks like JSON, otherwise treat as plain message
             try:
                 msg_dict = json.loads(record.msg)
                 if isinstance(msg_dict, dict):
                     log_entry.update(msg_dict)
                 else:
                     # It's valid JSON but not a dict, store under 'message'
                     log_entry["message"] = msg_dict
             except json.JSONDecodeError:
                 # Not a JSON string, store as plain message
                 log_entry["message"] = record.getMessage()
        else:
            # Not a string or dict, use standard formatting
             log_entry["message"] = record.getMessage()

        # Include exception info if available
        if record.exc_info:
            log_entry['exc_info'] = self.formatException(record.exc_info)
        if record.stack_info:
             log_entry['stack_info'] = self.formatStack(record.stack_info)

        return json.dumps(log_entry)

# ---------------------

class LogManager:
    """Manages application logging configuration, including file rotation."""

    APP_LOG_FILENAME = "app.log"
    CONVERSATION_LOG_FILENAME = "session.log"
    RAW_TRANSCRIPT_LOG_FILENAME = "raw_transcript.log"
    ARCHIVE_FOLDER = "logs_archive"
    APP_LOGGER_NAME = "dms_helper"
    CONVERSATION_LOGGER_NAME = "conversation"
    RAW_TRANSCRIPT_LOGGER_NAME = "transcript_raw"

    _initialized = False

    @staticmethod
    def initialize():
        """Sets up logging handlers, formatters, and performs log rotation."""
        # --- DIAGNOSTIC PRINTS --- 
        sys.stderr.write("LogManager.initialize() called.\n")
        sys.stderr.flush()
        # -------------------------

        if LogManager._initialized:
            sys.stderr.write("LogManager: Already initialized. Returning.\n")
            sys.stderr.flush()
            return

        try:
            # --- *** Setup Paths to use 'logs' subdirectory *** ---
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True) # Ensure the logs directory exists
            # -------------------------------------------------------
            archive_dir = log_dir / LogManager.ARCHIVE_FOLDER
            archive_dir.mkdir(exist_ok=True) # Ensure archive directory exists
            sys.stderr.write(f"LogManager: Log directory: {log_dir.resolve()}\n")
            sys.stderr.write(f"LogManager: Archive directory path: {archive_dir.resolve()}\n")
            sys.stderr.flush()

            # File paths will now be relative to the logs directory
            app_log_file = log_dir / LogManager.APP_LOG_FILENAME
            session_log_file_jsonl = log_dir / f"{LogManager.CONVERSATION_LOG_FILENAME}.jsonl"
            raw_transcript_log_file = log_dir / LogManager.RAW_TRANSCRIPT_LOG_FILENAME

            # --- Archive existing logs (checks paths within ./logs/) ---
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            LogManager._archive_log(app_log_file, archive_dir, f"{LogManager.APP_LOG_FILENAME}_{timestamp}.log")
            LogManager._archive_log(session_log_file_jsonl, archive_dir, f"{LogManager.CONVERSATION_LOG_FILENAME}_{timestamp}.jsonl")
            LogManager._archive_log(raw_transcript_log_file, archive_dir, f"{LogManager.RAW_TRANSCRIPT_LOG_FILENAME}_{timestamp}.log")

            sys.stderr.write("LogManager: Finished archiving step.\n")
            sys.stderr.flush()
            
            # Get Logger Instances
            app_logger = logging.getLogger(LogManager.APP_LOGGER_NAME)
            conversation_logger = logging.getLogger(LogManager.CONVERSATION_LOGGER_NAME)
            raw_transcript_logger = logging.getLogger(LogManager.RAW_TRANSCRIPT_LOGGER_NAME)

            # Clear Existing Handlers
            sys.stderr.write(f"LogManager: Clearing existing handlers for {LogManager.APP_LOGGER_NAME}...\n")
            sys.stderr.flush()
            app_logger.handlers.clear()
            sys.stderr.write(f"LogManager: Clearing existing handlers for {LogManager.CONVERSATION_LOGGER_NAME}...\n")
            sys.stderr.flush()
            conversation_logger.handlers.clear()
            sys.stderr.write(f"LogManager: Clearing existing handlers for {LogManager.RAW_TRANSCRIPT_LOGGER_NAME}...\n")
            sys.stderr.flush()
            raw_transcript_logger.handlers.clear()

            # --- Configure App Logger (File path is now inside ./logs/) ---
            sys.stderr.write("LogManager: Configuring App Logger...\n")
            sys.stderr.flush()
            app_logger.setLevel(logging.DEBUG)
            app_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            )
            app_file_handler = logging.FileHandler(app_log_file, mode='w', encoding='utf-8') # Path is logs/app.log
            app_file_handler.setFormatter(app_formatter)
            app_logger.addHandler(app_file_handler)
            app_console_handler = logging.StreamHandler(sys.stderr)
            app_console_handler.setFormatter(app_formatter)
            app_logger.addHandler(app_console_handler)
            app_logger.propagate = False
            sys.stderr.write("LogManager: App Logger configured with handlers (DEBUG level) and propagate=False.\n")
            sys.stderr.flush()

            # --- Configure JS Logger (for WebEngine console messages) ---
            js_logger = logging.getLogger("JS")
            js_logger.setLevel(logging.DEBUG)
            # Add the same handlers as the app logger
            js_logger.addHandler(app_file_handler)
            js_logger.addHandler(app_console_handler)
            js_logger.propagate = False # Prevent duplication if root handler exists
            sys.stderr.write("LogManager: JS Logger configured with handlers (DEBUG level) and propagate=False.\n")
            sys.stderr.flush()
            # -----------------------------------------------------------

            # --- Configure Conversation Logger (File path is now inside ./logs/) ---
            sys.stderr.write("LogManager: Configuring Conversation Logger...\n")
            sys.stderr.flush()
            conversation_logger.setLevel(logging.INFO)
            json_formatter = JsonFormatter(datefmt='%Y-%m-%d %H:%M:%S')
            conversation_file_handler = logging.FileHandler(session_log_file_jsonl, mode='w', encoding='utf-8') # Path is logs/session.log.jsonl
            conversation_file_handler.setFormatter(json_formatter)
            conversation_logger.addHandler(conversation_file_handler)
            conversation_logger.propagate = False
            sys.stderr.write("LogManager: Conversation Logger configured with handlers.\n")
            sys.stderr.flush()

            # --- Configure Raw Transcript Logger (New) --- 
            sys.stderr.write("LogManager: Configuring Raw Transcript Logger...\n")
            sys.stderr.flush()
            # Set level to WARNING to avoid logging every segment (INFO/DEBUG level)
            raw_transcript_logger.setLevel(logging.WARNING)
            raw_formatter = logging.Formatter('%(asctime)s - %(message)s')
            raw_file_handler = logging.FileHandler(raw_transcript_log_file, mode='w', encoding='utf-8')
            raw_file_handler.setFormatter(raw_formatter)
            raw_transcript_logger.addHandler(raw_file_handler)
            raw_transcript_logger.propagate = False
            sys.stderr.write("LogManager: Raw Transcript Logger configured.\n")
            sys.stderr.flush()
            
            # Set Initialized Flag
            LogManager._initialized = True
            app_logger.info("LogManager initialized. Logging started.") 
            sys.stderr.write("LogManager: Initialization complete. Logged first message.\n")
            sys.stderr.flush()

        except Exception as e:
             # Catch any unexpected error during the whole init process
             print(f"[LogManager CRITICAL ERROR] Unhandled exception during initialize: {e}", file=sys.stderr)
             # Also try logging it, although handlers might not be set up
             try:
                 logging.getLogger(LogManager.APP_LOGGER_NAME).critical(f"Unhandled exception during initialize: {e}", exc_info=True)
             except Exception:
                 pass # Ignore errors during logging attempt itself
             # We probably should not proceed, maybe re-raise or set a global error flag?
             # For now, just print and potentially leave _initialized as False
             LogManager._initialized = False # Ensure it's false on error
             sys.stderr.write("LogManager: Initialization FAILED.\n")
             sys.stderr.flush()

    @staticmethod
    def _archive_log(log_file_path: Path, archive_dir: Path, archive_name: str):
        """Helper method to archive a single log file."""
        if log_file_path.exists():
            sys.stderr.write(f"LogManager: Archiving existing {log_file_path}...\n")
            sys.stderr.flush()
            try:
                archive_path = archive_dir / archive_name
                os.rename(log_file_path, archive_path)
                sys.stderr.write(f"LogManager: Archived {log_file_path.name} to {archive_path}\n")
                sys.stderr.flush()
            except OSError as e:
                print(f"[LogManager CRITICAL ERROR] Error archiving {log_file_path.name}: {e}", file=sys.stderr)
                sys.stderr.flush()
        else:
            sys.stderr.write(f"LogManager: No existing {log_file_path.name} in {log_file_path.parent} to archive.\n")
            sys.stderr.flush()

    @staticmethod
    def get_app_logger():
        """Returns the configured application logger."""
        if not LogManager._initialized:
            sys.stderr.write("LogManager: get_app_logger called before initialized! Attempting init...\n")
            sys.stderr.flush()
            LogManager.initialize() # Ensure initialized
            # Add check after init attempt
            if not LogManager._initialized:
                 print("[LogManager CRITICAL ERROR] Failed to initialize logging, returning dummy logger for app.", file=sys.stderr)
                 sys.stderr.flush()
                 # Return a dummy logger that does nothing to prevent crashes maybe?
                 # Or raise an exception? For now, return base logger which might complain.
                 return logging.getLogger(f"{LogManager.APP_LOGGER_NAME}_UNINITIALIZED")
        return logging.getLogger(LogManager.APP_LOGGER_NAME)

    @staticmethod
    def get_conversation_logger():
        """Returns the configured conversation logger."""
        if not LogManager._initialized:
            sys.stderr.write("LogManager: get_conversation_logger called before initialized! Attempting init...\n")
            sys.stderr.flush()
            LogManager.initialize() # Ensure initialized
             # Add check after init attempt
            if not LogManager._initialized:
                 print("[LogManager CRITICAL ERROR] Failed to initialize logging, returning dummy logger for conversation.", file=sys.stderr)
                 sys.stderr.flush()
                 return logging.getLogger(f"{LogManager.CONVERSATION_LOGGER_NAME}_UNINITIALIZED")
        return logging.getLogger(LogManager.CONVERSATION_LOGGER_NAME)

    @staticmethod
    def get_raw_transcript_logger():
        """Returns the configured raw transcript logger."""
        if not LogManager._initialized:
            sys.stderr.write("LogManager: get_raw_transcript_logger called before initialized! Attempting init...\n")
            sys.stderr.flush()
            LogManager.initialize()
            if not LogManager._initialized:
                 print("[LogManager CRITICAL ERROR] Failed to initialize logging, returning dummy logger for raw transcript.", file=sys.stderr)
                 sys.stderr.flush()
                 return logging.getLogger(f"{LogManager.RAW_TRANSCRIPT_LOGGER_NAME}_UNINITIALIZED")
        return logging.getLogger(LogManager.RAW_TRANSCRIPT_LOGGER_NAME)

# Example Usage (Optional, for testing):
# if __name__ == '__main__':
#     LogManager.initialize()
#     app_log = LogManager.get_app_logger()
#     conv_log = LogManager.get_conversation_logger()
#
#     app_log.debug("This is a debug message for app log.")
#     app_log.info("This is an info message for app log.")
#     conv_log.info("USER: Hello there.")
#     app_log.warning("This is a warning for app log.")
#     conv_log.info("ASSISTANT: Hi! How can I help?")
#     app_log.error("This is an error for app log.") 