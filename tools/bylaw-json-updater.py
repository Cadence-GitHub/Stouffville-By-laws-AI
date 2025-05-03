#!/usr/bin/env python3
"""
Bylaw JSON Updater

This script spiders through a directory, updates each JSON file's bylawNumber to the expected format (as per modified-json-checker.py), adds a bylawFileName field, supports a --dry-run flag (default True), logs all actions, and produces an HTML report. Reuses logic from modified-json-checker.py for filename parsing and expected number generation.

Features:
- Recursively searches a directory for JSON files.
- Updates the 'bylawNumber' field in each JSON file to a standardized format based on the filename.
- Adds a 'bylawFileName' field to each JSON file.
- Supports a dry-run mode (default) that does not write changes to disk unless --no-dry-run is specified.
- Logs all actions to both a file and the console.
- Generates an HTML report summarizing the results of the operation.
- Reuses filename parsing logic from modified-json-checker.py for consistency.

Usage:
    python bylaw-json-updater.py [directory] [--dry-run|--no-dry-run]

Arguments:
    directory   Directory to search for JSON files (default: current directory)
    --dry-run   Perform a dry run (default: True)
    --no-dry-run Actually write changes to files

Example:
    python bylaw-json-updater.py ./bylaws --no-dry-run
"""
import os
import json
import argparse
import logging
from datetime import datetime

# --- Begin: Copied logic from modified-json-checker.py ---
import re

def extract_filename_info(filename):
    """
    Extracts year, number, combined year-number, and optional suffix from a bylaw filename.
    Handles various filename formats, including consolidated and legacy formats.

    Args:
        filename (str): The filename to parse (not the full path).

    Returns:
        tuple: (year, number, combined, suffix)
            - year (str): The four-digit year.
            - number (str): The zero-padded bylaw number.
            - combined (str): The combined year-number string (e.g., '2023-001').
            - suffix (str): Any suffix present (e.g., 'A').
    """
    base_filename = os.path.splitext(os.path.basename(filename))[0]
    # Remove ' Consolidated ' if present
    if " Consolidated " in base_filename:
        base_filename = base_filename.split(" Consolidated ")[0]
    # Match formats with suffix (e.g., 2023-001A)
    suffix_match = re.match(r'((?:19|20)\d{2})-(\d+)([A-Z])(?:\s*-\s*[A-Z]{2})?', base_filename)
    if suffix_match:
        year = suffix_match.group(1)
        number = suffix_match.group(2).zfill(3)
        suffix = suffix_match.group(3)
        return year, number, f"{year}-{number}", suffix
    # Match modern format (e.g., 2023-001)
    modern_match = re.match(r'((?:19|20)\d{2})\s*-\s*(\d+)(?:\s*-\s*[A-Z]{2})?', base_filename)
    if modern_match:
        year = modern_match.group(1)
        number = modern_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""
    # Match format with spaces (e.g., 2023 - 1)
    space_match = re.match(r'(\d{4})\s*-\s*(\d+)', base_filename)
    if space_match:
        year = space_match.group(1)
        number = space_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""
    # Match year-space format (redundant, but included for completeness)
    year_space_match = re.match(r'(\d{4})\s*-\s*(\d+)', base_filename)
    if year_space_match:
        year = year_space_match.group(1)
        number = year_space_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""
    # Match old format (e.g., 85-12)
    old_match = re.match(r'(\d{2})-(\d+)', base_filename)
    if old_match:
        year_prefix = "19"
        year = f"{year_prefix}{old_match.group(1)}"
        number = old_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""
    # Alternate old format (redundant, but included for completeness)
    alternate_match = re.match(r'(\d{2})-(\d+)', base_filename)
    if alternate_match:
        year = f"19{alternate_match.group(1)}"
        number = alternate_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""
    # If no match, return empty strings
    return "", "", "", ""
# --- End: Copied logic ---

def get_expected_json_number(filename):
    """
    Returns the expected bylawNumber for a given filename, including suffix if present.

    Args:
        filename (str): The filename to parse.

    Returns:
        str: The expected bylawNumber (e.g., '2023-001A' or '2023-001').
    """
    year, number, combined, suffix = extract_filename_info(filename)
    if suffix:
        return combined + suffix
    return combined

def update_json_file(filepath, dry_run, logger):
    """
    Updates a single JSON file's bylawNumber and adds bylawFileName.
    Optionally writes changes to disk unless dry_run is True.
    Logs the operation and returns a result dict for reporting.

    Args:
        filepath (str): Path to the JSON file.
        dry_run (bool): If True, do not write changes to disk.
        logger (logging.Logger): Logger for logging actions.

    Returns:
        dict: Result information for reporting (filename, old/new bylawNumber, status, error).
    """
    filename = os.path.basename(filepath)
    expected_json_number = get_expected_json_number(filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        old_bylaw_number = data.get('bylawNumber', None)
        # Update fields
        data['bylawNumber'] = expected_json_number
        data['bylawFileName'] = filename
        if not dry_run:
            # Write changes back to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Processed: {filepath} | old bylawNumber: {old_bylaw_number} -> new: {expected_json_number}")
        return {'Filepath': filepath, 'Filename': filename, 'Old_BylawNumber': old_bylaw_number, 'New_BylawNumber': expected_json_number, 'Status': 'Success', 'Error': ''}
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return {'Filepath': filepath, 'Filename': filename, 'Old_BylawNumber': '', 'New_BylawNumber': '', 'Status': 'Error', 'Error': str(e)}

def spider_and_update(root_dir, dry_run, logger):
    """
    Recursively walks through root_dir, updating all JSON files found.
    Calls update_json_file for each JSON file and collects results.

    Args:
        root_dir (str): Root directory to start the search.
        dry_run (bool): If True, do not write changes to disk.
        logger (logging.Logger): Logger for logging actions.

    Returns:
        list: List of result dicts for each file processed.
    """
    results = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.json'):
                filepath = os.path.join(root, file)
                result = update_json_file(filepath, dry_run, logger)
                results.append(result)
    return results

def generate_html_report(results, output_file, dry_run):
    """
    Generates an HTML report summarizing the results of the update operation.

    Args:
        results (list): List of result dicts from spider_and_update.
        output_file (str): Path to write the HTML report to.
        dry_run (bool): Whether the run was a dry run (affects report header).
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bylaw JSON Updater Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .success {{ color: green; font-weight: bold; }}
        .error {{ color: red; }}
    </style>
</head>
<body>
    <h1>Bylaw JSON Updater Report</h1>
    <div class="summary">
        <h3>Summary</h3>
        <p>Run at: <strong>{now}</strong></p>
        <p>Mode: <strong>{'Dry Run' if dry_run else 'Write Mode'}</strong></p>
        <p>Total files processed: <strong>{len(results)}</strong></p>
        <p>Success: <strong>{sum(1 for r in results if r['Status']=='Success')}</strong></p>
        <p>Errors: <strong>{sum(1 for r in results if r['Status']=='Error')}</strong></p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Filename</th>
                <th>Old bylawNumber</th>
                <th>New bylawNumber</th>
                <th>Status</th>
                <th>Error</th>
            </tr>
        </thead>
        <tbody>
'''
    for r in results:
        status_class = 'success' if r['Status'] == 'Success' else 'error'
        html += f'<tr>' \
                f'<td>{r["Filename"]}</td>' \
                f'<td>{r["Old_BylawNumber"]}</td>' \
                f'<td>{r["New_BylawNumber"]}</td>' \
                f'<td class="{status_class}">{r["Status"]}</td>' \
                f'<td>{r["Error"]}</td>' \
                f'</tr>'
    html += '''        </tbody>
    </table>
</body>
</html>'''
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

def main():
    """
    Main entry point for the script. Parses arguments, sets up logging, runs the update process, and generates the HTML report.
    """
    parser = argparse.ArgumentParser(description='Update bylawNumber and add bylawFileName in JSON files.')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to search for JSON files (default: current directory)')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Dry run (default: True). Use --no-dry-run to actually write changes.')
    parser.add_argument('--no-dry-run', dest='dry_run', action='store_false', help='Actually write changes to files.')
    parser.set_defaults(dry_run=True)
    args = parser.parse_args()

    log_file = 'json_spider.log'
    # Set up logging to both file and console
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
    logger = logging.getLogger('BylawJSONUpdater')

    logger.info(f"Starting bylaw JSON updater. Directory: {args.directory}, Dry run: {args.dry_run}")
    # Process all JSON files and collect results
    results = spider_and_update(args.directory, args.dry_run, logger)
    html_report = 'bylaw_json_update_report.html'
    # Generate HTML report
    generate_html_report(results, html_report, args.dry_run)
    logger.info(f"HTML report written to {html_report}")

if __name__ == "__main__":
    main() 