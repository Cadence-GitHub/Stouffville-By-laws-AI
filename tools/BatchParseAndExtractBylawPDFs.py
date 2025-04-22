#!/usr/bin/env python3
"""
PDF Data Extraction with Gemini API

This script uploads PDF files from a directory to Gemini API and processes them,
extracting structured data according to a specified schema. It includes rate limiting
to stay within Google's API constraints.
"""

import argparse
import os
import json
import requests
import time
import datetime
import glob
import logging
import csv
from collections import deque
from pathlib import Path

# Setup logging with both file and console handlers
def setup_logging(log_file_path):
    """Set up logging to both console and file"""
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Create and configure file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Logger will be initialized in main()
logger = None

def identify_errored_pdfs(input_dir, output_dir):
    """
    Identify PDFs that need to be reprocessed based on error files in the output directory.
    Only identifies files with "-error.json" suffix (not "-reprocessed-error.json"),
    to prevent infinite reprocessing loops.

    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory containing JSON output files

    Returns:
        List of paths to PDF files that need to be reprocessed
    """
    # Find all error JSON files (specifically "-error.json" not "-reprocessed-error.json")
    error_jsons = glob.glob(os.path.join(output_dir, "*-error.json"))

    # Check if any files matched the pattern
    if not error_jsons:
        logger.info("No error files found for reprocessing")
        return []

    # Count how many reprocessed error files exist (for reporting only)
    reprocessed_error_files = glob.glob(os.path.join(output_dir, "*-reprocessed-error.json"))
    if reprocessed_error_files:
        logger.info(f"Found {len(reprocessed_error_files)} previously reprocessed error files (these will not be reprocessed again)")

    # Extract base names (without the -error.json suffix)
    error_base_names = [os.path.basename(error_file).replace("-error.json", "") for error_file in error_jsons]

    # Find corresponding PDF files in input directory
    pdf_files_to_reprocess = []
    for base_name in error_base_names:
        pdf_path = os.path.join(input_dir, f"{base_name}.pdf")
        if os.path.isfile(pdf_path):
            pdf_files_to_reprocess.append(pdf_path)
        else:
            logger.warning(f"Could not find PDF file for error JSON: {base_name}")

    return pdf_files_to_reprocess

def load_url_mappings(csv_path):
    """Load URL mappings from a CSV file.

    Args:
        csv_path: Path to the CSV file with filename-URL mappings

    Returns:
        Dictionary mapping PDF filenames to URLs
    """
    if not csv_path:
        return {}

    url_map = {}
    try:
        logger.info(f"Loading URL mapping from {csv_path}...")
        with open(csv_path, 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file)
            # Check for header and skip if present
            first_row = next(csv_reader, None)
            if first_row and first_row[0].lower() == 'file name' and first_row[1].lower() == 'url':
                pass  # Skip the header
            else:
                # If no header or different format, add the first row
                if first_row and len(first_row) >= 2:
                    url_map[first_row[0]] = first_row[1]

            # Process the rest of the rows
            for row in csv_reader:
                if len(row) >= 2:
                    url_map[row[0]] = row[1]

        logger.info(f"Loaded {len(url_map)} URLs from CSV file")
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return {}

    return url_map

class RateLimiter:
    """Tracks and enforces Gemini API rate limits"""

    def __init__(self, rpm_limit=15, tpm_limit=1000000, rpd_limit=1500):
        self.rpm_limit = rpm_limit  # Requests per minute
        self.tpm_limit = tpm_limit  # Tokens per minute
        self.rpd_limit = rpd_limit  # Requests per day

        # Tracking request timestamps
        self.request_timestamps_minute = deque()
        self.request_timestamps_day = deque()

        # Tracking token usage (last 60 seconds)
        self.token_usage_minute = deque()

        # Store the first day's timestamp for RPD counting
        self.day_start = datetime.datetime.now()

    def _clean_old_entries(self):
        """Remove entries older than the tracking period"""
        now = datetime.datetime.now()

        # Clean minute tracking (RPM, TPM)
        minute_ago = now - datetime.timedelta(minutes=1)
        while self.request_timestamps_minute and self.request_timestamps_minute[0] < minute_ago:
            self.request_timestamps_minute.popleft()

        while self.token_usage_minute and self.token_usage_minute[0][0] < minute_ago:
            self.token_usage_minute.popleft()

        # Clean day tracking (RPD)
        # Reset if a new day starts
        if (now.date() > self.day_start.date()):
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

        # Calculate current usage
        rpm_current = len(self.request_timestamps_minute)
        rpd_current = len(self.request_timestamps_day)
        tpm_current = sum(tokens for _, tokens in self.token_usage_minute)

        # Check if any limit is exceeded
        is_rpm_exceeded = rpm_current >= self.rpm_limit
        is_rpd_exceeded = rpd_current >= self.rpd_limit
        is_tpm_exceeded = tpm_current >= self.tpm_limit

        # Return status and info
        limits_info = {
            "rpm": {"current": rpm_current, "limit": self.rpm_limit, "exceeded": is_rpm_exceeded},
            "rpd": {"current": rpd_current, "limit": self.rpd_limit, "exceeded": is_rpd_exceeded},
            "tpm": {"current": tpm_current, "limit": self.tpm_limit, "exceeded": is_tpm_exceeded},
        }

        is_allowed = not (is_rpm_exceeded or is_rpd_exceeded or is_tpm_exceeded)

        return is_allowed, limits_info

    def wait_if_needed(self):
        """Wait if rate limits are reached"""
        while True:
            is_allowed, limits_info = self.check_limits()
            if is_allowed:
                break

            # Determine wait time based on which limit was hit
            wait_time = 5  # Default 5 seconds

            if limits_info["rpm"]["exceeded"]:
                # Wait until oldest request falls out of the 1-minute window
                oldest = self.request_timestamps_minute[0]
                wait_time = max(wait_time, (oldest + datetime.timedelta(minutes=1) - datetime.datetime.now()).total_seconds())
                logger.warning(f"RPM limit reached ({limits_info['rpm']['current']}/{self.rpm_limit}). Waiting {wait_time:.1f} seconds.")

            if limits_info["tpm"]["exceeded"]:
                # Wait until oldest token usage falls out of the 1-minute window
                oldest, _ = self.token_usage_minute[0]
                wait_time = max(wait_time, (oldest + datetime.timedelta(minutes=1) - datetime.datetime.now()).total_seconds())
                logger.warning(f"TPM limit reached ({limits_info['tpm']['current']}/{self.tpm_limit}). Waiting {wait_time:.1f} seconds.")

            if limits_info["rpd"]["exceeded"]:
                # Reset at midnight
                tomorrow = datetime.datetime.now().replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
                wait_time = max(wait_time, (tomorrow - datetime.datetime.now()).total_seconds())
                logger.warning(f"RPD limit reached ({limits_info['rpd']['current']}/{self.rpd_limit}). Daily limit reached, waiting until midnight.")

            # Add a little buffer
            wait_time = min(wait_time + 1, 60)  # Cap at 60 seconds max wait

            logger.info(f"Rate limited. Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)

    def record_request(self, token_count=0):
        """Record that a request was made"""
        now = datetime.datetime.now()
        self.request_timestamps_minute.append(now)
        self.request_timestamps_day.append(now)

        if token_count > 0:
            self.token_usage_minute.append((now, token_count))

def upload_file(api_key, pdf_path, display_name=None, rate_limiter=None):
    """Upload a PDF file to Gemini API using resumable upload"""

    if rate_limiter:
        rate_limiter.wait_if_needed()

    base_url = "https://generativelanguage.googleapis.com"

    # Use filename as display name if not provided
    if display_name is None:
        display_name = os.path.basename(pdf_path).split('.')[0]

    # Get file size
    file_size = os.path.getsize(pdf_path)

    # Initial resumable request defining metadata
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": "application/pdf",
        "Content-Type": "application/json"
    }

    data = f'{{"file": {{"display_name": "{display_name}"}}}}'

    max_retries = 3
    retry_delay = 2  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{base_url}/upload/v1beta/files?key={api_key}",
                headers=headers,
                data=data
            )

            response.raise_for_status()  # Raise exception for HTTP errors

            # Record the request if rate limiter is provided
            if rate_limiter:
                rate_limiter.record_request()

            # Extract upload URL from response headers
            upload_url = None
            for header, value in response.headers.items():
                if header.lower() == "x-goog-upload-url":
                    upload_url = value
                    break

            if not upload_url:
                raise ValueError("Failed to get upload URL from response headers")

            break  # Success, exit retry loop

        except (requests.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Upload request failed: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Upload request failed after {max_retries} attempts: {str(e)}")
                raise

    # Upload the actual bytes
    with open(pdf_path, "rb") as f:
        file_content = f.read()

    upload_headers = {
        "Content-Length": str(file_size),
        "X-Goog-Upload-Offset": "0",
        "X-Goog-Upload-Command": "upload, finalize"
    }

    for attempt in range(max_retries):
        try:
            if rate_limiter:
                rate_limiter.wait_if_needed()

            upload_response = requests.post(
                upload_url,
                headers=upload_headers,
                data=file_content
            )

            upload_response.raise_for_status()

            # Record the request if rate limiter is provided
            if rate_limiter:
                rate_limiter.record_request()

            file_info = upload_response.json()

            # Extract file URI
            try:
                file_uri = file_info.get("file", {}).get("uri")
                if not file_uri:
                    raise ValueError("Failed to get file URI from response")
                return file_uri
            except Exception as e:
                logger.error(f"Error parsing response: {str(e)}")
                logger.error(f"Raw response: {upload_response.text}")
                raise

        except (requests.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"File upload failed: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"File upload failed after {max_retries} attempts: {str(e)}")
                raise

def delete_file(api_key, file_uri, rate_limiter=None):
    """Delete a file from Gemini API"""

    if rate_limiter:
        rate_limiter.wait_if_needed()

    # Extract file name from URI
    # URI format is typically files/{file_name}
    parts = file_uri.split('/')
    if len(parts) < 2:
        logger.error(f"Invalid file URI format: {file_uri}")
        return False

    file_name = parts[-1]

    url = f"https://generativelanguage.googleapis.com/v1beta/files/{file_name}?key={api_key}"

    max_retries = 3
    retry_delay = 2  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            response = requests.delete(url)

            response.raise_for_status()

            # Record the request if rate limiter is provided
            if rate_limiter:
                rate_limiter.record_request()

            logger.info(f"File {file_name} deleted successfully")
            return True

        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"File deletion failed: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"File deletion failed after {max_retries} attempts: {str(e)}")
                return False

def count_tokens(api_key, file_uri, model="gemini-2.0-flash", rate_limiter=None):
    """Count tokens in a PDF file"""

    if rate_limiter:
        rate_limiter.wait_if_needed()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:countTokens?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    # Simple prompt for token counting
    prompt = "Give me a summary of this document."

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"file_data": {"mime_type": "application/pdf", "file_uri": file_uri}}
                ]
            }
        ]
    }

    max_retries = 3
    retry_delay = 2  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data)
            )

            response.raise_for_status()

            # Record the request if rate limiter is provided
            if rate_limiter:
                rate_limiter.record_request()

            result = response.json()

            # Extract token count
            token_count = result.get("totalTokens", 0)
            return token_count

        except (requests.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Token count request failed: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Token count request failed after {max_retries} attempts: {str(e)}")
                raise

def extract_structured_data(api_key, file_uri, model="gemini-2.0-flash", rate_limiter=None, token_count=0):
    """Extract structured data from a PDF file"""

    if rate_limiter:
        rate_limiter.wait_if_needed()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    # Bylaw schema
    schema = {
      "type": "object",
      "properties": {
        "bylawNumber": {"type": "string"},
        "bylawYear": {"type": "string"},
        "bylawType": {"type": "string"},
        "bylawHeader": {"type": "string"},
        "extractedText": {  "type": "array",  "items": {    "type": "string"  }},
        "legalTopics": {  "type": "array",  "items": {    "type": "string"  }},
        "legislation": {  "type": "array",  "items": {    "type": "string"  }},
        "whyLegislation": {  "type": "array",  "items": {    "type": "string"  }},
        "otherBylaws": {  "type": "array",  "items": {    "type": "string"  }},
        "whyOtherBylaws": {  "type": "array",  "items": {    "type": "string"  }},
        "condtionsAndClauses": {"type": "string"},
        "entityAndDesignation": {  "type": "array",  "items": {    "type": "string"  }},
        "otherEntitiesMentioned": {  "type": "array",  "items": {    "type": "string"  }},
        "locationAddresses": {  "type": "array",  "items": {    "type": "string"  }},
        "moneyAndCategories": {  "type": "array",  "items": {    "type": "string"  }},
        "table": {  "type": "array",  "items": {    "type": "string"  }},
        "keywords": {  "type": "array",  "items": {    "type": "string"  }},
        "keyDatesAndInfo": {  "type": "array",  "items": {    "type": "string"  }},
        "otherDetails": {"type": "string"},
        "newsSources": {  "type": "array",  "items": {    "type": "string"  }},
        "hasEmbeddedImages": {"type": "boolean"},
        "imageDesciption": {  "type": "array",  "items": {    "type": "string"  }},
        "hasEmbeddedMaps": {"type": "boolean"},
        "mapDescription": {  "type": "array",  "items": {    "type": "string"  }},
        "laymanExplanation": {"type": "string"},
        "urlOriginalDocument": {"type":"string"}

      },
      "required": ["bylawNumber", "bylawYear", "bylawType", "bylawHeader", "extractedText", "legalTopics", "legislation", "otherBylaws", "condtionsAndClauses", "entityAndDesignation", "otherEntitiesMentioned", "locationAddresses", "moneyAndCategories", "table", "otherDetails", "hasEmbeddedImages", "hasEmbeddedMaps", "keywords", "laymanExplanation", "keyDatesAndInfo", "imageDesciption", "mapDescription", "whyLegislation", "whyOtherBylaws", "newsSources", "urlOriginalDocument"]
    }

    prompt = """You are a fantastic parser of legal documents. You excel at reasoning while parsing and extracting. You follow instructions like a robot. You will validate the json produced against the PDF and the instructions provided before responding. For PDF file attached, produce a json file that has the below information

bylawNumber: Bylaw alphanumeric code in the format YYYY-NNN where YYYY is the year and NNN is a three-digit bylaw number (e.g., 2015-139)
bylawYear: Bylaw year
bylawType: Bylaws are numbered in a unique way. Ending with ZO could be zoning order, AP could be appointment, FI could be financial. Use your reasoning skills to define the type. Do not abbreviate.
bylawHeader: The bolded text at the top of the document that forms part of the contiguous text that follows.
extractedText: Put each page text extract from PDF without hallucination into its own array index. Separate paragraphs using 3 newline characters. Separate pages into its own array.
legalTopics: Canadian legal topics
legislation: Acts, Regulations with sections referenced or mentioned. If nothing is found say None.
whyLegislation: If acts or regulation are mentioned, why are they mentioned? Is there a significance? Detail for each mentioned. Separate it by pipe symbol.
otherBylaws: Other bylaws mentioned. If nothing is found say None.
whyOtherBylaws: If other bylaws are mentioned, why are they mentioned? Is there a significance? Detail for each bylaw mentioned. Separate it by pipe symbol.
condtionsAndClauses: Conditions and clauses. If nothing is found say None.
entityAndDesignation: Signing entity (people or person) name and their designations
otherEntitiesMentioned: Other Entity (people or person or institutions or companies) names. If nothing is found say None.
locationAddresses: Addresses or locations mentioned - each one of them. If nothing is found say None.
moneyAndCategories: Money and category (examples of category: expense/revenue/payment etc.). If nothing is found say None.
table: If you encounter tables, please provide them as an array. Separate columns by using pipe symbol. use an agent or a function, if you cannot extract the table by yourself.
keywords: Extract a lexicon of legal keywords from the text so that we can use it to search
keyDatesAndInfo: Key dates (in DD-MMM-YYYY format - use an agent or a function, if you cannot do it by yourself.) and information for the date mentioned in the document. If nothing is found say None.
otherDetails: Other details that are deemed necessary. If nothing is found say None.
newsSources: Are there news sources mentioned? From where? If so, detail why and what here for each of them.
hasEmbeddedImages: Are there embedded images? (true/false)
imageDesciption: If there are images, describe each of the image in detail. If there are multiple images, title them and describe them individually and separate others. use an agent or a function, if you cannot read the image by yourself.
hasEmbeddedMaps: Are there embedded maps? (true/false)
mapDescription: If there are maps, describe each of the images in detail. If there are multiple maps, title them and describe them individually and separate others. use an agent or a function, if you cannot do read the map by yourself.
laymanExplanation: Provide a plain simple english version of the bylaw so that a layman can understand. Do not hallucinate. Be precise and accurate.
urlOriginalDocument: URL to original document will always be empty. Do not populate anything here.

AVOID: Trying to cram in entire decoded image in the extractedText. AVOID: printing or repeating newline characters \\n or dashes beyond what was requested - that breaches your output tokens in the json."""

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"file_data": {"mime_type": "application/pdf", "file_uri": file_uri}}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "responseSchema": schema,
            "responseMimeType":"application/json"
        }
    }

    max_retries = 3
    retry_delay = 2  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data)
            )

            response.raise_for_status()

            # Record the request with token usage if rate limiter is provided
            if rate_limiter:
                rate_limiter.record_request(token_count)

            result = response.json()

            # Extract usage metadata if available
            usage_metadata = {}
            if "usageMetadata" in result:
                usage_metadata = result["usageMetadata"]
                logger.info(f"Usage metadata: {usage_metadata}")

            # Extract and parse the JSON from the text response
            for candidate in result.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    if "text" in part:
                        text = part["text"]
                        try:
                            # Look for JSON object in the text
                            json_start = text.find("{")
                            json_end = text.rfind("}") + 1
                            if json_start >= 0 and json_end > json_start:
                                json_str = text[json_start:json_end]
                                return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass

            return result

        except (requests.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Extract data request failed: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Extract data request failed after {max_retries} attempts: {str(e)}")
                raise

def validate_json_schema(data):
    """
    Validate if the JSON response has the expected structure.
    Returns True if valid, False if invalid.
    """
    # Check for expected fields in a valid response
    expected_fields = [
        "bylawNumber", "bylawYear", "bylawType", "bylawHeader", "extractedText", "legalTopics", "legislation", "otherBylaws", "condtionsAndClauses", "entityAndDesignation", "otherEntitiesMentioned", "locationAddresses", "moneyAndCategories", "table", "otherDetails", "hasEmbeddedImages", "hasEmbeddedMaps", "keywords", "laymanExplanation", "keyDatesAndInfo", "imageDesciption", "mapDescription", "whyLegislation", "whyOtherBylaws", "newsSources", "urlOriginalDocument"
    ]

    # If the response has "candidates" at the top level, it's likely an error response
    if "candidates" in data:
        logger.warning("Response appears to be an error - found 'candidates' at top level")
        return False

    # Check if at least 70% of expected fields are present (allowing for some variation)
    fields_found = 0
    for field in expected_fields:
        if field in data:
            fields_found += 1

    validity_percentage = (fields_found / len(expected_fields)) * 100
    if validity_percentage < 70:
        logger.warning(f"Response appears to be invalid - only {validity_percentage:.1f}% of expected fields present")
        return False

    return True

def process_pdf_file(api_key, pdf_path, output_dir, model="gemini-2.0-flash", rate_limiter=None, url_map=None, is_reprocessing=False):
    """Process a single PDF file and save the output JSON"""
    try:
        # Determine output filename
        pdf_name = os.path.basename(pdf_path)
        base_name = os.path.splitext(pdf_name)[0]
        output_path = os.path.join(output_dir, f"{base_name}.json")
        error_output_path = os.path.join(output_dir, f"{base_name}-error.json")
        reprocessed_error_path = os.path.join(output_dir, f"{base_name}-reprocessed-error.json")

        logger.info(f"Processing {pdf_name}...")

        # Upload file
        logger.info(f"Uploading {pdf_path}...")
        file_uri = upload_file(api_key, pdf_path, rate_limiter=rate_limiter)
        logger.info(f"File URI: {file_uri}")

        # Count tokens
        logger.info("Counting tokens...")
        token_count = count_tokens(api_key, file_uri, model, rate_limiter)
        logger.info(f"Token count: {token_count}")
        if token_count > 10000:
            # Skip large token to process manually
            logger.info(f"Large token detected. Skipping. Run it manually.")
            return False

        # Extract structured data
        logger.info(f"Extracting structured data with model {model}...")
        response = extract_structured_data(api_key, file_uri, model, rate_limiter, token_count)

        # Validate JSON schema
        is_valid = validate_json_schema(response)

        # Add URL to response if valid and URL mapping is available
        if is_valid and url_map:
            # Look up URL by PDF filename
            if pdf_name in url_map:
                # Add the URL to the JSON response
                response['urlOriginalDocument'] = url_map[pdf_name]
                logger.info(f"Added URL for {pdf_name}: {url_map[pdf_name]}")
            else:
                logger.warning(f"No URL found for {pdf_name}")

            # If reprocessing, remove existing error file
            if is_reprocessing and os.path.exists(error_output_path):
                logger.info(f"Removing existing error file: {error_output_path}")
                os.remove(error_output_path)

                # Also remove any previous reprocessed error file if it exists
                if os.path.exists(reprocessed_error_path):
                    logger.info(f"Removing existing reprocessed error file: {reprocessed_error_path}")
                    os.remove(reprocessed_error_path)

        # Adjust output path if response is an error
        if not is_valid:
            if is_reprocessing:
                # If this is a reprocessing attempt that still produced an error,
                # use the reprocessed-error suffix to avoid picking it up again
                output_path = os.path.join(output_dir, f"{base_name}-reprocessed-error.json")
                logger.warning(f"Reprocessing still produced invalid response, saving as: {output_path}")
            else:
                output_path = os.path.join(output_dir, f"{base_name}-error.json")
                logger.warning(f"Invalid response schema detected, saving as error file: {output_path}")

        # Save response to output file
        logger.info(f"Saving results to {output_path}...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(response, f, indent=2)

        logger.info(f"Results saved to {output_path}")

        # Delete the file after successful processing
        logger.info(f"Deleting file {file_uri} from Gemini API...")
        if delete_file(api_key, file_uri, rate_limiter):
            logger.info(f"File {file_uri} deleted successfully")
        else:
            logger.warning(f"Failed to delete file {file_uri}")

        return True

    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Extract structured data from PDF files using Gemini API")
    parser.add_argument("--api-key", "-k", required=True, help="Gemini API key")
    parser.add_argument("--input", "-i", required=True, help="Path to input PDF file or directory of PDFs")
    parser.add_argument("--output", "-o", required=True, help="Path to output directory for JSON files")
    parser.add_argument("--model", "-m", default="gemini-2.0-flash",
                        help="Gemini model ID (default: gemini-2.0-flash)")
    parser.add_argument("--rpm", type=int, default=15, help="Requests per minute limit (default: 15)")
    parser.add_argument("--tpm", type=int, default=1000000, help="Tokens per minute limit (default: 1,000,000)")
    parser.add_argument("--rpd", type=int, default=1500, help="Requests per day limit (default: 1,500)")
    parser.add_argument("--log-file", "-l", default="pdf_extraction.log", help="Path to log file (default: pdf_extraction.log)")
    parser.add_argument("--csv-file", "-c", help="Path to CSV file with filename-URL mappings")
    parser.add_argument("--error", action="store_true", help="Only reprocess PDFs with error JSON files")

    args = parser.parse_args()

    # Initialize logger
    global logger
    logger = setup_logging(args.log_file)
    logger.info("Starting PDF extraction process")

    # Initialize rate limiter
    rate_limiter = RateLimiter(
        rpm_limit=args.rpm,
        tpm_limit=args.tpm,
        rpd_limit=args.rpd
    )

    # Load URL mappings if CSV file is provided
    url_map = {}
    if args.csv_file:
        if os.path.isfile(args.csv_file):
            url_map = load_url_mappings(args.csv_file)
        else:
            logger.error(f"CSV file {args.csv_file} does not exist")
            return 1

    try:
        # Ensure output directory exists
        os.makedirs(args.output, exist_ok=True)

        # Check if we're reprocessing only errored files
        if args.error:
            logger.info("Reprocessing only files with error JSON output")
            pdf_files = identify_errored_pdfs(args.input, args.output)
            if not pdf_files:
                logger.info("No errored files found to reprocess")
                return 0
            logger.info(f"Found {len(pdf_files)} errored files to reprocess")
        else:
            # Check if input is a file or directory
            if os.path.isfile(args.input):
                # Process single file
                pdf_files = [args.input]
            elif os.path.isdir(args.input):
                # Process all PDF files in directory
                pdf_files = glob.glob(os.path.join(args.input, "*.pdf"))
                if not pdf_files:
                    logger.error(f"No PDF files found in {args.input}")
                    return 1
                logger.info(f"Found {len(pdf_files)} PDF files to process")
            else:
                logger.error(f"Input path {args.input} does not exist")
                return 1

        # Process each PDF file
        success_count = 0
        for pdf_file in pdf_files:
            if process_pdf_file(args.api_key, pdf_file, args.output, args.model, rate_limiter, url_map, is_reprocessing=args.error):
                success_count += 1

        logger.info(f"Processing complete. {success_count}/{len(pdf_files)} files processed successfully.")
        return 0 if success_count == len(pdf_files) else 1

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
