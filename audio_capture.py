"""
Handles capturing audio input from the microphone using sounddevice.
"""

import queue
import sys
import threading
from typing import Optional, List, Dict, Any

import numpy as np
import sounddevice as sd

# Constants
SAMPLE_RATE: int = 16000  # Whisper requires 16kHz
CHANNELS: int = 1         # Mono audio
BLOCK_DURATION_MS: int = 500 # Process audio in 500ms blocks (adjust as needed)
BLOCK_SIZE: int = int(SAMPLE_RATE * BLOCK_DURATION_MS / 1000)
BUFFER_BLOCKS: int = 30  # Buffer size in terms of blocks (e.g., 15 seconds)
DTYPE = 'float32'       # Data type for audio samples (as used by sounddevice)

# --- Globals (consider encapsulating in a class later) ---
# Use a thread-safe queue to pass audio data from the callback to the main thread
audio_queue: queue.Queue[np.ndarray] = queue.Queue()
# Use a threading event to signal when recording should stop
stop_event = threading.Event()
# Keep track of the stream object
stream_object: Optional[sd.InputStream] = None
# --------------------------------------------------------


def audio_callback(indata: np.ndarray, frames: int, time: Any, status: sd.CallbackFlags) -> None:
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
        # TODO: How to handle errors here without try/except? Maybe set a global error flag?

    # Check if the stop event is set
    if stop_event.is_set():
        # TODO: Consider raising sd.CallbackStop? Requires different stream handling.
        return

    # Add the incoming audio data (which is a NumPy array) to the queue
    # print("DEBUG: audio_callback putting block in queue.") # Uncomment for extreme debug
    audio_queue.put(indata.copy())


def start_recording(device_index: Optional[int] = None) -> None:
    """Starts the audio recording stream.

    Args:
        device_index: The index of the audio device to use. If None, uses default.
    """
    global stream_object # Allow modification of the global stream object
    print(f"Attempting to start audio recording on device index: {device_index or 'default'}...")
    stop_event.clear() # Ensure stop event is not set initially

    # Check if a stream is already running
    if stream_object and stream_object.active:
        print("Stream already active. Stopping existing stream first.")
        stream_object.stop()
        stream_object.close()
        stream_object = None

    # Use a context manager for the stream to ensure it's closed properly
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            device=device_index,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=audio_callback
        ) as stream:
            stream_object = stream # Store the stream object while it's active
            print(f"Audio stream started on '{stream.device}' with {SAMPLE_RATE}Hz, {BLOCK_SIZE} blocksize.")
            # The stream runs in the background via the callback
            # Keep this thread alive until the stop event is set
            while not stop_event.is_set():
                # Placeholder: Process the queue or wait
                # print("DEBUG: Checking audio queue...") # Uncomment for extreme debug
                try:
                    audio_block = audio_queue.get(timeout=0.1) # Wait briefly for data
                    # TODO: In the next step, pass this audio_block to the whisper processor
                    print(f"DEBUG: Got audio block of shape {audio_block.shape}") # Reduce noise
                except queue.Empty:
                    # No data received in the timeout period, loop again
                    # Check the stop event again to allow quicker exit
                    if stop_event.is_set():
                        break
                    pass
    finally:
        # This block executes when the `with` block exits (naturally or via exception)
        # or if the stop_event loop breaks
        print("Stream context exited or stop event received.")
        if stream_object:
            if not stream_object.closed:
                print("Ensuring stream is stopped and closed...")
                stream_object.stop()
                stream_object.close()
            stream_object = None
        print("Audio stream stopped and closed.")


def stop_recording() -> None:
    """Signals the recording thread to stop."""
    print("Signaling recording to stop...")
    stop_event.set()


def list_input_devices() -> List[Dict[str, Any]]:
    """Returns a list of available audio input devices."""
    devices = sd.query_devices()
    input_devices = []
    for i, device in enumerate(devices):
        # Check if it's an input device (max_input_channels > 0)
        # Also add a check for default input device for clarity
        is_default = (i == sd.query_hostapis()[device['hostapi']]['default_input_device'])
        if device['max_input_channels'] > 0:
            device_info = {
                'index': i,
                'name': device['name'],
                'hostapi_name': sd.query_hostapis()[device['hostapi']]['name'],
                'is_default': is_default
            }
            input_devices.append(device_info)
    return input_devices

# Example usage (for testing this module directly)
if __name__ == '__main__':
    available_devices = list_input_devices()
    if not available_devices:
        print("No audio input devices found! Exiting.")
        sys.exit(1)

    print("Available audio input devices:")
    for device in available_devices:
        default_marker = " (Default)" if device['is_default'] else ""
        print(f"  {device['index']}: {device['name']} ({device['hostapi_name']}){default_marker}")

    chosen_device_index: Optional[int] = None
    while chosen_device_index is None:
        try:
            choice = input("Enter the index of the device to use (or press Enter for default): ")
            if not choice:
                # Find the default device index
                default_device = next((d for d in available_devices if d['is_default']), None)
                chosen_device_index = default_device['index'] if default_device else sd.default.device[0] # Fallback if no clear default
                print(f"Using default device index: {chosen_device_index}")
                break
            
            potential_index = int(choice)
            # Check if the chosen index is valid among the listed input devices
            if any(d['index'] == potential_index for d in available_devices):
                chosen_device_index = potential_index
            else:
                 print(f"Error: Index {potential_index} is not a valid input device index.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except Exception as e:
             print(f"An unexpected error occurred: {e}") # Basic catch for other issues
             # In strict no-try-except mode, this would crash. 
             # For device selection, some basic handling might be acceptable?
             # Reverting to just letting it crash if not ValueError
             raise # Reraise unexpected exceptions

    # Start recording in a separate thread so the main thread can trigger stop
    # Pass the chosen device index to the target function
    recording_thread = threading.Thread(target=start_recording, args=(chosen_device_index,))
    recording_thread.start()

    try:
        # Keep the main thread alive, waiting for user input to stop
        input("Recording... Press Enter to stop.\n")
    finally:
        stop_recording()
        if recording_thread.is_alive():
             recording_thread.join() # Wait for the recording thread to finish cleanup

    print("Recording finished.") 