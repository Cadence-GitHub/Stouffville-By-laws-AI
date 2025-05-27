# bylaw-json-updater.py

## Overview

`bylaw-json-updater.py` is a utility script designed to standardize and update bylaw JSON files in a directory tree. It ensures that each JSON file's `bylawNumber` field matches a canonical format derived from its filename, adds a `bylawFileName` field, and produces a detailed HTML report of all actions taken. The script can operate in a dry-run mode (default) or actually write changes to disk.

## Main Features

- **Recursive Directory Search:** Walks through a specified directory and all subdirectories to find JSON files.
- **Filename Parsing:** Extracts year, number, and optional suffix from each filename using robust regular expressions, supporting a variety of legacy and modern formats.
- **Field Normalization:** Updates the `bylawNumber` field in each JSON file to match the canonical format and adds a `bylawFileName` field.
- **Dry-Run Support:** By default, runs in dry-run mode (no files are modified). Use `--no-dry-run` to apply changes.
- **Logging:** Logs all actions to both a file and the console for traceability.
- **HTML Reporting:** Generates a styled HTML report summarizing all processed files, including successes and errors.

## Script Flow and Logic

1. **Argument Parsing:**
   - Accepts a directory to process (default: current directory).
   - Supports `--dry-run` (default) and `--no-dry-run` flags.

2. **Logging Setup:**
   - Logs to both a file (`json_spider.log`) and the console.

3. **File Processing:**
   - Recursively walks the directory tree.
   - For each `.json` file found:
     - Parses the filename to extract the expected bylaw number.
     - Loads the JSON file and updates the `bylawNumber` and `bylawFileName` fields.
     - If not in dry-run, writes the changes back to the file.
     - Logs the action and collects results for reporting.

4. **Reporting:**
   - After processing all files, generates an HTML report (`bylaw_json_update_report.html`) summarizing:
     - Total files processed
     - Number of successes and errors
     - Per-file details (old/new bylaw numbers, status, errors)

## Use Case

This script is ideal for municipalities or organizations managing large collections of bylaw documents, ensuring consistency and traceability across all bylaw JSON files.

---

*See the script's docstrings and comments for further technical details.* 