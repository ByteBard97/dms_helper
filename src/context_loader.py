"""
Handles loading and combining context files based on a campaign config file.
"""

import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global Configuration ---
# Removed DEFAULT_CONTEXT_FILES constant

# Define the footer for the LLM context (preamble comes from config file)
CONTEXT_FOOTER = "\n--- END CONTEXT ---"
# --------------------------

def load_preamble(preamble_file_path: Optional[str]) -> Optional[str]:
    """Loads the context preamble from the specified file path."""
    if not preamble_file_path:
        logging.warning("No preamble file specified in config.")
        return "" # Return empty string if no preamble specified

    preamble_path = Path(preamble_file_path)
    if not preamble_path.is_file():
        logging.error(f"Preamble file not found: {preamble_path}")
        return None
    logging.info(f"Loading preamble from: {preamble_path}")
    # No try block as per rules
    return preamble_path.read_text(encoding="utf-8")

def _load_single_file_content(file_path_str: Optional[str]) -> Optional[str]:
    """Loads content from a single file path string. Returns None if path is None or file not found."""
    if not file_path_str:
        return None
    file_path = Path(file_path_str)
    if file_path.is_file():
        logging.info(f"Loading context from: {file_path}")
        # No try block as per rules
        content = file_path.read_text(encoding="utf-8")
        
        # --- Add logging for first 5 lines --- 
        # logging.info(f"  -> Preparing to send file: {file_path.name}")
        # lines = content.splitlines()
        # num_lines_to_log = min(len(lines), 5)
        # for i in range(num_lines_to_log):
            # Indent logged lines for clarity
            # logging.info(f"     | {lines[i]}")
        # if len(lines) > 5:
            # logging.info("     | ... (file truncated for log)")
        # ---------------------------------------
        
        return content
    else:
        logging.warning(f"Context file not found, skipping: {file_path}")
        return None

def load_and_combine_context(campaign_config_path: str) -> Optional[str]:
    """
    Loads campaign config, reads specified context files, and combines them.

    Args:
        campaign_config_path (str): Path to the campaign JSON configuration file.

    Returns:
        Optional[str]: The combined context string (preamble + file contents + footer),
                       or None if config/preamble loading fails or no files are found.
    """
    config_path = Path(campaign_config_path)
    if not config_path.is_file():
        logging.error(f"Campaign configuration file not found: {config_path}")
        return None

    logging.info(f"Loading campaign configuration from: {config_path}")
    # No try block as per rules
    config_data: Dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))

    preamble = load_preamble(config_data.get("preamble_file"))
    if preamble is None:
        # load_preamble logs error if file specified but not found
        # If preamble_file key is missing entirely, preamble will be "" (empty string)
        # We only fail hard if a specified preamble file is missing.
        if config_data.get("preamble_file"):
             return None # Fail if specified preamble couldn't load
        else:
             preamble = "" # Proceed without preamble if not specified

    combined_content = [preamble]
    files_loaded_successfully = False

    # Load individual files specified directly
    file_keys_to_load = ["pc_description_file", "current_state_file"]
    for key in file_keys_to_load:
        content = _load_single_file_content(config_data.get(key))
        if content:
            combined_content.append(f"\n\n--- Context Section: {key} ({config_data.get(key)}) ---\n\n")
            combined_content.append(content)
            files_loaded_successfully = True

    # Load files from lists
    list_keys_to_load = ["adventure_files", "extra_lore_files"]
    for key in list_keys_to_load:
        file_list = config_data.get(key, [])
        if not isinstance(file_list, list):
            logging.warning(f"Config key '{key}' is not a list, skipping.")
            continue
        for file_path_str in file_list:
            content = _load_single_file_content(file_path_str)
            if content:
                combined_content.append(f"\n\n--- Context Section: {key} ({file_path_str}) ---\n\n")
                combined_content.append(content)
                files_loaded_successfully = True

    # If preamble loaded but no other files were found/specified, that's still okay
    if not files_loaded_successfully and preamble == "":
        logging.error("Failed to load preamble and no other context files were found or specified.")
        return None
    elif not files_loaded_successfully:
         logging.warning("No specific context files found/loaded, proceeding with only preamble.")

    combined_content.append(CONTEXT_FOOTER)
    return "".join(combined_content)

# Example usage (for testing purposes)
if __name__ == "__main__":
    logging.info("Testing context loader with campaign config...")

    # Specify the campaign config file to load (updated path)
    test_config_file = "source_materials/ceres_group/ceres_odyssey.json"

    logging.info(f"Attempting to load context using config: {test_config_file}")
    full_context = load_and_combine_context(test_config_file)

    if full_context:
        logging.info(f"Successfully loaded and combined context ({len(full_context)} characters).")
        # Avoid printing the whole thing, just show start and end
        print("\n--- Combined Context Snippet Start ---")
        print(full_context[:500]) # Print first 500 chars
        print("[...]")
        print(full_context[-500:]) # Print last 500 chars
        print("--- Combined Context Snippet End ---")
    else:
        logging.error("Failed to load context using campaign config.")

    logging.info("Context loader test finished.") 