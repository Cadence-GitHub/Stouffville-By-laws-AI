#!/usr/bin/env python3
"""
Bylaw Reference Extractor and Analyzer

This script processes a directory of JSON bylaw files, extracts referenced bylaws and their status using the Google Gemini API, and collates all results into a single output JSON file. It is designed to automate the extraction and semantic analysis of bylaw references and their statuses from OCR-extracted bylaw texts.

Features:
- Recursively scans a directory for bylaw JSON files.
- For each file, uses Gemini API to extract:
  - The status of the main bylaw (from filename and text).
  - Any referenced bylaws and their statuses.
  - Expiry or validity dates and their types, if present.
  - An explanation of the status, if available.
- Handles Gemini API rate limits (requests per minute, tokens per minute, requests per day).
- Processes files in parallel using a thread pool for efficiency.
- Handles and logs errors robustly, including API failures and JSON parsing issues.
- Produces a single output JSON file with all extracted data, and a list of bylaws referenced but not present in the input set.

Usage:
    python BylawStatusAnalyzer.py --api-key <API_KEY> --input <input_dir> --output <output.json> [options]

Arguments:
    --api-key, -k   Google Gemini API key (required)
    --input, -i     Path to input directory containing JSON files (required)
    --output, -o    Path to output JSON file (required)
    --log-file, -l  Path to log file (default: bylaw_extraction.log)
    --max-workers, -w  Number of parallel worker threads (default: 4)
    --rpm           Rate limit: Requests per minute (default: 15)
    --tpm           Rate limit: Tokens per minute (default: 1000000)
    --rpd           Rate limit: Requests per day (default: 1500)
    --model, -m     Gemini model ID (default: gemini-2.0-flash)

Example:
    python BylawStatusAnalyzer.py -k <API_KEY> -i ./bylaws -o output.json
"""

import argparse
import os
import json
import glob
import logging
import re
import requests
import time
from collections import deque
import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup logging
def setup_logging(log_file_path):
    """
    Set up logging to both console and file.
    Returns a logger instance.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

# Logger will be initialized in main()
logger = None

# Status mapping based on filename patterns
STATUS_PATTERNS = {
    r"withdrawn": "withdrawn",
    r"cancel": "cancelled",
    r"repeal": "repealed",
    r"spent": "spent",
    r"expir": "expired",
    r"amendment": "amendment",
    r"amend": "amended",
    r"consolidat": "consolidated",
    r"not\s+pass": "did not pass",
    r"not\s+assign": "not assigned",
    r"confirmatory": "confirmatory",
    r"delete": "deleted",
    r"defeat": "defeated",
    r"not\s+used": "not used"
}

class RateLimiter:
    """
    Tracks and enforces Gemini API rate limits (requests per minute, tokens per minute, requests per day).
    """
    def __init__(self, rpm_limit=15, tpm_limit=1000000, rpd_limit=1500):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.rpd_limit = rpd_limit
        self.request_timestamps_minute = deque()
        self.request_timestamps_day = deque()
        self.token_usage_minute = deque()
        self.day_start = datetime.datetime.now()

    def _clean_old_entries(self):
        """Remove entries older than the tracking period."""
        now = datetime.datetime.now()
        minute_ago = now - datetime.timedelta(minutes=1)
        while self.request_timestamps_minute and self.request_timestamps_minute[0] < minute_ago:
            self.request_timestamps_minute.popleft()
        while self.token_usage_minute and self.token_usage_minute[0][0] < minute_ago:
            self.token_usage_minute.popleft()
        if now.date() > self.day_start.date():
            self.request_timestamps_day.clear()
            self.day_start = now
        day_ago = now - datetime.timedelta(days=1)
        while self.request_timestamps_day and self.request_timestamps_day[0] < day_ago:
            self.request_timestamps_day.popleft()

    def check_limits(self):
        """
        Check if we're within rate limits.
        Returns (is_allowed, limits_info)
        """
        self._clean_old_entries()
        rpm_current = len(self.request_timestamps_minute)
        rpd_current = len(self.request_timestamps_day)
        tpm_current = sum(tokens for _, tokens in self.token_usage_minute)
        is_rpm_exceeded = rpm_current >= self.rpm_limit
        is_rpd_exceeded = rpd_current >= self.rpd_limit
        is_tpm_exceeded = tpm_current >= self.tpm_limit
        limits_info = {
            "rpm": {"current": rpm_current, "limit": self.rpm_limit, "exceeded": is_rpm_exceeded},
            "rpd": {"current": rpd_current, "limit": self.rpd_limit, "exceeded": is_rpd_exceeded},
            "tpm": {"current": tpm_current, "limit": self.tpm_limit, "exceeded": is_tpm_exceeded},
        }
        is_allowed = not (is_rpm_exceeded or is_rpd_exceeded or is_tpm_exceeded)
        return is_allowed, limits_info

    def wait_if_needed(self):
        """
        Wait if rate limits are reached. Sleeps until a request is allowed.
        """
        while True:
            is_allowed, limits_info = self.check_limits()
            if is_allowed:
                break
            wait_time = 5  # Default 5 seconds
            if limits_info["rpm"]["exceeded"]:
                oldest = self.request_timestamps_minute[0]
                wait_time = max(wait_time, (oldest + datetime.timedelta(minutes=1) - datetime.datetime.now()).total_seconds())
                logger.warning(f"RPM limit reached ({limits_info['rpm']['current']}/{self.rpm_limit}). Waiting {wait_time:.1f} seconds.")
            if limits_info["tpm"]["exceeded"]:
                oldest, _ = self.token_usage_minute[0]
                wait_time = max(wait_time, (oldest + datetime.timedelta(minutes=1) - datetime.datetime.now()).total_seconds())
                logger.warning(f"TPM limit reached ({limits_info['tpm']['current']}/{self.tpm_limit}). Waiting {wait_time:.1f} seconds.")
            if limits_info["rpd"]["exceeded"]:
                tomorrow = datetime.datetime.now().replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
                wait_time = max(wait_time, (tomorrow - datetime.datetime.now()).total_seconds())
                logger.warning(f"RPD limit reached ({limits_info['rpd']['current']}/{self.rpd_limit}). Daily limit reached, waiting until midnight.")
            wait_time = min(wait_time + 1, 60)  # Cap at 60 seconds max wait
            logger.info(f"Rate limited. Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)

    def record_request(self, token_count=0):
        """
        Record that a request was made (for rate limiting).
        """
        now = datetime.datetime.now()
        self.request_timestamps_minute.append(now)
        self.request_timestamps_day.append(now)
        if token_count > 0:
            self.token_usage_minute.append((now, token_count))

def determine_status_from_filename(filename: str) -> str:
    """
    Determine the status of a bylaw based on its filename using regex patterns.
    Returns a status string (e.g., 'withdrawn', 'repealed', 'in-force/active', etc.).
    """
    filename_lower = filename.lower()
    for pattern, status in STATUS_PATTERNS.items():
        if re.search(pattern, filename_lower):
            return status
    return "in-force/active"

def extract_bylaw_references(model: str, api_key: str, extracted_text: List[str], filename: str, rate_limiter: RateLimiter) -> Dict[str, Any]:
    """
    Use Google Gemini to extract bylaw references and their status from the extracted text.
    Returns a dictionary with bylawfilename, status, referenced_bylaws, and error (if any).
    Handles API errors and retries.
    """
    if not api_key:
        logger.error("Gemini API key not found")
        return {
            "bylawfilename": filename,
            "status": determine_status_from_filename(filename),
            "referenced_bylaws": [],
            "error": "API key not found"
        }
    full_text = "\n\n".join(extracted_text)
    prompt = f"""
    You are analyzing the text of a bylaw - a legal document governing the municipality in Ontraio, Canada. This text was extracted using OCR, so there might be transcription errors.
    
    Act as a legal expert and please extract the following information:
    1. Status of the bylaw you are analyzing. The bylaw number can be deciphered based on the filename. Analyze clauses that may state when it would expire or how it expires or how it is spent and cease to be a bylaw. You status would be based on your analysis. The current bylaw may not be categorized as "Expired" or "Spent" if a date is mentioned. It will always be active or in-force or passed. Thus, if there is a language similar to "This By-law shall expire at 5:00 pm on the 5th day of June, 2026." - it shouldn't set as "Expired" or "Spent". Callout the date - if any - in this format: DD-MMM-YYYY. Call out the date type.
    2. Any referenced bylaws that are in the text. Bylaws are numbered based on year and a set of numbers. You must not confuse a bylaw from Canadian or Ontario  or other provincial legislation such as acts or regulations.
    3. Decipher the status of those referenced bylaws (again the bylaws are numbered with year and sequential numbering) semantically. This status is for the referrenced bylaws. It could be any of these known statuses: withdrawn, cancelled, repealed, spent, expired, in-force/active, amendment or amended, consolidated, did not pass, not assigned, confirmatory, deleted, defeated, and not used. Or what you can try and decipher. You don't need to explain - just the status.
    4. (2) and (3) will be part of an array.
    
    Format your response as a JSON object with the following structure:
    {{
        "bylawfilename": "{filename}",
        "status": "Status",
        "date": "Date when it expires or spent or until when it is valid or when it would be passed. In this format: DD-MMM-YYYY",
        "dateType": "spend or expiry or pass or valid until or any othe clauses"
        "explanation": "clauses for the status - based on your analysis of the text"
        "referenced_bylaws": [
            {{"bylaw_number": "bylaw-number", "status": "status deciphered based on the instructions given to you above, otherwise Active/No status"}}
        ]
    }}
    
    Here is the text of the bylaw:
    {full_text}
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json"
        }
    }
    max_retries = 3
    retry_delay = 2
    rate_limiter.wait_if_needed()
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            rate_limiter.record_request()
            result = response.json()
            try:
                response_text = result["candidates"][0]["content"]["parts"][0]["text"]
                json_match = re.search(r'```json\n(.*?)```', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    parsed_result = json.loads(json_str)
                else:
                    parsed_result = json.loads(response_text)
                return parsed_result
            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse Gemini response for {filename}: {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        "bylawfilename": filename,
                        "status": determine_status_from_filename(filename),
                        "referenced_bylaws": [],
                        "error": f"Failed to parse response: {str(e)}"
                    }
        except requests.RequestException as e:
            logger.error(f"API request failed for {filename}: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.warning(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                return {
                    "bylawfilename": filename,
                    "status": determine_status_from_filename(filename),
                    "referenced_bylaws": [],
                    "error": f"API request failed: {str(e)}"
                }
    return {
        "bylawfilename": filename,
        "status": determine_status_from_filename(filename),
        "referenced_bylaws": [],
        "error": "All API request attempts failed"
    }

def process_bylaw_file(args):
    """
    Process a single bylaw JSON file.
    Loads the file, extracts text, calls Gemini API, and returns the result.
    Handles errors and missing data.
    """
    file_path, api_key, rate_limiter, model = args
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        extracted_text = data.get("extractedText", [])
        if not extracted_text:
            logger.warning(f"No extractedText found in {file_path}")
            return {
                "bylawfilename": Path(file_path).name,
                "status": determine_status_from_filename(Path(file_path).name),
                "referenced_bylaws": [],
                "error": "No extractedText found"
            }
        result = extract_bylaw_references(
            model = model,
            api_key=api_key,
            extracted_text=extracted_text,
            filename=Path(file_path).name,
            rate_limiter=rate_limiter
        )
        logger.info(f"Processed {file_path}")
        return result
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON file: {file_path}")
        return {
            "bylawfilename": Path(file_path).name,
            "status": determine_status_from_filename(Path(file_path).name),
            "referenced_bylaws": [],
            "error": "Invalid JSON file"
        }
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return {
            "bylawfilename": Path(file_path).name,
            "status": determine_status_from_filename(Path(file_path).name),
            "referenced_bylaws": [],
            "error": f"Processing error: {str(e)}"
        }

def find_bylaws_without_status(results: List[Dict[str, Any]]) -> List[str]:
    """
    Find bylaws that are referenced but don't have a status assigned.
    Returns a list of bylaw numbers.
    """
    all_bylaws = {}
    for result in results:
        bylaw_filename = result["bylawfilename"]
        status = result["status"]
        if bylaw_filename.endswith(".json"):
            bylaw_filename = bylaw_filename[:-5]
        all_bylaws[bylaw_filename] = status
    referenced_bylaws = {}
    for result in results:
        for ref in result.get("referenced_bylaws", []):
            bylaw_number = ref.get("bylaw_number")
            if bylaw_number and bylaw_number not in all_bylaws:
                referenced_bylaws[bylaw_number] = ref.get("status")
    return [bylaw for bylaw, status in referenced_bylaws.items() if not status]

def main():
    """
    Main entry point: parses arguments, sets up logging, processes all bylaw files, and writes output.
    """
    parser = argparse.ArgumentParser(description="Extract bylaw references from JSON files")
    parser.add_argument("--api-key", "-k", required=True, help="Google Gemini API key")
    parser.add_argument("--input", "-i", required=True, help="Path to input directory containing JSON files")
    parser.add_argument("--output", "-o", required=True, help="Path to output JSON file")
    parser.add_argument("--log-file", "-l", default="bylaw_extraction.log", help="Path to log file")
    parser.add_argument("--max-workers", "-w", type=int, default=4, help="Maximum number of worker threads")
    parser.add_argument("--rpm", type=int, default=15, help="Rate limit: Maximum Requests Per Minute allowed")
    parser.add_argument("--tpm", type=int, default=1000000, help="Rate limit: Maximum Tokens Per Minute allowed")
    parser.add_argument("--rpd", type=int, default=1500, help="Rate limit: Maximum Requests Per Day allowed")
    parser.add_argument("--model", "-m", default="gemini-2.0-flash", help="Gemini model ID (default: gemini-2.0-flash)")
    args = parser.parse_args()
    global logger
    logger = setup_logging(args.log_file)
    logger.info("Starting bylaw reference extraction process")
    rate_limiter = RateLimiter(
        rpm_limit=args.rpm,
        tpm_limit=args.tpm,
        rpd_limit=args.rpd
    )
    model = args.model
    input_dir = Path(args.input)
    json_files = []
    if not input_dir.is_dir():
        logger.error(f"Input directory does not exist: {input_dir}")
        return 1
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.json'):
                filepath = os.path.join(root, file)
                json_files.append(filepath)
    logger.info(f"Found {len(json_files)} JSON files in {input_dir}")
    results = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        task_args = [(file_path, args.api_key, rate_limiter, model) for file_path in json_files]
        for result in executor.map(process_bylaw_file, task_args):
            results.append(result)
    bylaws_without_status = find_bylaws_without_status(results)
    for bylaw in bylaws_without_status:
        logger.info(f"Assigning default status 'Active/No status' to {bylaw}")
    output = {
        "bylaw_references": results,
        "bylaws_without_status": [
            {"bylaw_number": bylaw, "status": "Active/No status"}
            for bylaw in bylaws_without_status
        ]
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    logger.info(f"Output written to {args.output}")
    return 0

if __name__ == "__main__":
    exit(main())
