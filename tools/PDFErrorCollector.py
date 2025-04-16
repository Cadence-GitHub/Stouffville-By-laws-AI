#!/usr/bin/env python3
"""
PDF Error Collector

This script recursively searches through a directory structure to find JSON error files
from the PDF extraction process and copies the corresponding PDF files to an output folder
for reprocessing.

It specifically searches for files with "-error.json" suffix, finds the matching PDF files,
and copies them to the specified output directory.

Usage:
    python PDFErrorCollector.py --input source_directory --output destination_directory
"""

import argparse
import os
import glob
import shutil
import logging
from pathlib import Path

def setup_logging(debug=False):
    """
    Configure logging to console with optional debug output
    
    Args:
        debug (bool): Enable debug logging if True
        
    Returns:
        logging.Logger: Configured logger object
    """
    level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def find_error_files(input_dir):
    """
    Recursively find all files with "-error.json" suffix in the input directory.
    
    Args:
        input_dir (str): Directory to search for error files
        
    Returns:
        list: Paths to all error JSON files found
    """
    error_files = []
    for root, _, _ in os.walk(input_dir):
        # Find all files with -error.json suffix in this directory
        for error_file in glob.glob(os.path.join(root, "*-error.json")):
            error_files.append(error_file)
    
    return error_files

def find_pdf_file(error_file_path, input_dir):
    """
    Find the corresponding PDF file for an error JSON file.
    First checks in the same directory as the error file, then
    searches through the entire directory tree for a matching PDF.
    
    Args:
        error_file_path (str): Path to the error JSON file
        input_dir (str): Root directory to search for PDF files
        
    Returns:
        str or None: Path to matching PDF file or None if not found
    """
    logger = logging.getLogger(__name__)
    
    # Extract base name from the error file (remove the -error.json suffix)
    error_file_name = os.path.basename(error_file_path)
    base_name = error_file_name.replace("-error.json", "")
    error_dir = os.path.dirname(error_file_path)
    
    # First check in the same directory as the error file
    for pdf_ext in ['.pdf', '.PDF']:
        potential_pdf_path = os.path.join(error_dir, f"{base_name}{pdf_ext}")
        if os.path.exists(potential_pdf_path):
            logger.debug(f"Found PDF in same directory: {potential_pdf_path}")
            return potential_pdf_path
    
    # If not found in same directory, search the entire directory tree
    logger.debug(f"Searching for PDF matching '{base_name}' in entire directory tree")
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_base, file_ext = os.path.splitext(file)
            if file_ext.lower() == '.pdf' and file_base == base_name:
                logger.debug(f"Found matching PDF: {os.path.join(root, file)}")
                return os.path.join(root, file)
    
    logger.debug(f"No matching PDF found for base name: {base_name}")
    return None

def collect_error_pdfs(input_dir, output_dir):
    """
    Find all error JSON files and copy their corresponding PDFs to the output directory.
    
    Args:
        input_dir (str): Directory to search for error files
        output_dir (str): Directory to copy matching PDF files to
        
    Returns:
        tuple: (found_count, copied_count) - number of error files found and PDFs copied
    """
    logger = logging.getLogger(__name__)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all error JSON files
    error_files = find_error_files(input_dir)
    logger.info(f"Found {len(error_files)} error JSON files")
    
    # Process each error file
    copied_count = 0
    not_found_pdfs = []
    
    for error_file in error_files:
        # Find corresponding PDF
        base_name = os.path.basename(error_file).replace("-error.json", "")
        pdf_path = find_pdf_file(error_file, input_dir)
        
        if pdf_path:
            # Copy PDF to output directory
            pdf_filename = os.path.basename(pdf_path)
            destination = os.path.join(output_dir, pdf_filename)
            
            # Check if file already exists in destination
            if os.path.exists(destination):
                logger.warning(f"File already exists in destination: {pdf_filename}")
            else:
                try:
                    shutil.copy2(pdf_path, destination)
                    logger.info(f"Copied: {pdf_filename}")
                    copied_count += 1
                except (shutil.Error, IOError) as e:
                    logger.error(f"Error copying {pdf_filename}: {str(e)}")
        else:
            # No matching PDF found
            not_found_pdfs.append(base_name)
            logger.warning(f"Could not find PDF file for: {base_name}")
            
            # Try a more flexible search as a fallback
            potential_matches = []
            for root, _, files in os.walk(input_dir):
                for file in files:
                    file_lower = file.lower()
                    if (file_lower.endswith('.pdf') and 
                        base_name.lower() in file_lower and
                        "-error.json" not in file_lower):
                        potential_matches.append(os.path.join(root, file))
            
            if potential_matches:
                logger.debug(f"Potential matches for {base_name}: {[os.path.basename(m) for m in potential_matches]}")
                        
    # Log summary
    if not_found_pdfs:
        logger.warning(f"Could not find {len(not_found_pdfs)} PDF files: {', '.join(not_found_pdfs)}")
    
    return len(error_files), copied_count

def main():
    """Main entry point for the script"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Copy PDF files with error JSON files to an output folder")
    parser.add_argument("--input", "-i", required=True, help="Input directory to search for error files")
    parser.add_argument("--output", "-o", required=True, help="Output directory to copy PDFs to")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.debug)
    
    logger.info(f"Starting PDF error collector")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")
    
    # Collect error PDFs
    found_count, copied_count = collect_error_pdfs(args.input, args.output)
    
    # Report results
    logger.info(f"Process complete. Found {found_count} error files, copied {copied_count} PDFs.")
    
    return 0 if copied_count > 0 else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
