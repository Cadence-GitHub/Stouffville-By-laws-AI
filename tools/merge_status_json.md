# merge_status_json.py

## Overview

`merge_status_json.py` is a utility script for merging multiple `status.json` files from bylaw folders (e.g., 'By-laws 2020', 'By-laws 2021', etc.) into a single consolidated JSON file. It also produces a summary of bylaw statuses and modification histories, and logs any errors encountered during processing. This tool is designed to help consolidate and audit bylaw status data across multiple years or sources.

## Main Features

- **Recursive Folder Search:** Finds all folders matching the pattern 'By-laws YYYY' under a specified root directory.
- **Batch File Collection:** Collects all `status.json` files from the discovered folders.
- **Robust Merging:** Merges all bylaw references and bylaws without status into a single combined JSON file.
- **Status & Modification Summary:** Tracks the latest status and modification history for each bylaw, including which bylaws modified others.
- **Error Handling:** Handles JSON parsing errors gracefully, logs the context of any issues, and continues processing other files.
- **Sorted Output:** Sorts bylaws and modification histories in chronological order for easy auditing.
- **Multiple Outputs:**
  - Combined JSON file with all bylaw references and bylaws without status.
  - Summary JSON file with the latest status and modification history for each bylaw.
  - Error log JSON file if any files could not be processed.

## Script Flow and Logic

1. **Argument Parsing:**
   - Accepts arguments for the root directory, output file paths, and error log location.

2. **Folder Discovery:**
   - Recursively searches for folders named like 'By-laws YYYY'.
   - Sorts folders by year (newest first).

3. **File Collection:**
   - Collects all `status.json` files from the discovered folders.

4. **Merging and Processing:**
   - For each `status.json` file:
     - Loads the file and extracts bylaw references and bylaws without status.
     - Tracks the status and modification history for each bylaw.
     - Handles and logs any JSON parsing errors, showing the context for easier debugging.
   - Sorts modification histories in reverse chronological order (newest first).
   - Sorts the summary of bylaws in chronological order (oldest first).

5. **Output:**
   - Writes the combined data to the specified output file.
   - Writes the summary data to a separate summary file.
   - Writes any errors encountered to an error log file.
   - Prints a summary of the merging process to the console.

## Use Case

This script is ideal for municipalities, archivists, or researchers who need to consolidate, audit, or analyze bylaw status data from multiple years or sources, ensuring a unified and traceable dataset.

---

*See the script's docstrings and comments for further technical details.* 