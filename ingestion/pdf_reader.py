import os
import time
import pymupdf4llm

from utils.timing import print_timing
from utils.logger import logger

from config.config import (
    FILES_INPUT_FOLDER, 
    FILES_OUTPUT_FOLDER
    )


def convert_pdf_to_md(pdf_path, md_path):
    """
    Converts a single PDF to Markdown using PyMuPDF4LLM and saves it to disk.
    Returns the extracted markdown string.
    """
    # Convert the PDF to Markdown format
    md_text = pymupdf4llm.to_markdown(pdf_path)
    
    # Save the markdown text to the specified file path
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
        
    return md_text

def read_pdfs(files):
    start = time.perf_counter()
    documents = []

    # # Create the md_files folder inside the data_folder
    # md_folder = os.path.join(data_folder, "md_files")
    # os.makedirs(md_folder, exist_ok=True)

    for filename in files:
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(FILES_INPUT_FOLDER, filename)
        
        # Create the markdown filename by replacing the .pdf extension
        md_filename = f"{os.path.splitext(filename)[0]}.md"
        md_path = os.path.join(FILES_OUTPUT_FOLDER, md_filename)

        # Perform the conversion using the separate function
        md_text = convert_pdf_to_md(pdf_path, md_path)

        if md_text.strip():
            documents.append({
                "text": md_text,
                "source": md_filename # Updating source to reflect the markdown file
            })

            logger.info(f"Loaded PDF: {filename} and saved as {md_filename}")

    # Add this summary print:
    print(f"Successfully processed {len(documents)} PDF file(s).")

    print_timing(
        "read_pdfs()",
        "Read PDF documents and converted to Markdown",
        start
    )


    return documents