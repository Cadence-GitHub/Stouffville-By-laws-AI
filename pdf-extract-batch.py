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
from collections import deque
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        "extractedText": {  "type": "array",  "items": {    "type": "string"  }},
        "legalTopics": {"type": "string"},
        "legislation": {"type": "string"},
        "otherBylaws": {"type": "string"},
        "condtionsAndClauses": {"type": "string"},
        "entitySigned": {"type": "string"},
        "otherEntitiesMentioned": {"type": "string"},
        "locationAddresses": {"type": "string"},
        "moneyAndCategories": {"type": "string"},
        "table": {  "type": "array",  "items": {    "type": "string"  }},
        "otherDetails": {"type": "string"}
      },
      "required": ["bylawNumber", "bylawYear", "extractedText"]
    }
    
    prompt = """For PDF file attached, produce a json file that has the below information:

Bylaw number
Bylaw year
Put each page text extracted PDF without hallucination into its own array
Canadian legal topics
Acts, Regulations with sections referenced or mentioned
Other bylaws mentioned
Conditions and clauses
Signing entity name
Other Entity names
Addresses or locations mentioned
Money and category (examples of category: expense/revenue/payment etc.)
Table: if you encounter tables, please provide them as an array
Other details that are deemed necessary"""
    
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
            "temperature": 0.1,
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

def process_pdf_file(api_key, pdf_path, output_dir, model="gemini-2.0-flash", rate_limiter=None):
    """Process a single PDF file and save the output JSON"""
    try:
        # Determine output filename
        pdf_name = os.path.basename(pdf_path)
        base_name = os.path.splitext(pdf_name)[0]
        output_path = os.path.join(output_dir, f"{base_name}.json")
        
        logger.info(f"Processing {pdf_name}...")
        
        # Upload file
        logger.info(f"Uploading {pdf_path}...")
        file_uri = upload_file(api_key, pdf_path, rate_limiter=rate_limiter)
        logger.info(f"File URI: {file_uri}")
        
        # Count tokens
        logger.info("Counting tokens...")
        token_count = count_tokens(api_key, file_uri, model, rate_limiter)
        logger.info(f"Token count: {token_count}")
        
        # Extract structured data
        logger.info(f"Extracting structured data with model {model}...")
        response = extract_structured_data(api_key, file_uri, model, rate_limiter, token_count)
        
        # Save response to output file
        logger.info(f"Saving results to {output_path}...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(response, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
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
    
    args = parser.parse_args()
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(
        rpm_limit=args.rpm,
        tpm_limit=args.tpm,
        rpd_limit=args.rpd
    )
    
    try:
        # Ensure output directory exists
        os.makedirs(args.output, exist_ok=True)
        
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
            if process_pdf_file(args.api_key, pdf_file, args.output, args.model, rate_limiter):
                success_count += 1
        
        logger.info(f"Processing complete. {success_count}/{len(pdf_files)} files processed successfully.")
        return 0 if success_count == len(pdf_files) else 1
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
