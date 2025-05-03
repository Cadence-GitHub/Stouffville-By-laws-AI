# recategorize-statuses-isactive.py

## Overview

`recategorize-statuses-isactive.py` is a script designed to process a JSON file containing bylaw reference information, categorize the status of each referenced bylaw as active, inactive, or undetermined (NA), and generate a searchable, sortable HTML report. The script uses regular expressions to determine the `isActive` status based on keywords in the status string, and logs all processing activities for traceability.

## Main Features

- **Status Categorization:** Uses robust regular expressions to classify each referenced bylaw's status as active (`True`), inactive (`False`), or undetermined (`NA`).
- **Batch Processing:** Processes all referenced bylaws within a structured JSON file, supporting large datasets.
- **HTML Reporting:** Generates a feature-rich HTML report (`bylaw_statuses_report.html`) with searching, sorting, and filtering capabilities using DataTables.js.
- **Logging:** Logs all processing steps, warnings, and errors to both a file and the console for transparency and debugging.
- **Configurable Paths:** Allows easy modification of input/output file paths and log file location.

## Script Flow and Logic

1. **Configuration:**
   - Set file paths for the input JSON, output HTML report, and log file.

2. **Logging Setup:**
   - Configures logging to output to both a file and the console.

3. **Status Categorization Logic:**
   - Defines regular expressions for active and inactive status keywords.
   - The `determine_is_active` function applies these patterns to each status string, prioritizing inactive matches.

4. **Main Processing:**
   - Loads the input JSON file and validates its structure.
   - Iterates through each main bylaw and its referenced bylaws.
   - For each referenced bylaw:
     - Extracts the bylaw number and original status.
     - Categorizes the status using the defined logic.
     - Collects all relevant data for reporting.

5. **HTML Report Generation:**
   - Generates a styled HTML report with a searchable, sortable table of all processed referenced bylaws and their categorized statuses.

6. **Output:**
   - Writes the HTML report to the specified path.
   - Logs all actions and any issues encountered during processing.

## Use Case

This script is ideal for organizations or researchers who need to audit, review, or present the status of referenced bylaws in a clear, interactive format, especially when dealing with large or complex bylaw datasets.

---

*See the script's docstrings and comments for further technical details.* 