# modified-json-checker.py

## Overview

`modified-json-checker.py` is a validation tool for bylaw JSON files. It compares information extracted from each file's name (treated as the source of truth) with the `bylawNumber` and `bylawYear` fields inside the JSON. The script supports a wide range of filename formats and produces both CSV and interactive HTML reports summarizing the validation results.

## Main Features

- **Flexible Filename Parsing:** Handles modern, legacy, and consolidated filename formats to extract year, number, and suffix.
- **Content Validation:** Compares the canonical bylaw number and year (from the filename) with the values in the JSON file.
- **Normalization:** Uses normalization logic to allow for flexible matching (removes spaces, dashes, leading zeros, etc.).
- **Batch Processing:** Recursively processes all JSON files in a given directory.
- **Reporting:**
  - Outputs a CSV file (`bylaw_validation.csv`) with per-file validation results.
  - Generates an interactive HTML report (`bylaw_validation.html`) with summary statistics and filtering/export features.

## Script Flow and Logic

1. **Argument Parsing:**
   - Accepts a directory to process (default: current directory).

2. **File Processing:**
   - Recursively walks the directory tree.
   - For each `.json` file found:
     - Extracts year, number, and suffix from the filename.
     - Loads the JSON file and extracts `bylawNumber` and `bylawYear`.
     - Normalizes and compares the extracted and JSON values for flexible matching.
     - Collects results for reporting.

3. **Reporting:**
   - Writes a CSV file with all validation results.
   - Generates an interactive HTML report with summary statistics and per-file details (including pass/fail for number and year).
   - Prints a summary to the console.

## Use Case

This script is useful for auditing and validating large collections of bylaw JSON files, ensuring that the metadata inside each file matches the canonical information encoded in the filename.

---

*See the script's docstrings and comments for further technical details.* 