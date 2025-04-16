#!/usr/bin/env python3
"""
Incremental PDF Data Extraction with Gemini API

This script processes PDF files from a directory, extracting structured data for bylaw documents
in multiple incremental steps rather than a single large API call. This approach improves
reliability and allows for better handling of large documents.

Extraction Process:
1. First uploads and extracts raw text content from the PDF
2. Then makes individual API calls for each schema element using the extracted text 
3. Combines all elements into a final JSON output file

Features:
- Two-phase extraction for improved reliability with large documents
- Rate limiting to stay within Google API usage constraints
- URL mapping from CSV file to add source URLs to output
- Error handling with exponential backoff retry mechanism
- Field-specific prompts for targeted extraction
- Configurable output paths and model selection
- Detailed logging to both console and file
- Option to reprocess only previously failed documents

Usage:
    python IncrementalPDFExtraction.py --api-key YOUR_API_KEY --input pdf_folder --output json_folder

Required arguments:
    --api-key, -k    : Gemini API key
    --input, -i      : Path to input PDF file or directory of PDFs
    --output, -o     : Path to output directory for JSON files

Optional arguments:
    --model, -m      : Gemini model ID (default: gemini-2.0-flash)
    --rpm            : Requests per minute limit (default: 15)
    --tpm            : Tokens per minute limit (default: 1,000,000)
    --rpd            : Requests per day limit (default: 1,500)
    --log-file, -l   : Path to log file (default: pdf_extraction.log)
    --csv-file, -c   : Path to CSV file with filename-URL mappings
    --error          : Only reprocess PDFs with error JSON files

Output format:
    The script creates a JSON file for each PDF with the following schema elements:
    - bylawNumber        : Bylaw alphanumeric code
    - bylawYear          : Bylaw year
    - bylawType          : Type of bylaw based on code and content
    - bylawHeader        : Title or header of the document
    - extractedText      : Array of text content, one element per page
    - legalTopics        : Canadian legal topics covered
    - legislation        : Referenced acts and regulations
    - whyLegislation     : Explanation of legislation references
    - otherBylaws        : Other bylaws referenced
    - whyOtherBylaws     : Explanation of other bylaw references
    - condtionsAndClauses: Conditions and clauses in the bylaw
    - entityAndDesignation: Signing entities and their roles
    - otherEntitiesMentioned: Other entities mentioned
    - locationAddresses  : Addresses or locations mentioned
    - moneyAndCategories : Money amounts and their categories
    - table              : Table content converted to text
    - keywords           : Key legal terms for search
    - keyDatesAndInfo    : Important dates and related information
    - otherDetails       : Additional relevant details
    - newsSources        : Referenced news sources
    - hasEmbeddedImages  : Boolean indicating if images are present
    - imageDesciption    : Descriptions of embedded images
    - hasEmbeddedMaps    : Boolean indicating if maps are present
    - mapDescription     : Descriptions of embedded maps
    - laymanExplanation  : Simplified explanation of the bylaw
    - urlOriginalDocument: URL to the original document
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
    """
    Set up logging to both console and file with proper formatting.
    
    This function configures a logger that outputs messages to both a file
    and the console, making it easier to track the script's progress and
    diagnose issues both in real-time and after execution.
    
    Args:
        log_file_path (str): Path where the log file will be saved
        
    Returns:
        logging.Logger: Configured logger object ready for use
        
    Note:
        The log format includes timestamp, log level, and message for both outputs.
        The default logging level is set to INFO.
    """
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # If logger already has handlers, clear them to avoid duplicate messages
    if logger.handlers:
        logger.handlers.clear()

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
    
    This function scans the output directory for files ending with "-error.json", which
    indicate previously failed processing attempts. It then finds the corresponding PDF 
    files in the input directory for reprocessing. To prevent infinite loops, it ignores
    files ending with "-reprocessed-error.json", which indicate previously failed 
    reprocessing attempts.
    
    Args:
        input_dir (str): Directory containing the original PDF files
        output_dir (str): Directory containing JSON output files and error files
        
    Returns:
        list: Absolute paths to PDF files that need to be reprocessed
        
    Note:
        If a PDF has an error file but the original PDF no longer exists in the input
        directory, a warning will be logged but execution will continue.
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
    """
    Load URL mappings from a CSV file to associate PDFs with their source URLs.
    
    This function reads a CSV file containing mappings between PDF filenames and 
    their source URLs. These URLs will be included in the final JSON output under
    the 'urlOriginalDocument' field.
    
    Args:
        csv_path (str): Path to the CSV file with filename-URL mappings
        
    Returns:
        dict: Dictionary mapping PDF filenames (keys) to URLs (values)
        
    Notes:
        - Expected CSV format: two columns with optional header
        - If header is present, it should have "File Name" and "URL" as column names
        - If no header is present, the first row is treated as data
        - Returns empty dict if csv_path is None or if file reading fails
        - UTF-8 encoding is assumed for the CSV file
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
    """
    Tracks and enforces Gemini API rate limits to prevent quota overruns.
    
    This class implements a rate limiting mechanism that tracks API usage across
    three dimensions:
    1. Requests per minute (RPM)
    2. Tokens per minute (TPM)
    3. Requests per day (RPD)
    
    When any limit is approached, the class will automatically pause execution
    with appropriate wait times to ensure API quota compliance.
    
    Attributes:
        rpm_limit (int): Maximum requests per minute allowed
        tpm_limit (int): Maximum tokens per minute allowed
        rpd_limit (int): Maximum requests per day allowed
        request_timestamps_minute (deque): Rolling window of request timestamps (minute)
        request_timestamps_day (deque): Rolling window of request timestamps (day)
        token_usage_minute (deque): Rolling window of token usage with timestamps
        day_start (datetime): Starting timestamp for the current day
    """

    def __init__(self, rpm_limit=15, tpm_limit=1000000, rpd_limit=1500):
        """
        Initialize the rate limiter with configurable limits.
        
        Args:
            rpm_limit (int, optional): Requests per minute limit. Defaults to 15.
            tpm_limit (int, optional): Tokens per minute limit. Defaults to 1,000,000.
            rpd_limit (int, optional): Requests per day limit. Defaults to 1,500.
        """
        self.rpm_limit = rpm_limit  # Requests per minute
        self.tpm_limit = tpm_limit  # Tokens per minute
        self.rpd_limit = rpd_limit  # Requests per day

        # Tracking request timestamps using double-ended queues for efficient
        # addition/removal as the time windows roll
        self.request_timestamps_minute = deque()
        self.request_timestamps_day = deque()

        # Tracking token usage (last 60 seconds)
        self.token_usage_minute = deque()

        # Store the first day's timestamp for RPD counting
        self.day_start = datetime.datetime.now()

    def _clean_old_entries(self):
        """
        Remove tracking entries that have fallen outside the relevant time windows.
        
        This method maintains the rate limiting queues by removing expired entries:
        - For RPM and TPM: Entries older than 1 minute
        - For RPD: Entries older than 1 day or reset if date has changed
        
        This ensures that rate calculations are always based on the most recent
        relevant time window.
        """
        now = datetime.datetime.now()

        # Clean minute tracking (RPM, TPM)
        minute_ago = now - datetime.timedelta(minutes=1)
        # Remove requests older than 1 minute from RPM tracking
        while self.request_timestamps_minute and self.request_timestamps_minute[0] < minute_ago:
            self.request_timestamps_minute.popleft()

        # Remove token usage older than 1 minute from TPM tracking
        while self.token_usage_minute and self.token_usage_minute[0][0] < minute_ago:
            self.token_usage_minute.popleft()

        # Clean day tracking (RPD)
        # If the date has changed, completely reset the day counter
        if (now.date() > self.day_start.date()):
            self.request_timestamps_day.clear()
            self.day_start = now

        # Remove requests older than 24 hours from RPD tracking
        day_ago = now - datetime.timedelta(days=1)
        while self.request_timestamps_day and self.request_timestamps_day[0] < day_ago:
            self.request_timestamps_day.popleft()

    def check_limits(self):
        """
        Check if we're within all rate limits and get current usage statistics.
        
        This method calculates the current usage across all three rate limiting
        dimensions (RPM, TPM, RPD) and determines if any limit has been exceeded.
        
        Returns:
            tuple: (is_allowed, limits_info)
                - is_allowed (bool): True if all limits are respected, False otherwise
                - limits_info (dict): Dictionary containing detailed usage information
                  for each rate limit type, with the following structure:
                  {
                    "rpm": {"current": int, "limit": int, "exceeded": bool},
                    "rpd": {"current": int, "limit": int, "exceeded": bool},
                    "tpm": {"current": int, "limit": int, "exceeded": bool}
                  }
        """
        # First clean out old entries to ensure accurate calculations
        self._clean_old_entries()

        # Calculate current usage for each limit type
        rpm_current = len(self.request_timestamps_minute)
        rpd_current = len(self.request_timestamps_day)
        tpm_current = sum(tokens for _, tokens in self.token_usage_minute)

        # Check if any limit is exceeded
        is_rpm_exceeded = rpm_current >= self.rpm_limit
        is_rpd_exceeded = rpd_current >= self.rpd_limit
        is_tpm_exceeded = tpm_current >= self.tpm_limit

        # Build detailed information dictionary for reporting
        limits_info = {
            "rpm": {"current": rpm_current, "limit": self.rpm_limit, "exceeded": is_rpm_exceeded},
            "rpd": {"current": rpd_current, "limit": self.rpd_limit, "exceeded": is_rpd_exceeded},
            "tpm": {"current": tpm_current, "limit": self.tpm_limit, "exceeded": is_tpm_exceeded},
        }

        # Request is allowed only if none of the limits are exceeded
        is_allowed = not (is_rpm_exceeded or is_rpd_exceeded or is_tpm_exceeded)

        return is_allowed, limits_info

    def wait_if_needed(self):
        """
        Pause execution if any rate limit has been reached.
        
        This method checks if the API usage is within allowed limits, and if not,
        it pauses execution for an appropriate amount of time. The wait time is
        calculated dynamically based on which limits were exceeded and how long
        until enough capacity becomes available again.
        
        For RPM and TPM limits, it waits until the oldest request/tokens fall out of
        the 1-minute window. For RPD limit, it waits until midnight when the daily
        counter resets.
        
        Note:
            - Maximum wait time is capped at 60 seconds for RPM/TPM limits
            - For RPD limit, it may wait until midnight
            - A small buffer (1 second) is added to ensure limits are truly reset
        """
        while True:
            # Check current limit status
            is_allowed, limits_info = self.check_limits()
            if is_allowed:
                # If we're within limits, proceed immediately
                break

            # Determine wait time based on which limit was hit
            wait_time = 5  # Default 5 seconds minimum wait

            if limits_info["rpm"]["exceeded"]:
                # For RPM: Wait until oldest request falls out of the 1-minute window
                oldest = self.request_timestamps_minute[0]
                # Calculate seconds until this request is 1 minute old
                rpm_wait = (oldest + datetime.timedelta(minutes=1) - datetime.datetime.now()).total_seconds()
                wait_time = max(wait_time, rpm_wait)
                logger.warning(f"RPM limit reached ({limits_info['rpm']['current']}/{self.rpm_limit}). Waiting {wait_time:.1f} seconds.")

            if limits_info["tpm"]["exceeded"]:
                # For TPM: Wait until oldest token usage falls out of the 1-minute window
                oldest, _ = self.token_usage_minute[0]
                # Calculate seconds until this token usage is 1 minute old
                tpm_wait = (oldest + datetime.timedelta(minutes=1) - datetime.datetime.now()).total_seconds()
                wait_time = max(wait_time, tpm_wait)
                logger.warning(f"TPM limit reached ({limits_info['tpm']['current']}/{self.tpm_limit}). Waiting {wait_time:.1f} seconds.")

            if limits_info["rpd"]["exceeded"]:
                # For RPD: Wait until midnight when the daily counter resets
                tomorrow = datetime.datetime.now().replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
                wait_time = max(wait_time, (tomorrow - datetime.datetime.now()).total_seconds())
                logger.warning(f"RPD limit reached ({limits_info['rpd']['current']}/{self.rpd_limit}). Daily limit reached, waiting until midnight.")

            # Add a small buffer and cap the maximum wait (except for RPD)
            if limits_info["rpd"]["exceeded"]:
                # For RPD we might need to wait until midnight, so don't cap
                wait_time += 1
            else:
                # For RPM/TPM, add buffer and cap at 60 seconds
                wait_time = min(wait_time + 1, 60)

            logger.info(f"Rate limited. Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)

    def record_request(self, token_count=0):
        """
        Record a completed API request with optional token usage.
        
        This method should be called after each successful API request to track
        usage for rate limiting purposes. If the request involved token consumption
        (like generating content), the token count should be provided.
        
        Args:
            token_count (int, optional): Number of tokens used in this request.
                                        Defaults to 0 for requests that don't use tokens.
        """
        now = datetime.datetime.now()
        # Add timestamp to both minute and day tracking
        self.request_timestamps_minute.append(now)
        self.request_timestamps_day.append(now)

        # Only track token usage if tokens were actually used
        if token_count > 0:
            self.token_usage_minute.append((now, token_count))

def upload_file(api_key, pdf_path, display_name=None, rate_limiter=None):
    """
    Upload a PDF file to Gemini API using the resumable upload protocol.
    
    This function handles the upload of PDF files to the Gemini API using Google's
    resumable upload protocol, which is more reliable for larger files. The upload
    happens in two steps:
    1. Initiate the upload and get an upload URL
    2. Upload the actual file content to that URL
    
    Args:
        api_key (str): Gemini API key
        pdf_path (str): Path to the PDF file to upload
        display_name (str, optional): Name to assign to the file. 
                                     Defaults to the filename without extension.
        rate_limiter (RateLimiter, optional): Rate limiter object to track API usage.
                                             Defaults to None.
    
    Returns:
        str: File URI that can be used to reference the uploaded file in future API calls
    
    Raises:
        ValueError: If unable to get upload URL or file URI
        requests.RequestException: If HTTP requests fail after retries
    """

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
    """
    Delete a previously uploaded file from Gemini API.
    
    This function removes a file that was uploaded to the Gemini API to free up 
    storage. It's important to delete files after processing to avoid accumulating
    unused files in your account.
    
    Args:
        api_key (str): Gemini API key
        file_uri (str): URI of the file to delete (from upload_file function)
        rate_limiter (RateLimiter, optional): Rate limiter object to track API usage.
                                             Defaults to None.
    
    Returns:
        bool: True if deletion was successful, False otherwise
    
    Note:
        The function extracts the file name from the URI and uses it to construct
        the deletion URL. If the URI format is invalid, it will log an error and
        return False.
    """

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
    """
    Count the number of tokens in a PDF file to estimate API usage.
    
    This function uses the Gemini API's countTokens endpoint to determine how many
    tokens would be consumed when processing the PDF. This helps with:
    1. Rate limiting for token-based quotas
    2. Detecting PDFs that are too large to process efficiently
    3. Planning API usage and estimating costs
    
    Args:
        api_key (str): Gemini API key
        file_uri (str): URI of the uploaded PDF file
        model (str, optional): Gemini model ID to use for counting. 
                              Defaults to "gemini-2.0-flash".
        rate_limiter (RateLimiter, optional): Rate limiter object to track API usage.
                                             Defaults to None.
    
    Returns:
        int: Number of tokens in the PDF file
    
    Raises:
        requests.RequestException: If HTTP request fails after retries
        ValueError: If response cannot be parsed
    """

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

def extract_text_only(api_key, file_uri, model="gemini-2.5-pro-exp-03-25", rate_limiter=None):
    """
    Extract only the text content from a PDF file as the first extraction step.
    
    This function focuses solely on extracting the raw text content from the PDF,
    organized page by page. This is the first phase of the incremental extraction
    process. The extracted text will be used as input for subsequent field-specific
    extraction steps rather than repeatedly sending the full PDF.
    
    Args:
        api_key (str): Gemini API key
        file_uri (str): URI of the uploaded PDF file
        model (str, optional): Gemini model ID to use for extraction.
                              Defaults to "gemini-2.0-flash".
        rate_limiter (RateLimiter, optional): Rate limiter object to track API usage.
                                             Defaults to None.
    
    Returns:
        list: List of strings where each element contains the text from one page of the PDF
    
    Raises:
        requests.RequestException: If HTTP request fails after retries
        ValueError: If response cannot be parsed
        
    Note:
        The function uses a simplified schema that only requests the extractedText field,
        which helps improve reliability for large documents.
    """
    if rate_limiter:
        rate_limiter.wait_if_needed()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    # Text extraction schema
    schema = {
        "type": "object",
        "properties": {
            "extractedText": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["extractedText"]
    }

    prompt = """You are a fantastic parser of legal documents. You excel at reasoning while parsing and extracting. You follow instructions like a robot. You will validate the json produced against the PDF and the instructions provided before responding. For PDF file attached, produce a json file that has the below information. AVOID: Trying to cram in entire decoded image in the extractedText. AVOID: printing or repeating newline characters \\n or dashes beyond what was requested - that breaches your output tokens in the json.:
{
  "extractedText": ["page 1 text...", "page 2 text...", "..."]
}

Put each page text extract from PDF without hallucination into its own array index. Separate paragraphs using 3 newline characters. Each page should be its own element in the array."""

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
            "temperature": 0.2,
            "responseSchema": schema,
            "responseMimeType": "application/json"
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

            # Record the request if rate limiter is provided
            if rate_limiter:
                rate_limiter.record_request()

            result = response.json()

            # Extract text from the response
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
                                parsed_json = json.loads(json_str)
                                if "extractedText" in parsed_json:
                                    return parsed_json["extractedText"]
                        except json.JSONDecodeError:
                            pass

            # If we couldn't parse JSON, return the raw text
            logger.warning("Could not parse JSON from text extraction response")
            return []

        except (requests.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Text extraction request failed: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Text extraction request failed after {max_retries} attempts: {str(e)}")
                raise

def extract_field(api_key, field_name, field_type, extracted_text, model="gemini-2.0-flash", rate_limiter=None):
    """
    Extract a specific field from the previously extracted text content.
    
    This function represents the second phase of incremental extraction, where
    individual fields are extracted one at a time from the text content rather
    than from the original PDF. Each field uses a targeted schema and prompt.
    
    Args:
        api_key (str): Gemini API key
        field_name (str): Name of the field to extract (must match schema)
        field_type (str): Type of the field - must be one of:
                         - "string": For text fields
                         - "array": For list fields
                         - "boolean": For true/false fields
        extracted_text (list): List of text content by page (from extract_text_only)
        model (str, optional): Gemini model ID to use for extraction.
                              Defaults to "gemini-2.0-flash".
        rate_limiter (RateLimiter, optional): Rate limiter object to track API usage.
                                             Defaults to None.
    
    Returns:
        Various: The extracted field value with the appropriate type:
                - str for field_type="string"
                - list for field_type="array"
                - bool for field_type="boolean"
    
    Raises:
        ValueError: For unsupported field types or if JSON cannot be parsed
        requests.RequestException: If HTTP request fails after retries
        
    Note:
        On error, the function returns appropriate empty values for each type
        (empty string, empty list, or False) rather than raising an exception.
    """
    if rate_limiter:
        rate_limiter.wait_if_needed()

#    if field_name == "table":
#        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-exp-03-25 :generateContent?key={api_key}"
#    else:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"


    headers = {
        "Content-Type": "application/json"
    }

    # Turn extracted text into a single string for the prompt
    text_content = "\n\n".join(extracted_text)
    
    # Field-specific schema
    if field_type == "string":
        schema = {
            "type": "object",
            "properties": {
                field_name: {"type": "string"}
            },
            "required": [field_name]
        }
    elif field_type == "array":
        schema = {
            "type": "object",
            "properties": {
                field_name: {"type": "array", "items": {"type": "string"}}
            },
            "required": [field_name]
        }
    elif field_type == "boolean":
        schema = {
            "type": "object",
            "properties": {
                field_name: {"type": "boolean"}
            },
            "required": [field_name]
        }
    else:
        raise ValueError(f"Unsupported field type: {field_type}")

    # Field-specific prompt
    prompt = get_field_prompt(field_name, field_type, text_content)

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "responseSchema": schema,
            "responseMimeType": "application/json"
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

            # Record the request if rate limiter is provided
            if rate_limiter:
                rate_limiter.record_request()

            result = response.json()

            # Extract field value from the response
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
                                parsed_json = json.loads(json_str)
                                if field_name in parsed_json:
                                    return parsed_json[field_name]
                        except json.JSONDecodeError:
                            pass

            # If we couldn't parse JSON, return a default value
            logger.warning(f"Could not parse JSON for field {field_name}")
            if field_type == "string":
                return ""
            elif field_type == "array":
                return []
            elif field_type == "boolean":
                return False

        except (requests.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Field extraction request for {field_name} failed: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Field extraction request for {field_name} failed after {max_retries} attempts: {str(e)}")
                if field_type == "string":
                    return ""
                elif field_type == "array":
                    return []
                elif field_type == "boolean":
                    return False

def get_field_prompt(field_name, field_type, text_content):
    """
    Generate a field-specific prompt for targeted extraction.
    
    This function creates customized prompts for each field to be extracted,
    tailoring the instructions based on the field's purpose and expected content.
    Using field-specific prompts improves extraction accuracy and relevance.
    
    Args:
        field_name (str): Name of the field to extract
        field_type (str): Type of the field (string, array, boolean)
        text_content (str): The combined text content from the PDF
    
    Returns:
        str: A complete prompt string ready to be sent to the API
        
    Note:
        The function contains a dictionary of field-specific instructions that
        provide detailed guidance on how to extract each particular field. If
        a field is not in this dictionary, a generic extraction prompt is used.
    """
    # Define field-specific prompts based on the field name
    field_prompts = {
        "bylawNumber": "Extract the bylaw alphanumeric code from the text.",
        "bylawYear": "Extract the bylaw year from the text.",
        "bylawType": "Analyze the bylaw number and content to determine the type. Bylaws are numbered in a unique way. Ending with ZO could be zoning order, AP could be appointment, FI could be financial. Use your reasoning skills to define the type. Do not abbreviate.",
        "bylawHeader": "Extract the bolded text at the top of the document that forms part of the contiguous text that follows.",
        "legalTopics": "Identify all Canadian legal topics mentioned in the text.",
        "legislation": "Extract all Acts, Regulations with sections referenced or mentioned. If nothing is found say None.",
        "whyLegislation": "If acts or regulation are mentioned, explain why they are mentioned and their significance. Detail for each mentioned. Separate by pipe symbol.",
        "otherBylaws": "Identify other bylaws mentioned in the text. If nothing is found say None.",
        "whyOtherBylaws": "If other bylaws are mentioned, explain why they are mentioned and their significance. Detail for each bylaw mentioned. Separate by pipe symbol.",
        "condtionsAndClauses": "Extract conditions and clauses from the text. If nothing is found say None.",
        "entityAndDesignation": "Identify signing entity (people or person) names and their designations.",
        "otherEntitiesMentioned": "Identify other entity (people, person, institutions, companies) names mentioned. If nothing is found say None.",
        "locationAddresses": "Extract all addresses or locations mentioned. If nothing is found say None.",
        "moneyAndCategories": "Extract money amounts and their categories (examples: expense/revenue/payment). If nothing is found say None.",
        "table": "Extract any tables in the text. Separate columns using pipe symbol. If nothing is found return an empty array.",
        "keywords": "Extract a lexicon of legal keywords from the text for search purposes.",
        "keyDatesAndInfo": "Extract key dates (in DD-MMM-YYYY format) and information for each date mentioned. If nothing is found say None.",
        "otherDetails": "Extract any other important details from the text. If nothing is found say None.",
        "newsSources": "Identify any news sources mentioned, detailing why and what for each.",
        "hasEmbeddedImages": "Determine if there are embedded images mentioned in the text (true/false).",
        "imageDesciption": "If there are images, describe each image in detail. If there are multiple images, title them and describe them individually.",
        "hasEmbeddedMaps": "Determine if there are embedded maps mentioned in the text (true/false).",
        "mapDescription": "If there are maps, describe each map in detail. If there are multiple maps, title them and describe them individually.",
        "laymanExplanation": "Provide a plain simple English version of the bylaw so that a layman can understand. Be precise and accurate.",
        "urlOriginalDocument": "This field should be empty. Return an empty string."
    }
    
    # Get the specific prompt for this field, or use a generic one if not found
    specific_prompt = field_prompts.get(field_name, f"Extract the {field_name} from the text.")
    
    # Base prompt structure
    base_prompt = f"""You are a fantastic parser of legal documents. You excel at reasoning while parsing and extracting. You follow instructions like a robot. AVOID: Trying to cram in entire decoded image in the extractedText. AVOID: printing or repeating newline characters \\n or dashes beyond what was requested - that breaches your output tokens in the json. Based on the following OCR'd text (so there may be transcription errors) from a bylaw document, extract the {field_name}.

{specific_prompt}

Provide your response in JSON format like this:
{{
  "{field_name}": "value"
}}
"""
    
    # For array types, adjust the example format
    if field_type == "array":
        base_prompt = base_prompt.replace('"value"', '["value1", "value2", ...]')
    
    # For boolean types, adjust the example format
    elif field_type == "boolean":
        base_prompt = base_prompt.replace('"value"', 'true or false')
    
    # Add the text content to the prompt (truncate if too long)
    max_length = 5000000  # Reasonable limit for prompt size
    if len(text_content) > max_length:
        text_snippet = text_content[:max_length] + "... [text truncated]"
        base_prompt += f"\n\nDocument text (truncated):\n{text_snippet}"
    else:
        base_prompt += f"\n\nDocument text:\n{text_content}"
    
    return base_prompt

def validate_json_schema(data):
    """
    Validate if the aggregated JSON response has the expected structure.
    
    This function checks if the combined JSON data from all extraction steps
    contains most of the expected fields for a valid bylaw document. It uses
    a threshold-based approach where at least 70% of expected fields must be
    present for the response to be considered valid.
    
    Args:
        data (dict): The complete JSON data to validate
        
    Returns:
        bool: True if the data structure is valid, False otherwise
        
    Notes:
        - The function detects error responses that may have "candidates" at the top level
        - A 70% field presence threshold is used to accommodate some variation
        - The validation logs warnings with specific details about invalid responses
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
    """
    Process a single PDF file using the incremental extraction approach.
    
    This function handles the complete processing of a PDF file through these steps:
    1. Upload the PDF to the Gemini API
    2. Count tokens to check if processing is feasible
    3. Extract text content from the PDF
    4. Extract each individual field using the text content
    5. Combine all extracted fields into a single JSON result
    6. Add URL information from mapping if available
    7. Validate the final JSON structure
    8. Save the result to the appropriate output file
    9. Delete the uploaded PDF from the API
    
    Args:
        api_key (str): Gemini API key
        pdf_path (str): Path to the PDF file to process
        output_dir (str): Directory to save output JSON files
        model (str, optional): Gemini model ID to use. Defaults to "gemini-2.0-flash".
        rate_limiter (RateLimiter, optional): Rate limiter object. Defaults to None.
        url_map (dict, optional): Mapping of PDF filenames to URLs. Defaults to None.
        is_reprocessing (bool, optional): Whether this is a reprocessing attempt for
                                         a previously failed PDF. Defaults to False.
    
    Returns:
        bool: True if processing was successful, False otherwise
        
    Note:
        The function handles error cases by creating files with "-error.json" or
        "-reprocessed-error.json" suffixes to indicate failures.
    """
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
            logger.info(f"Large token detected ({token_count}). This may require more time to process.")

        # First, extract just the text
        logger.info("Extracting text content...")
        extracted_text = extract_text_only(api_key, file_uri, "gemini-2.5-pro-exp-03-25", rate_limiter)
        if not extracted_text:
            logger.error("Failed to extract text from the PDF")
            # Save error and return
            error_data = {"error": "Failed to extract text from the PDF", "file": pdf_name}
            with open(error_output_path, "w") as f:
                json.dump(error_data, f, indent=2)
            return False

        # Define the fields to extract with their types
        fields_to_extract = {
            "bylawNumber": "string",
            "bylawYear": "string",
            "bylawType": "string",
            "bylawHeader": "string",
            "legalTopics": "array",
            "legislation": "array",
            "whyLegislation": "array",
            "otherBylaws": "array",
            "whyOtherBylaws": "array",
            "condtionsAndClauses": "string",
            "entityAndDesignation": "array",
            "otherEntitiesMentioned": "array",
            "locationAddresses": "array",
            "moneyAndCategories": "array",
            "table": "array",
            "keywords": "array",
            "keyDatesAndInfo": "array",
            "otherDetails": "string",
            "newsSources": "array",
            "hasEmbeddedImages": "boolean",
            "imageDesciption": "array",
            "hasEmbeddedMaps": "boolean",
            "mapDescription": "array",
            "laymanExplanation": "string",
            "urlOriginalDocument": "string"
        }

        # Initialize result with extracted text
        result = {"extractedText": extracted_text}

        # Extract each field one by one
        for field_name, field_type in fields_to_extract.items():
            if field_name == "extractedText":  # Already extracted
                continue
                
            logger.info(f"Extracting field: {field_name}...")
            try:
                field_value = extract_field(api_key, field_name, field_type, extracted_text, model, rate_limiter)
                result[field_name] = field_value
                logger.info(f"Field {field_name} extracted successfully")
            except Exception as e:
                logger.error(f"Error extracting field {field_name}: {str(e)}")
                # Use empty default value for this field
                if field_type == "string":
                    result[field_name] = ""
                elif field_type == "array":
                    result[field_name] = []
                elif field_type == "boolean":
                    result[field_name] = False

        # Add URL to response if URL mapping is available
        if url_map:
            # Look up URL by PDF filename
            if pdf_name in url_map:
                # Add the URL to the JSON response
                result['urlOriginalDocument'] = url_map[pdf_name]
                logger.info(f"Added URL for {pdf_name}: {url_map[pdf_name]}")
            else:
                logger.warning(f"No URL found for {pdf_name}")

        # Validate the final JSON
        is_valid = validate_json_schema(result)

        # If reprocessing, handle error files
        if is_reprocessing and is_valid and os.path.exists(error_output_path):
            logger.info(f"Removing existing error file: {error_output_path}")
            os.remove(error_output_path)

            # Also remove any previous reprocessed error file if it exists
            if os.path.exists(reprocessed_error_path):
                logger.info(f"Removing existing reprocessed error file: {reprocessed_error_path}")
                os.remove(reprocessed_error_path)

        # Adjust output path if response is invalid
        if not is_valid:
            if is_reprocessing:
                # If this is a reprocessing attempt that still produced an error,
                # use the reprocessed-error suffix to avoid picking it up again
                output_path = reprocessed_error_path
                logger.warning(f"Reprocessing still produced invalid response, saving as: {output_path}")
            else:
                output_path = error_output_path
                logger.warning(f"Invalid response schema detected, saving as error file: {output_path}")

        # Save response to output file
        logger.info(f"Saving results to {output_path}...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

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
    """
    Main entry point for the PDF extraction script.
    
    This function handles command-line argument parsing, initializes logging and rate
    limiting, identifies PDFs to process, and coordinates the processing. It also
    tracks overall success/failure counts and sets the appropriate exit code.
    
    Command-line arguments:
        --api-key, -k   : (Required) Gemini API key
        --input, -i     : (Required) Path to input PDF file or directory
        --output, -o    : (Required) Path to output directory for JSON files
        --model, -m     : Gemini model ID (default: gemini-2.0-flash)
        --rpm           : Requests per minute limit (default: 15)
        --tpm           : Tokens per minute limit (default: 1,000,000)
        --rpd           : Requests per day limit (default: 1,500)
        --log-file, -l  : Path to log file (default: pdf_extraction.log)
        --csv-file, -c  : Path to CSV file with filename-URL mappings
        --error         : Only reprocess PDFs with error JSON files
    
    Returns:
        int: Exit code (0 for complete success, 1 if any PDFs failed)
    """
    # Set up command-line argument parser
    parser = argparse.ArgumentParser(
        description="Extract structured data from PDF files using Gemini API in multiple incremental steps",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter  # Shows defaults in help text
    )
    
    # Required arguments
    parser.add_argument("--api-key", "-k", required=True, 
                       help="Gemini API key")
    parser.add_argument("--input", "-i", required=True, 
                       help="Path to input PDF file or directory of PDFs")
    parser.add_argument("--output", "-o", required=True, 
                       help="Path to output directory for JSON files")
    
    # Optional arguments with defaults
    parser.add_argument("--model", "-m", default="gemini-2.0-flash",
                       help="Gemini model ID")
    parser.add_argument("--rpm", type=int, default=15, 
                       help="Requests per minute limit")
    parser.add_argument("--tpm", type=int, default=1000000, 
                       help="Tokens per minute limit")
    parser.add_argument("--rpd", type=int, default=1500, 
                       help="Requests per day limit")
    parser.add_argument("--log-file", "-l", default="pdf_extraction.log", 
                       help="Path to log file")
    
    # Optional arguments without defaults
    parser.add_argument("--csv-file", "-c", 
                       help="Path to CSV file with filename-URL mappings")
    
    # Flag arguments
    parser.add_argument("--error", action="store_true", 
                       help="Only reprocess PDFs with error JSON files")

    args = parser.parse_args()

    # Initialize logger
    global logger
    logger = setup_logging(args.log_file)
    logger.info("Starting incremental PDF extraction process")

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
