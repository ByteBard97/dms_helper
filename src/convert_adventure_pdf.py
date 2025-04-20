"""
Converts PDF adventure modules to Markdown using the Marker library.
"""

import logging
# Corrected imports based on user-provided snippet
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
import torch
from pathlib import Path
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Removed global model cache as the new pattern seems self-contained

def convert_pdf_to_markdown(pdf_path: str, output_dir: str):
    """
    Converts a single PDF file to Markdown using the marker library
    based on the PdfConverter pattern. Forces CUDA usage.

    Args:
        pdf_path (str): Path to the input PDF file.
        output_dir (str): Directory to save the output Markdown file.
                          (Note: Will save alongside input in source_materials as per user request)
    """
    pdf_filepath = Path(pdf_path)
    # Output directly alongside the input PDF
    output_path = pdf_filepath.parent

    # Input path checking
    if not pdf_filepath.is_file():
        logging.error(f"Input PDF not found: {pdf_path}")
        return # Skip this file

    # No need to check/create output_path if it's the source dir
    # if not output_path.is_dir():
    #     logging.info(f"Creating output directory: {output_dir}")
    #     output_path.mkdir(parents=True, exist_ok=True)

    output_filename = pdf_filepath.stem + ".md"
    full_output_path = output_path / output_filename

    # Optional: Check if Markdown file already exists and skip if desired
    # if full_output_path.exists():
    #     logging.warning(f"Output file already exists, skipping: {full_output_path}")
    #     return

    logging.info(f"Starting conversion for: {pdf_filepath.name} using PdfConverter")
    logging.info(f"Output will be saved to: {full_output_path}")

    start_time = time.time()

    # Force CUDA device
    device = "cuda"
    # logging.info(f"Attempting to use device: {device}") # Logged once in main now

    # Assert CUDA is available before proceeding (Checked once in main)
    # if not torch.cuda.is_available():
    #     error_message = "CUDA is not available, but script is configured to force CUDA usage. Please check PyTorch installation and GPU drivers."
    #     logging.error(error_message)
    #     raise RuntimeError(error_message)
    # logging.info("CUDA check passed.")

    # Instantiate the converter, loading models internally via create_model_dict
    # NOTE: This still loads models for EACH file. Consider optimizing later if slow.
    logging.info(f"Initializing PdfConverter (loading models to {device})...")
    model_load_start = time.time()
    converter = PdfConverter(
        # Explicitly pass the selected device to the model creation function
        artifact_dict=create_model_dict(device=device),
    )
    model_load_end = time.time()
    logging.info(f"Marker PdfConverter initialized in {model_load_end - model_load_start:.2f} seconds.")

    # Convert the PDF by calling the converter object
    logging.info("Calling converter object on PDF path...")
    convert_start = time.time()
    # Ensure the converter uses the specified device context if necessary (often handled internally)
    rendered = converter(str(pdf_filepath))
    convert_end = time.time()
    logging.info(f"Converter call finished in {convert_end - convert_start:.2f} seconds.")

    # Extract text from the rendered output
    logging.info("Extracting text from rendered output...")
    render_proc_start = time.time()
    text, _, _ = text_from_rendered(rendered) # Assuming we only need text
    render_proc_end = time.time()
    logging.info(f"Text extraction finished in {render_proc_end - render_proc_start:.2f} seconds.")
    logging.info(f"Conversion successful for: {pdf_filepath.name}")

    # Save the output
    logging.info("Saving markdown output...")
    save_start = time.time()
    with open(full_output_path, "w", encoding="utf-8") as f:
        f.write(text)
    save_end = time.time()
    logging.info(f"Markdown saved to: {full_output_path} in {save_end - save_start:.2f} seconds.")

    # Log total time outside of try block
    total_time = time.time() - start_time
    logging.info(f"Total processing time for {pdf_filepath.name}: {total_time:.2f} seconds.")


if __name__ == "__main__":
    # Directory containing the source PDF files
    SOURCE_DIR = Path("source_materials")

    if not SOURCE_DIR.is_dir():
        logging.error(f"Source directory not found: {SOURCE_DIR}")
    else:
        logging.info(f"Scanning for PDF files in: {SOURCE_DIR}")
        pdf_files = list(SOURCE_DIR.glob("*.pdf"))

        if not pdf_files:
            logging.warning(f"No PDF files found in {SOURCE_DIR}")
        else:
            logging.info(f"Found {len(pdf_files)} PDF file(s) to process.")

            # Check CUDA once before the loop
            if not torch.cuda.is_available():
                 error_message = "CUDA is not available, but script is configured to force CUDA usage. Cannot proceed."
                 logging.error(error_message)
                 # Exit script if CUDA is mandatory and not found
                 exit() # Or raise RuntimeError(error_message)
            else:
                logging.info("CUDA check passed. Proceeding with GPU.")

            # Process each PDF file
            for pdf_file in pdf_files:
                logging.info(f"\n--- Processing file: {pdf_file.name} ---")
                # Pass the directory of the PDF as the 'output_dir' argument
                convert_pdf_to_markdown(str(pdf_file), str(pdf_file.parent))
                logging.info(f"--- Finished processing: {pdf_file.name} ---")

    logging.info("Batch conversion script finished.") 