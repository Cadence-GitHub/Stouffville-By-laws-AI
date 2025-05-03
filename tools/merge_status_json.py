"""
merge_status_json.py

This script merges multiple `status.json` files from bylaw folders (e.g., 'By-laws 2020', 'By-laws 2021', etc.) into a single combined JSON file and produces a summary of bylaw statuses and modifications. It is designed to help consolidate and audit bylaw status data across multiple years or sources.

Features:
- Recursively finds all folders matching the pattern 'By-laws YYYY' under a root directory.
- Collects and merges all `status.json` files found in these folders.
- Handles JSON parsing errors gracefully, reporting the context of any issues.
- Tracks and summarizes the status and modification history of each bylaw.
- Outputs:
  - A combined JSON file with all bylaw references and bylaws without status.
  - A summary JSON file with the latest status and modification history for each bylaw.
  - An error log JSON file if any files could not be processed.
- Sorts bylaws and modification histories in chronological order for easy auditing.

Usage:
    python merge_status_json.py --root <root_dir> --output <combined_status.json> --summary <bylaw_status_summary.json> --error-log <processing_errors.json>

Arguments:
    --root       Root directory containing 'By-laws YYYY' folders (default: current directory)
    --output     Output file path for the combined JSON (default: combined_status.json)
    --summary    Output file path for the summary JSON (default: bylaw_status_summary.json)
    --error-log  Output file path for the error log (default: processing_errors.json)

Example:
    python merge_status_json.py --root ./bylaws --output combined_status.json --summary bylaw_status_summary.json --error-log processing_errors.json
"""
import os
import json
import re
import argparse
import traceback
from pathlib import Path
from collections import defaultdict, OrderedDict

def extract_year(folder_path):
    """
    Extract the year from a folder name like 'By-laws YYYY'.
    Returns the year as an integer, or 0 if not found.
    """
    folder_name = os.path.basename(folder_path)
    match = re.search(r'\d{4}', folder_name)
    if match:
        return int(match.group(0))
    return 0  # Default if no year found

def find_bylaw_folders(root_dir):
    """
    Find all folders matching the pattern 'By-laws YYYY' under the root directory.
    Returns a list of folder paths, sorted by year descending (newest first).
    """
    bylaw_folders = []
    # Walk through all directories and subdirectories
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirname = os.path.basename(dirpath)
        if re.match(r"By-laws\s+\d{4}", dirname, re.IGNORECASE):
            bylaw_folders.append(dirpath)
    # Sort folders by year in descending order (newest first)
    bylaw_folders.sort(key=extract_year, reverse=True)
    return bylaw_folders

def collect_status_files(bylaw_folders):
    """
    Collect all 'status.json' files from the given bylaw folders.
    Returns a list of file paths.
    """
    status_files = []
    for folder in bylaw_folders:
        status_path = os.path.join(folder, "status.json")
        if os.path.isfile(status_path):
            status_files.append(status_path)
        else:
            print(f"Warning: No status.json found in {folder}")
    return status_files

def show_json_error_context(file_path, line_no, column_no):
    """
    Print the JSON content around the error location for easier debugging.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Calculate the range of lines to show
        start_line = max(0, line_no - 3)
        end_line = min(len(lines), line_no + 2)
        print("\nJSON content around error:")
        for i in range(start_line, end_line):
            line = lines[i].rstrip()
            line_prefix = f"{'>' if i+1 == line_no else ' '} {i+1:4d}: "
            print(f"{line_prefix}{line}")
            if i+1 == line_no:
                # Point to the column where the error occurred
                print(" " * (len(line_prefix) + column_no) + "^")
    except Exception as e:
        print(f"Could not display JSON context: {e}")

def sort_key_for_bylaw(bylaw_str):
    """
    Create a sort key for bylaws to sort by year and then by numeric part.
    Handles both 'YYYY-XXX' and 'XX-XX' formats.
    Returns a tuple (year, number) for sorting.
    """
    # Try to match YYYY-XXX-XX format
    match = re.match(r'(\d{4})-(\d+)', bylaw_str)
    if match:
        year = int(match.group(1))
        num = int(match.group(2))
        return (year, num)
    # Try to match XX-XX format (assuming 19XX for century)
    match = re.match(r'(\d+)-(\d+)', bylaw_str)
    if match:
        year = int(match.group(1))
        if year < 100:  # Assume 1900s for two-digit years
            year += 1900
        num = int(match.group(2))
        return (year, num)
    # Default case - just return zeros for lexicographic sorting
    return (0, 0)

def merge_status_files(status_files, output_file, summary_file, error_log_file):
    """
    Merge all status.json files into one large JSON file and create a summary.
    Handles errors gracefully and logs them to an error log file.
    Produces three outputs:
      - output_file: Combined bylaw references and bylaws without status.
      - summary_file: Summary of bylaw statuses and modification history.
      - error_log_file: List of any errors encountered during processing.
    """
    combined_data = {
        "bylaw_references": [],
        "bylaws_without_status": []
    }
    # Dictionary to track bylaws and their status changes
    bylaw_summary = {}
    # List to track processing errors
    errors = []
    # Process each status file in chronological order (newest first)
    for file_path in status_files:
        folder_name = os.path.basename(os.path.dirname(file_path))
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Try to load the entire file
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    error_msg = f"ERROR in {file_path}: JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}"
                    print(error_msg)
                    show_json_error_context(file_path, e.lineno, e.colno)
                    errors.append({
                        "file": file_path,
                        "error": "JSON parse error",
                        "message": str(e),
                        "line": e.lineno,
                        "column": e.colno
                    })
                    continue  # Skip this file and continue with others
                references = data.get("bylaw_references", [])
                references_count = len(references)
                without_status_count = len(data.get("bylaws_without_status", []))
                # Process each bylaw reference
                for bylaw_ref in references:
                    # Add to combined data
                    combined_data["bylaw_references"].append(bylaw_ref)
                    # Extract filename without extension for the current bylaw
                    bylaw_filename = bylaw_ref["bylawfilename"]
                    bylaw_number = os.path.splitext(bylaw_filename)[0]
                    # Update the summary for this bylaw if it doesn't exist or has no status yet
                    if bylaw_number not in bylaw_summary or "status" not in bylaw_summary[bylaw_number]:
                        bylaw_summary[bylaw_number] = {
                            "status": bylaw_ref["status"],
                            "date": bylaw_ref.get("date"),
                            "dateType": bylaw_ref.get("dateType"),
                            "modifiedBy": []
                        }
                    # Process referenced bylaws to track status changes
                    for ref in bylaw_ref.get("referenced_bylaws", []):
                        ref_bylaw_number = ref["bylaw_number"]
                        ref_status = ref["status"]
                        # Create or update entry for the referenced bylaw
                        if ref_bylaw_number not in bylaw_summary:
                            bylaw_summary[ref_bylaw_number] = {
                                "status": ref_status,
                                "modifiedBy": []
                            }
                        # Add information about which bylaw modified this one
                        modifier_info = {
                            "bylaw": bylaw_number,
                            "status": ref_status
                        }
                        # Check if this modifier is already in the list
                        if not any(m["bylaw"] == bylaw_number for m in bylaw_summary[ref_bylaw_number]["modifiedBy"]):
                            bylaw_summary[ref_bylaw_number]["modifiedBy"].append(modifier_info)
                combined_data["bylaws_without_status"].extend(data.get("bylaws_without_status", []))
                print(f"Processed {folder_name}: {references_count} references, {without_status_count} without status")
        except Exception as e:
            error_msg = f"ERROR processing {file_path}: {type(e).__name__}: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            errors.append({
                "file": file_path,
                "error": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            })
    # Sort modifiedBy lists in reverse chronological order by bylaw number (newest first)
    for bylaw_num, bylaw_data in bylaw_summary.items():
        if "modifiedBy" in bylaw_data:
            bylaw_data["modifiedBy"].sort(
                key=lambda x: sort_key_for_bylaw(x["bylaw"]),
                reverse=True  # Reverse for newest first
            )
    # Sort the bylaw summary keys in chronological order (oldest first)
    sorted_bylaw_summary = OrderedDict()
    sorted_keys = sorted(bylaw_summary.keys(), key=sort_key_for_bylaw)
    for key in sorted_keys:
        sorted_bylaw_summary[key] = bylaw_summary[key]
    # Write the combined data to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2)
    # Write the sorted summary data to a separate file
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_bylaw_summary, f, indent=2)
    # Write the error log to a file
    if errors:
        with open(error_log_file, 'w', encoding='utf-8') as f:
            json.dump(errors, f, indent=2)
        print(f"WARNING: Encountered {len(errors)} errors during processing. See {error_log_file} for details.")
    total_references = len(combined_data["bylaw_references"])
    total_without_status = len(combined_data["bylaws_without_status"])
    total_bylaws = len(bylaw_summary)
    total_modified = sum(1 for bylaw in bylaw_summary.values() if bylaw.get("modifiedBy"))
    print(f"Successfully merged {len(status_files) - len(errors)} status files.")
    print(f"Total bylaw references: {total_references}")
    print(f"Total bylaws without status: {total_without_status}")
    print(f"Total unique bylaws in summary: {total_bylaws}")
    print(f"Total bylaws with status modifications: {total_modified}")

def main():
    """
    Main entry point: parses arguments, finds bylaw folders, collects status files, and merges them.
    """
    parser = argparse.ArgumentParser(description='Merge status.json files from bylaw folders')
    parser.add_argument('--root', default='.', help='Root directory containing By-laws folders')
    parser.add_argument('--output', default='combined_status.json', help='Output file path')
    parser.add_argument('--summary', default='bylaw_status_summary.json', help='Summary file path')
    parser.add_argument('--error-log', default='processing_errors.json', help='Error log file path')
    args = parser.parse_args()
    # Find all By-laws folders
    bylaw_folders = find_bylaw_folders(args.root)
    if not bylaw_folders:
        print("No By-laws folders found.")
        return
    # Collect status files from the folders
    status_files = collect_status_files(bylaw_folders)
    if not status_files:
        print("No status.json files found.")
        return
    # Merge the status files
    merge_status_files(status_files, args.output, args.summary, args.error_log)
    print(f"Combined status saved to {args.output}")
    print(f"Bylaw status summary saved to {args.summary}")

if __name__ == "__main__":
    main()
