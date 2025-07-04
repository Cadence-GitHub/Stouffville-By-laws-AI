#!/usr/bin/env python3
"""
normalize_combined_status.py

This script normalizes the `bylaw_number` fields within the `referenced_bylaws` entries
of a `combined_status.json` file. It ensures that all referenced bylaw numbers follow
a canonical format, using the same normalization logic as other bylaw tools in the project.

Features:
- Targeted normalization of bylaw_number fields in referenced_bylaws
- Consistent logic with bylaw-json-updater.py for filename parsing
- Dry-run support (default) with --no-dry-run to apply changes
- Comprehensive logging to both file and console
- HTML report generation with detailed change summary
"""

import os
import json
import argparse
import logging
import re
from datetime import datetime
from pathlib import Path

def extract_filename_info(filename):
    """
    Extract year, number, combined, and suffix from a bylaw filename.
    Copied from bylaw-json-updater.py for consistency.
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
    
    # Match old format (e.g., 85-12)
    old_match = re.match(r'(\d{2})-(\d+)', base_filename)
    if old_match:
        year_prefix = "19"
        year = f"{year_prefix}{old_match.group(1)}"
        number = old_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""
    
    # If no match, return empty strings
    return "", "", "", ""

def get_expected_json_number(filename):
    """Get expected bylaw number for a filename"""
    year, number, combined, suffix = extract_filename_info(filename)
    if suffix:
        return combined + suffix
    return combined

def normalize_combined_status(input_file, output_file, dry_run, logger):
    """
    Normalize bylaw numbers in the combined status file.
    
    Args:
        input_file: Path to input combined_status.json
        output_file: Path to output normalized file
        dry_run: If True, don't write changes
        logger: Logger instance
    
    Returns:
        List of changes made (or that would be made)
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {input_file}: {e}")
        return []
    
    changes = []
    normalized_count = 0
    
    # Process bylaw references
    for bylaw_ref in data.get("bylaw_references", []):
        for ref in bylaw_ref.get("referenced_bylaws", []):
            original_number = ref.get("bylaw_number", "")
            if original_number:
                # Extract expected number from the original
                year, number, combined, suffix = extract_filename_info(original_number)
                expected_number = combined + suffix if suffix else combined
                
                if expected_number and expected_number != original_number:
                    change_info = {
                        "context": f"bylaw_references -> {bylaw_ref.get('bylawfilename', 'unknown')}",
                        "original": original_number,
                        "normalized": expected_number
                    }
                    changes.append(change_info)
                    
                    if not dry_run:
                        ref["bylaw_number"] = expected_number
                    
                    normalized_count += 1
                    logger.info(f"Normalized: {original_number} -> {expected_number}")
    
    # Save normalized data if not dry run
    if not dry_run:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved normalized data to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save {output_file}: {e}")
    
    return changes

def generate_html_report(changes, output_file, dry_run):
    """
    Generate HTML report for normalization results.
    
    Args:
        changes: List of changes made
        output_file: Path to output HTML file
        dry_run: Whether this was a dry run
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bylaw Number Normalization Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Bylaw Number Normalization Report</h1>
    <div class="summary">
        <h3>Summary</h3>
        <p>Run at: <strong>{now}</strong></p>
        <p>Mode: <strong>{'Dry Run' if dry_run else 'Write Mode'}</strong></p>
        <p>Total changes: <strong>{len(changes)}</strong></p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Context</th>
                <th>Original Number</th>
                <th>Normalized Number</th>
            </tr>
        </thead>
        <tbody>
'''
    
    for change in changes:
        html += f'<tr>' \
                f'<td>{change["context"]}</td>' \
                f'<td>{change["original"]}</td>' \
                f'<td>{change["normalized"]}</td>' \
                f'</tr>'
    
    html += '''        </tbody>
    </table>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Normalize bylaw numbers in combined_status.json file'
    )
    parser.add_argument('--input', default='combined_status.json',
                       help='Input combined_status.json file (default: combined_status.json)')
    parser.add_argument('--output', default='combined_status.normalized.json',
                       help='Output normalized file (default: combined_status.normalized.json)')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Dry run (default: True). Use --no-dry-run to apply changes.')
    parser.add_argument('--no-dry-run', dest='dry_run', action='store_false',
                       help='Actually write changes to files.')
    parser.add_argument('--log-file', default='normalize_combined_status.log',
                       help='Log file path (default: normalize_combined_status.log)')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(args.log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger('NormalizeCombinedStatus')
    
    logger.info(f"Starting normalization. Input: {args.input}, Output: {args.output}, Dry run: {args.dry_run}")
    
    # Check if input file exists
    if not os.path.exists(args.input):
        logger.error(f"Input file {args.input} does not exist")
        return 1
    
    # Perform normalization
    changes = normalize_combined_status(args.input, args.output, args.dry_run, logger)
    
    # Generate HTML report
    html_report = 'normalize_combined_status_report.html'
    generate_html_report(changes, html_report, args.dry_run)
    
    logger.info(f"Normalization complete. {len(changes)} changes {'would be made' if args.dry_run else 'made'}")
    logger.info(f"HTML report written to {html_report}")
    
    return 0

if __name__ == "__main__":
    exit(main()) 