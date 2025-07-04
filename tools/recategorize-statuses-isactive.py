#!/usr/bin/env python3
"""
recategorize-statuses-isactive.py

This script processes a JSON file containing bylaw reference information, categorizes
the status of each referenced bylaw as active, inactive, or undetermined (NA), and
generates a searchable, sortable HTML report. The script uses regular expressions to
determine the `isActive` status based on keywords in the status string.

Features:
- Status categorization using robust regular expressions
- Batch processing of all referenced bylaws
- HTML reporting with searching, sorting, and filtering capabilities
- Comprehensive logging for transparency and debugging
- Configurable file paths and log locations
"""

import os
import json
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path

def determine_is_active(status_string):
    """
    Determine if a bylaw is active based on its status string.
    
    Args:
        status_string: The status string to analyze
        
    Returns:
        str: 'True' for active, 'False' for inactive, 'NA' for undetermined
    """
    if not status_string:
        return 'NA'
    
    status_lower = status_string.lower()
    
    # Patterns for inactive statuses (prioritized)
    inactive_patterns = [
        r'\bwithdrawn\b',
        r'\bcancelled?\b',
        r'\brepealed?\b',
        r'\bspent\b',
        r'\bexpired?\b',
        r'\bdeleted?\b',
        r'\bdefeated?\b',
        r'\bdid\s+not\s+pass\b',
        r'\bnot\s+assigned\b',
        r'\bnot\s+used\b',
        r'\bterminated\b',
        r'\bvoid\b',
        r'\bnullified\b',
        r'\brescinded\b',
        r'\babolished\b',
        r'\bdiscontinued\b',
        r'\bdiscontinued\b',
        r'\bsuperseded\b',
        r'\breplaced\b'
    ]
    
    # Patterns for active statuses
    active_patterns = [
        r'\bin\s*force\b',
        r'\bactive\b',
        r'\bcurrent\b',
        r'\bvalid\b',
        r'\beffective\b',
        r'\boperative\b',
        r'\benacted\b',
        r'\bpassed\b',
        r'\badopted\b',
        r'\bapproved\b',
        r'\bimplemented\b',
        r'\bexecuted\b'
    ]
    
    # Check for inactive patterns first (higher priority)
    for pattern in inactive_patterns:
        if re.search(pattern, status_lower):
            return 'False'
    
    # Check for active patterns
    for pattern in active_patterns:
        if re.search(pattern, status_lower):
            return 'True'
    
    # If no clear pattern is found, return NA
    return 'NA'

def process_bylaw_references(input_file, logger):
    """
    Process bylaw references and categorize their active status.
    
    Args:
        input_file: Path to input JSON file
        logger: Logger instance
        
    Returns:
        List of processed bylaw references with isActive status
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {input_file}: {e}")
        return []
    
    processed_bylaws = []
    
    # Process main bylaw references
    for bylaw_ref in data.get("bylaw_references", []):
        main_bylaw = {
            "bylaw_number": bylaw_ref.get("bylawfilename", "").replace(".json", ""),
            "original_status": bylaw_ref.get("status", ""),
            "is_active": determine_is_active(bylaw_ref.get("status", "")),
            "context": "main_bylaw",
            "source_file": bylaw_ref.get("bylawfilename", "")
        }
        processed_bylaws.append(main_bylaw)
        
        # Process referenced bylaws
        for ref in bylaw_ref.get("referenced_bylaws", []):
            ref_bylaw = {
                "bylaw_number": ref.get("bylaw_number", ""),
                "original_status": ref.get("status", ""),
                "is_active": determine_is_active(ref.get("status", "")),
                "context": "referenced_bylaw",
                "source_file": bylaw_ref.get("bylawfilename", "")
            }
            processed_bylaws.append(ref_bylaw)
    
    # Process bylaws without status
    for bylaw in data.get("bylaws_without_status", []):
        no_status_bylaw = {
            "bylaw_number": bylaw.get("bylaw_number", ""),
            "original_status": bylaw.get("status", ""),
            "is_active": determine_is_active(bylaw.get("status", "")),
            "context": "no_status",
            "source_file": "N/A"
        }
        processed_bylaws.append(no_status_bylaw)
    
    logger.info(f"Processed {len(processed_bylaws)} bylaw references")
    return processed_bylaws

def generate_html_report(processed_bylaws, output_file, logger):
    """
    Generate HTML report with searchable, sortable table.
    
    Args:
        processed_bylaws: List of processed bylaw references
        output_file: Path to output HTML file
        logger: Logger instance
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Count statistics
    total_count = len(processed_bylaws)
    active_count = sum(1 for bylaw in processed_bylaws if bylaw["is_active"] == "True")
    inactive_count = sum(1 for bylaw in processed_bylaws if bylaw["is_active"] == "False")
    na_count = sum(1 for bylaw in processed_bylaws if bylaw["is_active"] == "NA")
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bylaw Status Categorization Report</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.2.2/css/buttons.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.2.2/js/dataTables.buttons.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.1.3/jszip.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.2.2/js/buttons.html5.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.2.2/js/buttons.print.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .summary-item {{ background: white; padding: 10px; border-radius: 5px; text-align: center; }}
        .summary-item h3 {{ margin: 0; color: #2c3e50; }}
        .summary-item p {{ margin: 5px 0 0 0; font-size: 1.2em; font-weight: bold; }}
        .active {{ color: #27ae60; }}
        .inactive {{ color: #e74c3c; }}
        .na {{ color: #f39c12; }}
        table.dataTable {{ width: 100%; border-collapse: collapse; }}
        table.dataTable th, table.dataTable td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        table.dataTable th {{ background-color: #f2f2f2; }}
        .controls {{ margin: 15px 0; }}
    </style>
</head>
<body>
    <h1>Bylaw Status Categorization Report</h1>
    
    <div class="summary">
        <h3>Summary</h3>
        <p>Generated at: <strong>{now}</strong></p>
        <div class="summary-grid">
            <div class="summary-item">
                <h3>Total Bylaws</h3>
                <p>{total_count}</p>
            </div>
            <div class="summary-item">
                <h3>Active</h3>
                <p class="active">{active_count}</p>
            </div>
            <div class="summary-item">
                <h3>Inactive</h3>
                <p class="inactive">{inactive_count}</p>
            </div>
            <div class="summary-item">
                <h3>Undetermined</h3>
                <p class="na">{na_count}</p>
            </div>
        </div>
    </div>

    <table id="bylawTable" class="display" style="width:100%">
        <thead>
            <tr>
                <th>Bylaw Number</th>
                <th>Original Status</th>
                <th>Is Active</th>
                <th>Context</th>
                <th>Source File</th>
            </tr>
        </thead>
        <tbody>
'''
    
    for bylaw in processed_bylaws:
        is_active_class = bylaw["is_active"].lower()
        html += f'<tr>' \
                f'<td>{bylaw["bylaw_number"]}</td>' \
                f'<td>{bylaw["original_status"]}</td>' \
                f'<td class="{is_active_class}">{bylaw["is_active"]}</td>' \
                f'<td>{bylaw["context"]}</td>' \
                f'<td>{bylaw["source_file"]}</td>' \
                f'</tr>'
    
    html += '''        </tbody>
    </table>

    <script>
        $(document).ready(function() {
            $('#bylawTable').DataTable({
                dom: 'Bfrtip',
                buttons: [
                    'copy', 'csv', 'excel', 'print'
                ],
                pageLength: 25,
                lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
                order: [[0, 'asc']]
            });
        });
    </script>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"Generated HTML report: {output_file}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Categorize bylaw statuses as active/inactive and generate HTML report'
    )
    parser.add_argument('--input', default='combined_status.json',
                       help='Input JSON file (default: combined_status.json)')
    parser.add_argument('--output', default='bylaw_statuses_report.html',
                       help='Output HTML report file (default: bylaw_statuses_report.html)')
    parser.add_argument('--log-file', default='recategorize_statuses.log',
                       help='Log file path (default: recategorize_statuses.log)')
    
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
    logger = logging.getLogger('RecategorizeStatuses')
    
    logger.info(f"Starting status categorization. Input: {args.input}, Output: {args.output}")
    
    # Check if input file exists
    if not os.path.exists(args.input):
        logger.error(f"Input file {args.input} does not exist")
        return 1
    
    # Process bylaw references
    processed_bylaws = process_bylaw_references(args.input, logger)
    
    if not processed_bylaws:
        logger.warning("No bylaw references found to process")
        return 1
    
    # Generate HTML report
    generate_html_report(processed_bylaws, args.output, logger)
    
    # Print summary
    total_count = len(processed_bylaws)
    active_count = sum(1 for bylaw in processed_bylaws if bylaw["is_active"] == "True")
    inactive_count = sum(1 for bylaw in processed_bylaws if bylaw["is_active"] == "False")
    na_count = sum(1 for bylaw in processed_bylaws if bylaw["is_active"] == "NA")
    
    print(f"\nStatus Categorization Summary:")
    print(f"  Total bylaws processed: {total_count}")
    print(f"  Active: {active_count}")
    print(f"  Inactive: {inactive_count}")
    print(f"  Undetermined: {na_count}")
    print(f"  Report saved to: {args.output}")
    
    return 0

if __name__ == "__main__":
    exit(main()) 