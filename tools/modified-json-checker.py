#!/usr/bin/env python3
"""
Bylaw Validator

This script validates bylaw JSON files by comparing information extracted from the filename with the content of the JSON file. The filename is treated as the source of truth for the bylaw's year and number. The script supports a variety of filename formats, including those with suffixes and consolidated files. It produces both CSV and interactive HTML reports summarizing the validation results.

Features:
- Recursively searches a directory for JSON files.
- Extracts year, number, and suffix from filenames using robust regex patterns.
- Compares extracted filename data with the 'bylawNumber' and 'bylawYear' fields in each JSON file.
- Flexible normalization and comparison logic to handle legacy and modern formats.
- Outputs a CSV file and an interactive HTML report with summary statistics and per-file validation results.

Usage:
    python modified-json-checker.py [directory]

Arguments:
    directory   Directory to search for JSON files (default: current directory)

Example:
    python modified-json-checker.py ./bylaws
"""
import os
import json
import csv
import re
import sys
import argparse

def extract_filename_info(filename):
    """
    Extract year, number, and suffix from a bylaw filename.
    Handles various filename patterns, including consolidated and legacy formats.

    Args:
        filename (str): The filename to parse (not the full path).

    Returns:
        tuple: (year, number, combined, suffix)
            - year (str): The four-digit year (or empty string if not found).
            - number (str): The zero-padded bylaw number (or empty string).
            - combined (str): The combined year-number string (e.g., '2023-001').
            - suffix (str): Any suffix present (e.g., 'A').
    """
    base_filename = os.path.splitext(os.path.basename(filename))[0]

    # Handle consolidated files (keep only the bylaw part)
    if " Consolidated " in base_filename:
        base_filename = base_filename.split(" Consolidated ")[0]

    # Modern format with alphabetical suffix: YYYY-NNNA
    suffix_match = re.match(r'((?:19|20)\d{2})-(\d+)([A-Z])(?:\s*-\s*[A-Z]{2})?', base_filename)
    if suffix_match:
        year = suffix_match.group(1)
        number = suffix_match.group(2).zfill(3)
        suffix = suffix_match.group(3)
        return year, number, f"{year}-{number}", suffix

    # Modern format with or without spaces: YYYY-NNN-XX or YYYY - NNN-XX
    modern_match = re.match(r'((?:19|20)\d{2})\s*-\s*(\d+)(?:\s*-\s*[A-Z]{2})?', base_filename)
    if modern_match:
        year = modern_match.group(1)
        number = modern_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""

    # Format with spaces: YYYY - NNN
    space_match = re.match(r'(\d{4})\s*-\s*(\d+)', base_filename)
    if space_match:
        year = space_match.group(1)
        number = space_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""

    # Format like: 1977 - 001
    year_space_match = re.match(r'(\d{4})\s*-\s*(\d+)', base_filename)
    if year_space_match:
        year = year_space_match.group(1)
        number = year_space_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""

    # Older format (1900s): YY-NNN
    old_match = re.match(r'(\d{2})-(\d+)', base_filename)
    if old_match:
        year_prefix = "19"  # Assuming all 2-digit years are 1900s
        year = f"{year_prefix}{old_match.group(1)}"
        number = old_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""

    # Format like 81-10.json (1981, bylaw 10)
    alternate_match = re.match(r'(\d{2})-(\d+)', base_filename)
    if alternate_match:
        year = f"19{alternate_match.group(1)}"
        number = alternate_match.group(2).zfill(3)
        return year, number, f"{year}-{number}", ""

    # If no match, return empty strings
    return "", "", "", ""

def extract_json_info(filepath):
    """
    Extract 'bylawNumber' and 'bylawYear' from a JSON file.

    Args:
        filepath (str): Path to the JSON file.

    Returns:
        tuple: (bylaw_number, bylaw_year) as strings (empty if not found or error).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
            bylaw_number = data.get('bylawNumber', '')
            bylaw_year = data.get('bylawYear', '')
            return bylaw_number, bylaw_year
    except Exception as e:
        print(f"ERROR: Failed to read {filepath}: {e}")
        return '', ''

def normalize_for_comparison(text):
    """
    Normalize text for flexible comparison by removing spaces, dashes, and leading zeros.
    Also attempts to extract year, number, and suffix for consistent comparison.

    Args:
        text (str): The text to normalize.

    Returns:
        str: Normalized string for comparison.
    """
    if not text:
        return ""
    # Remove spaces, dashes
    normalized = re.sub(r'[\s-]', '', text)
    # Convert any year format (19xx, xx) to consistent format
    year_match = re.match(r'(?:19|20)?(\d{2})(\d{1,3})([A-Z])?', normalized)
    if year_match:
        year = year_match.group(1)
        number = year_match.group(2).lstrip('0')
        suffix = year_match.group(3) or ''
        if number == '':  # Handle case where number was just '0'
            number = '0'
        return f"{year}{number}{suffix}"
    return normalized

def compare_and_validate(filename_info, json_info):
    """
    Compare filename information with JSON content using flexible matching.
    Handles normalization and multiple possible formats for robust validation.

    Args:
        filename_info (tuple): (year, number, combined, suffix) from extract_filename_info.
        json_info (tuple): (bylawNumber, bylawYear) from extract_json_info.

    Returns:
        dict: Validation results and extracted fields for reporting.
    """
    filename_year, filename_number, filename_combined, filename_suffix = filename_info
    json_number, json_year = json_info

    # Normalize for comparison
    norm_filename_combined = normalize_for_comparison(filename_combined)
    norm_json_number = normalize_for_comparison(json_number)
    
    # Include suffix in the comparison if present
    if filename_suffix:
        norm_filename_combined_with_suffix = f"{norm_filename_combined}{filename_suffix}"
    else:
        norm_filename_combined_with_suffix = norm_filename_combined

    # Short year format (2 digits)
    if filename_year and len(filename_year) == 4:
        short_year = filename_year[2:]
        short_year_number = f"{short_year}-{filename_number}"
        norm_short_year_number = normalize_for_comparison(short_year_number)
        
        if filename_suffix:
            norm_short_year_number_with_suffix = f"{norm_short_year_number}{filename_suffix}"
        else:
            norm_short_year_number_with_suffix = norm_short_year_number
    else:
        norm_short_year_number = ""
        norm_short_year_number_with_suffix = ""

    # Number comparison with multiple formats
    number_match = (
        norm_filename_combined in norm_json_number or
        norm_filename_combined_with_suffix in norm_json_number or
        norm_short_year_number in norm_json_number or
        norm_short_year_number_with_suffix in norm_json_number or
        filename_number in json_number or
        (filename_year and filename_year[-2:] + filename_number.lstrip('0')) in norm_json_number or
        (filename_year and filename_year[-2:] + filename_number.lstrip('0') + filename_suffix) in norm_json_number
    )

    # Year validation
    year_match = (
        filename_year == json_year or
        (filename_year and filename_year[-2:] == json_year[-2:])
    )

    return {
        "Filename_Year": filename_year,
        "Filename_Number": filename_number,
        "Filename_Combined": filename_combined,
        "Filename_Suffix": filename_suffix,
        "JSON_Number": json_number,
        "JSON_Year": json_year,
        "Number_Match": number_match,
        "Year_Match": year_match
    }

def main():
    """
    Main entry point for the script. Parses arguments, walks the directory, validates each JSON file, and writes CSV and HTML reports.
    """
    parser = argparse.ArgumentParser(
        description='Validate bylaws by comparing filename with JSON content')
    parser.add_argument('directory', nargs='?', default='.',
                      help='Directory to search for JSON files (default: current directory)')
    args = parser.parse_args()

    root_dir = args.directory
    results = []

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.json'):
                filepath = os.path.join(root, file)

                # Extract info from filename
                filename_info = extract_filename_info(file)

                # Extract info from JSON
                json_info = extract_json_info(filepath)

                # Validate
                validation_result = compare_and_validate(filename_info, json_info)

                # Combine expected JSON number (Filename_Combined + Suffix if present)
                expected_json_number = validation_result['Filename_Combined']
                if validation_result['Filename_Suffix']:
                    expected_json_number += validation_result['Filename_Suffix']

                # Add to results
                results.append({
                    'Filepath': filepath,
                    'Filename': file,
                    'Filename_Year': validation_result['Filename_Year'],
                    'Filename_Number': validation_result['Filename_Number'],
                    'Expected_JSON_Number': expected_json_number,
                    'JSON_Number': validation_result['JSON_Number'],
                    'JSON_Year': validation_result['JSON_Year'],
                    'Number_Match': validation_result['Number_Match'],
                    'Year_Match': validation_result['Year_Match']
                })

    # Write CSV and HTML report
    csv_file = 'bylaw_validation.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Filepath', 'Filename', 'Filename_Year', 'Filename_Number',
                      'Expected_JSON_Number', 'JSON_Number', 'JSON_Year',
                      'Number_Match', 'Year_Match']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)

    html_file = 'bylaw_validation.html'
    generate_html(results, html_file)

    # Print summary
    total = len(results)
    number_matches = sum(1 for r in results if r['Number_Match'])
    year_matches = sum(1 for r in results if r['Year_Match'])
    complete_matches = sum(1 for r in results if r['Number_Match'] and r['Year_Match'])

    print(f"Results summary:")
    print(f"- Total files: {total}")
    print(f"- Number matches: {number_matches} ({number_matches/total*100:.1f}%)")
    print(f"- Year matches: {year_matches} ({year_matches/total*100:.1f}%)")
    print(f"- Complete matches: {complete_matches} ({complete_matches/total*100:.1f}%)")


def generate_html(results, output_file):
    """
    Generate an interactive HTML report with the validation results.
    Uses DataTables for sorting, filtering, and exporting.

    Args:
        results (list): List of result dicts from main validation loop.
        output_file (str): Path to write the HTML report to.
    """
    html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bylaw Validation Report</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.2.2/css/buttons.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.2.2/js/dataTables.buttons.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.1.3/jszip.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.2.2/js/buttons.html5.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.2.2/js/buttons.print.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .summary {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        table.dataTable {
            width: 100%;
            border-collapse: collapse;
        }
        table.dataTable th, table.dataTable td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        table.dataTable th {
            background-color: #f2f2f2;
        }
        .true-value {
            color: green;
            font-weight: bold;
        }
        .false-value {
            color: red;
        }
        .controls {
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <h1>Bylaw Validation Report</h1>

    <div class="summary">
        <h3>Summary</h3>
        <p>Total files processed: <strong id="totalFiles">0</strong></p>
        <p>Files with matching bylaw numbers: <strong id="matchingNumbers">0</strong></p>
        <p>Files with matching bylaw years: <strong id="matchingYears">0</strong></p>
        <p>Files with complete matches: <strong id="completeMatches">0</strong></p>
    </div>

    <table id="resultsTable" class="display" style="width:100%">
        <thead>
            <tr>
                <th>Filename</th>
                <th>Filename Year</th>
                <th>Filename Number</th>
                <th>Expected JSON Number</th>
                <th>JSON Number</th>
                <th>JSON Year</th>
                <th>Number Match</th>
                <th>Year Match</th>
            </tr>
        </thead>
        <tbody>
'''

    # Add the data rows
    number_matches = 0
    year_matches = 0
    complete_matches = 0

    for result in results:
        number_match_class = "true-value" if result['Number_Match'] else "false-value"
        year_match_class = "true-value" if result['Year_Match'] else "false-value"
        number_match_text = "\u2713" if result['Number_Match'] else "\u2717"
        year_match_text = "\u2713" if result['Year_Match'] else "\u2717"

        if result['Number_Match']:
            number_matches += 1
        if result['Year_Match']:
            year_matches += 1
        if result['Number_Match'] and result['Year_Match']:
            complete_matches += 1

        html_content += f'''
            <tr>
                <td>{result['Filename']}</td>
                <td>{result['Filename_Year']}</td>
                <td>{result['Filename_Number']}</td>
                <td>{result['Expected_JSON_Number']}</td>
                <td>{result['JSON_Number']}</td>
                <td>{result['JSON_Year']}</td>
                <td class="{number_match_class}">{number_match_text}</td>
                <td class="{year_match_class}">{year_match_text}</td>
            </tr>'''

    # Finish the HTML
    html_content += '''
        </tbody>
    </table>

    <script>
        $(document).ready(function() {
            // Initialize DataTable
            $('#resultsTable').DataTable({
                dom: 'Bfrtip',
                buttons: [
                    'copy', 'csv', 'excel', 'print'
                ],
                pageLength: 25,
                lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]]
            });

            // Update summary counts
            $('#totalFiles').text(''' + str(len(results)) + ''');
            $('#matchingNumbers').text(''' + str(number_matches) + ''');
            $('#matchingYears').text(''' + str(year_matches) + ''');
            $('#completeMatches').text(''' + str(complete_matches) + ''');
        });
    </script>
</body>
</html>
'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
