import json
import os
from pathlib import Path
import logging
from typing import Any

# Configure logging for the config manager itself
config_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Basic config for this module if run standalone

class ConfigManager:
    """Manages loading, accessing, and saving application settings from/to config.json."""
    
    def __init__(self, config_filename="config.json"):
        """Initializes the ConfigManager.

        Args:
            config_filename (str): The name of the config file relative to project root.
        """
        self.config_path = Path(config_filename).resolve() # Store absolute path
        self.defaults = {
            "general": {
                "llm_model_name": "gemini-1.5-flash",
                "gatekeeper_model": "mistral:latest",
                "mute_playback": False
            },
            "paths": {
                "campaign_config": "source_materials/ceres_group/ceres_odyssey.json",
                "input_audio": "source_materials/recording_of_dm_resampled.wav",
                "gatekeeper_prompt": "prompts/gatekeeper_prompt.md",
                "main_prompt": "prompts/dm_assistant_prompt.md",
                "session_log": "logs/latest_session.log",
                "css_file": "css/dnd_style.css"
            },
            "servers": {
                "transcription_host": "localhost",
                "transcription_port": 9090,
                "ollama_host": "http://192.168.0.200:11434"
            },
            "ui_settings": {
                "show_user_speech": True
            },
            "session_state": {
                "last_audio_position_sec": 0.0
            },
            "audio_settings": {
                "last_playback_position": 0.0
            }
        }
        self.data = self.defaults.copy() # Start with defaults
        self.load()

    def load(self):
        """Loads configuration from the JSON file, merging with defaults."""
        loaded_data = {}
        if self.config_path.is_file():
            config_logger.info(f"Loading configuration from: {self.config_path}")
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
        else:
            config_logger.warning(f"Config file not found... Using defaults.")

        # Merge loaded data into defaults (ensures all keys exist)
        def merge_dicts(base, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    merge_dicts(base[key], value)
                else:
                    base[key] = value
            return base
        
        self.data = self.defaults.copy() # Start fresh with defaults
        self.data = merge_dicts(self.data, loaded_data) # Use helper
        config_logger.info("Configuration loaded.")

    def save(self):
        """Saves the current configuration data back to the JSON file."""
        config_logger.info(f"Saving configuration to: {self.config_path}")
        # No try/except for file writing per rules
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)
        config_logger.debug("Configuration saved successfully.") # Debug level for save success

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the configuration using a dot-separated key.

        Args:
            key: The dot-separated key (e.g., "servers.transcription_host").
            default: The value to return if the key is not found.

        Returns:
            The configuration value or the default.
        """
        try:
            value = self.data
            for k in key.split('.'):
                # Check if the current level is a dictionary and the key exists
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    # Key not found at this level, return default
                    config_logger.debug(f"Key '{k}' not found in path '{key}'. Returning default: {default}")
                    return default
            return value
        except Exception as e:
            # Catch any other unexpected errors during lookup
            config_logger.error(f"Error getting config key '{key}': {e}", exc_info=True)
            return default

    def set(self, key: str, value: Any):
        """Sets a configuration value using dot notation and saves immediately."""
        # No try/except per rules. Errors will propagate.
        keys = key.split('.')
        d = self.data
        for k in keys[:-1]: # Navigate to the parent dictionary
            # This part can still potentially raise errors if structure is unexpected
            # but we are avoiding try/except.
            if k not in d or not isinstance(d[k], dict):
                d[k] = {} # Create intermediate dictionaries if they don't exist
            d = d[k]
        
        final_key = keys[-1]
        if final_key in d and d[final_key] == value:
            config_logger.debug(f"Config key '{key}' already set to '{value}'. No change.")
            return 
            
        d[final_key] = value
        config_logger.debug(f"Set config key '{key}' = {value}")
        self.save() 