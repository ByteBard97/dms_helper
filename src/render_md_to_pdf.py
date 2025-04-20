"""
Converts a Markdown file to PDF using Pandoc (via pypandoc) for comparison.

Requires 'pypandoc' library (install with 'pip install pypandoc')
and a working Pandoc installation with a LaTeX engine (like MiKTeX or TeX Live).
NOTE: Using options like 'mainfont' requires XeLaTeX or LuaLaTeX engines.
MiKTeX might need to install additional packages for these engines and fonts.
"""

import logging
import pypandoc
import argparse
from pathlib import Path
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def render_markdown_to_pdf(md_input_path: str, pdf_output_path: str):
    """
    Converts the specified Markdown file to PDF using Pandoc.
    Attempts a more 'book-like' style using XeLaTeX and Georgia font.

    Args:
        md_input_path (str): Path to the input Markdown file.
        pdf_output_path (str): Path to save the output PDF file.
    """
    md_filepath = Path(md_input_path)
    pdf_filepath = Path(pdf_output_path)

    if not md_filepath.is_file():
        logging.error(f"Input Markdown file not found: {md_input_path}")
        return

    # Ensure output directory exists (which is the same as the input directory)
    pdf_filepath.parent.mkdir(parents=True, exist_ok=True)

    logging.info(f"Attempting conversion: {md_filepath.name} -> {pdf_filepath.name}")
    start_time = time.time()

    # Note: No try block as per rules. Errors will propagate.
    # Using XeLaTeX engine to allow system fonts.
    # Setting Georgia font and 1-inch margins.
    extra_args = [
        '--pdf-engine=xelatex',
        '-V', 'mainfont=Georgia',
        '-V', 'geometry:margin=1in',
        # '-V', 'fontsize=11pt', # Optional: uncomment to change base font size
    ]
    logging.info(f"Using Pandoc extra arguments: {extra_args}")

    pypandoc.convert_file(
        str(md_filepath),
        to='pdf',
        outputfile=str(pdf_filepath),
        extra_args=extra_args
    )

    end_time = time.time()
    logging.info(f"Conversion successful in {end_time - start_time:.2f} seconds.")
    logging.info(f"Output saved to: {pdf_filepath}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a Markdown file to PDF using Pandoc.")
    parser.add_argument("input_md", help="Path to the input Markdown file.")
    parser.add_argument("-o", "--output", help="Path for the output PDF file. Defaults to input filename with _from_md.pdf suffix in the same directory as the input.")

    args = parser.parse_args()
    input_path = Path(args.input_md)

    # Determine default output path if not specified
    if args.output:
        output_pdf = args.output
    else:
        # Default output is alongside the input file
        output_pdf = input_path.parent / (input_path.stem + "_from_md.pdf")

    render_markdown_to_pdf(args.input_md, str(output_pdf))

    logging.info("Rendering script finished.") 