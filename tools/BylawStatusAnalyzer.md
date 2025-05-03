# BylawStatusAnalyzer.py

## Overview

`BylawStatusAnalyzer.py` is an advanced tool for extracting, analyzing, and consolidating bylaw reference information from a directory of JSON bylaw files. It leverages the Google Gemini API to semantically extract referenced bylaws and their statuses from OCR-extracted bylaw texts, and produces a unified output JSON file for further analysis or reporting.

## Main Features

- **Recursive Directory Scanning:** Recursively finds all JSON bylaw files in a specified directory.
- **Semantic Extraction via Gemini API:** For each bylaw file, uses the Gemini API to extract:
  - The status of the main bylaw (from filename and text).
  - Any referenced bylaws and their statuses.
  - Expiry or validity dates and their types, if present.
  - An explanation of the status, if available.
- **Robust Rate Limiting:** Enforces Gemini API rate limits (requests per minute, tokens per minute, requests per day) to avoid throttling or bans.
- **Parallel Processing:** Processes files in parallel using a thread pool for efficiency and speed.
- **Error Handling and Logging:** Logs all actions, warnings, and errors to both a file and the console. Handles API failures, JSON parsing issues, and missing data gracefully.
- **Unified Output:** Produces a single output JSON file containing all extracted bylaw references and a list of bylaws referenced but not present in the input set.

## Script Flow and Logic

1. **Argument Parsing:**
   - Accepts arguments for the Gemini API key, input directory, output file, log file, number of worker threads, rate limits, and Gemini model ID.

2. **Logging Setup:**
   - Configures logging to output to both a file and the console.

3. **File Discovery:**
   - Recursively scans the input directory for all `.json` files.

4. **Parallel Processing:**
   - Uses a thread pool to process files in parallel, calling the Gemini API for each file.
   - For each file:
     - Loads the JSON and extracts the OCR text.
     - Calls the Gemini API to extract bylaw references and statuses.
     - Handles and logs any errors (API, JSON, or missing data).

5. **Rate Limiting:**
   - The `RateLimiter` class tracks and enforces API rate limits, pausing processing as needed to stay within allowed limits.

6. **Post-processing:**
   - Identifies bylaws that are referenced but not present in the input set, assigning them a default status.

7. **Output:**
   - Writes a unified output JSON file containing all bylaw references and bylaws without status.
   - Logs a summary of the process.

## Use Case

This script is ideal for municipalities, legal researchers, or data analysts who need to automate the extraction and semantic analysis of bylaw references and statuses from large collections of bylaw documents, especially when working with OCR-extracted text and requiring robust error handling and API rate management.

---

*See the script's docstrings and comments for further technical details.* 