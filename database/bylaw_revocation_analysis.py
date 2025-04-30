#!/usr/bin/env python3
"""
Bylaw Revocation Analyzer

This script analyzes JSON bylaw data to identify bylaws that revoke other bylaws.
It uses Gemini API via Langchain to analyze the extracted text and identify revocation information.

The script reads bylaws from an input JSON file, checks for revocation information,
and updates the status of revoked bylaws.
"""

import os
import json
import argparse
import logging
import time
import signal
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bylaw_revocation_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flag to track if the program should terminate
terminate = False

# Signal handler for graceful termination
def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) by setting the terminate flag and logging."""
    global terminate
    logger.info("Received termination signal. Finishing current task and exiting gracefully...")
    terminate = True

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# Define the prompt template for checking if a bylaw revokes other bylaws
REVOCATION_CHECK_PROMPT = ChatPromptTemplate.from_template("""
You are a legal expert in Canadian municipal bylaws. Your task is to analyze the text of a bylaw
and determine if it fully revokes, repeals, or replaces any previous bylaws.

Here is the bylaw text to analyze:
<bylaw_text>
{bylaw_text}
</bylaw_text>

Bylaw number: {bylaw_number}
Bylaw year: {bylaw_year}
Bylaw type: {bylaw_type}

IMPORTANT DISTINCTION:
- You should ONLY identify bylaws that are COMPLETELY revoked, repealed, or replaced
- Do NOT include bylaws that are merely amended, partially modified, or have specific sections/provisions changed
- Amendments, even substantial ones, do not count as full revocations

Carefully search for language indicating that this bylaw completely revokes, repeals, or replaces previous bylaws. Look for phrases like:
- "This by-law repeals by-law number X"
- "By-law X is hereby repealed"
- "By-law X is rescinded in its entirety"
- "This by-law replaces by-law X in its entirety"

Ignore language that indicates only partial amendments such as:
- "By-law X is hereby amended by..."
- "Section Y of By-law X is repealed"
- "By-law X is amended by adding/deleting/substituting..."

If the bylaw fully revokes multiple bylaws, identify all of them.

IMPORTANT: When you identify a revoked bylaw number, you MUST convert it to the standard format: YYYY-NNN where:
- YYYY is the 4-digit year 
- NNN is a 3-digit number padded with leading zeros if needed

Examples of correct formatting:
- Bylaw 71-55 should be formatted as 1971-055
- Bylaw 83-114 should be formatted as 1983-114
- Bylaw 5-16 should be formatted as 2005-016 (assuming it's from the 2000s)
- Bylaw 45-002 should be formatted as 1945-002

For bylaws with only two digits for the year (e.g., "71-55"):
- If the two digits are 30-99, assume they are from the 1900s (e.g., 71 → 1971)
- If the two digits are 00-29, assume they are from the 2000s (e.g., 05 → 2005)

Respond with ONLY a JSON object in the following format:

If the bylaw fully revokes other bylaws:
{{
  "revokesOtherBylaws": true,
  "revokedBylaws": [
    {{
      "bylawNumber": "YYYY-NNN",
      "revocationReason": "Concise description of why/how this bylaw was revoked (e.g., 'Fully repealed', 'Completely replaced', 'Entirely rescinded')"
    }},
    {{
      "bylawNumber": "YYYY-NNN",
      "revocationReason": "Concise description of why/how this bylaw was revoked (e.g., 'Fully repealed', 'Completely replaced', 'Entirely rescinded')"
    }}
  ]
}}

If the bylaw does not fully revoke any other bylaws (including if it only amends them):
{{
  "revokesOtherBylaws": false,
  "revokedBylaws": []
}}

Remember: ALL bylaw numbers in your response MUST be in the YYYY-NNN format. This is critical for the system to find the referenced bylaws.
""")

def load_json_file(file_path):
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return []
    except FileNotFoundError:
        logger.info(f"File not found: {file_path}, will create it if needed")
        return []

def get_processed_bylaws(processed_file):
    """
    Get a set of bylaw numbers that have already been processed for revocation.
    
    Args:
        processed_file: Path to the processed bylaws file
        
    Returns:
        set: Set of processed bylaw numbers
    """
    processed = set()
    
    # Check processed bylaws file
    if os.path.exists(processed_file):
        processed_bylaws = load_json_file(processed_file)
        for bylaw in processed_bylaws:
            if 'bylawNumber' in bylaw:
                processed.add(bylaw['bylawNumber'])
    
    return processed

def append_to_json_file(file_path, data):
    """
    Append data to a JSON file. If the file doesn't exist, create it with the data.
    If it exists, read it, append the data, and write it back.
    
    Args:
        file_path: Path to the JSON file
        data: Data to append to the file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # If file exists, read existing data
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                
            # If it's not a list, make it one
            if not isinstance(existing_data, list):
                existing_data = [existing_data]
                
            # Append new data
            existing_data.append(data)
            file_data = existing_data
        else:
            # Create new file with data in a list
            file_data = [data]
        
        # Write the data back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)
            
        return True
    except Exception as e:
        logger.error(f"Error appending to file {file_path}: {e}")
        return False

def clean_llm_response(response):
    """
    Clean LLM response by removing code block markers before parsing JSON.
    
    Args:
        response (str): The raw response from the LLM
        
    Returns:
        str: Cleaned response without markdown code block formatting
    """
    # Remove ```json at the beginning if present
    if response.strip().startswith("```json"):
        response = response.strip()[7:]
    elif response.strip().startswith("```"):
        response = response.strip()[3:]
        
    # Remove ``` at the end if present
    if response.strip().endswith("```"):
        response = response.strip()[:-3]
    
    return response.strip()

def find_bylaw_by_number(bylaws, bylaw_number):
    """
    Find a bylaw in the list by its bylaw number.
    
    Args:
        bylaws: List of bylaw data
        bylaw_number: Bylaw number to find (should be in YYYY-NNN format)
        
    Returns:
        dict or None: The bylaw data if found, None otherwise
    """
    for bylaw in bylaws:
        if bylaw.get("bylawNumber") == bylaw_number:
            return bylaw
    return None

def analyze_bylaw_revocation(bylaw, model_name, api_key):
    """
    Analyze a bylaw to determine if it revokes other bylaws using Gemini API.
    
    Args:
        bylaw: JSON bylaw data
        model_name: Name of the Gemini model to use
        api_key: Google API key
        
    Returns:
        dict: Analysis result with revocation information
        
    Raises:
        Exception: If there's a rate limit error, so the calling code can retry
    """
    # Extract necessary bylaw information
    bylaw_text = ""
    if "extractedText" in bylaw:
        if isinstance(bylaw["extractedText"], list):
            bylaw_text = "\n\n".join(bylaw["extractedText"])
        else:
            bylaw_text = bylaw["extractedText"]
    
    bylaw_number = bylaw.get("bylawNumber", "Unknown")
    bylaw_year = bylaw.get("bylawYear", "Unknown")
    bylaw_type = bylaw.get("bylawType", "Unknown")
    
    try:
        # Set up the LLM
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.2
        )
        
        # Create the chain
        chain = REVOCATION_CHECK_PROMPT | llm | StrOutputParser()
        
        # Run the chain
        result = chain.invoke({
            "bylaw_text": bylaw_text,
            "bylaw_number": bylaw_number,
            "bylaw_year": bylaw_year,
            "bylaw_type": bylaw_type
        })
        
        # Clean the result of markdown formatting before parsing
        cleaned_result = clean_llm_response(result)
        
        # Parse the cleaned result
        try:
            logger.debug(f"Cleaned LLM response: {cleaned_result}")
            revocation_data = json.loads(cleaned_result)
            
            return revocation_data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response for bylaw {bylaw_number}: {e}")
            logger.error(f"Raw response: {result}")
            logger.error(f"Cleaned response: {cleaned_result}")
            # Re-raise to trigger retry instead of defaulting
            raise
            
    except Exception as e:
        # Check if this is a rate limit error
        if "429" in str(e) and "exceeded your current quota" in str(e):
            logger.warning(f"Rate limit hit for bylaw {bylaw_number}. Will retry.")
            # Re-raise the exception to trigger retry in the main loop
            raise
        
        logger.error(f"Error analyzing bylaw {bylaw_number}: {e}")
        # Re-raise any error to handle retry logic in the main loop
        raise

def is_bylaw_in_file(bylaw_number, file_path):
    """
    Check if a bylaw is already in a given file.
    
    Args:
        bylaw_number: Bylaw number to check
        file_path: Path to the JSON file
        
    Returns:
        bool: True if the bylaw is in the file, False otherwise
    """
    if not os.path.exists(file_path):
        return False
        
    bylaws = load_json_file(file_path)
    for bylaw in bylaws:
        if bylaw.get("bylawNumber") == bylaw_number:
            return True
    
    return False

def main():
    parser = argparse.ArgumentParser(description='Analyze bylaws to identify revocations')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file containing bylaws')
    parser.add_argument('--model', '-m', default='gemini-2.0-flash', help='Gemini model to use')
    parser.add_argument('--limit', '-l', type=int, help='Limit number of bylaws to process')
    parser.add_argument('--env-file', '-e', help='Path to .env file (defaults to .env in current directory)')
    parser.add_argument('--api-key', '-k', help='Google API key (overrides the key in .env file if provided)')
    args = parser.parse_args()
    
    # Load environment variables from custom .env file if specified
    if args.env_file:
        load_dotenv(args.env_file)
        logger.info(f"Loaded environment variables from {args.env_file}")
    
    # Get API key from command line argument or environment
    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("No API key provided. Either use --api-key option or set GOOGLE_API_KEY in your .env file.")
        return 1
    
    if args.api_key:
        logger.info("Using API key provided via command line")
    else:
        logger.info("Using API key from environment variables")
        
    # Get input file and create output file paths
    input_file = args.input
    base_name = os.path.splitext(input_file)[0]
    processed_file = f"{base_name}.PROCESSED_FOR_REVOCATION.json"
    revoked_file = f"{base_name}.REVOKED.json"
    
    # Load input bylaws
    bylaws = load_json_file(input_file)
    if not bylaws:
        logger.error(f"No bylaws found in {input_file}")
        return 1
        
    logger.info(f"Loaded {len(bylaws)} bylaws from {input_file}")
    
    # Get already processed bylaws
    processed_bylaws = get_processed_bylaws(processed_file)
    logger.info(f"Found {len(processed_bylaws)} already processed bylaws")
    
    # Apply the limit if specified
    if args.limit and args.limit > 0:
        bylaws = bylaws[:args.limit]
        logger.info(f"Limited processing to {args.limit} bylaws")
    
    # Process each bylaw
    processed_count = 0
    revoked_count = 0
    
    i = 0
    while i < len(bylaws):
        # Check if termination was requested
        if terminate:
            logger.info("Termination requested. Exiting cleanly...")
            break
        
        bylaw = bylaws[i]
        
        # Get bylaw number or skip if not present
        bylaw_number = bylaw.get("bylawNumber")
        if bylaw_number is None:
            logger.warning(f"Skipping bylaw with missing bylawNumber field: {bylaw}")
            i += 1
            continue
            
        # Skip already processed bylaws
        if bylaw_number in processed_bylaws:
            logger.info(f"Skipping already processed bylaw: {bylaw_number}")
            i += 1
            continue
            
        logger.info(f"Processing bylaw: {bylaw_number}")
        
        try:
            # Analyze the bylaw for revocation information
            revocation_data = analyze_bylaw_revocation(bylaw, args.model, api_key)
            processed_count += 1
            
            # Track if we've successfully handled all revoked bylaws
            all_revoked_bylaws_found = True
            
            # If this bylaw revokes other bylaws, process them
            if revocation_data.get("revokesOtherBylaws", False):
                revoked_bylaws = revocation_data.get("revokedBylaws", [])
                logger.info(f"Bylaw {bylaw_number} revokes {len(revoked_bylaws)} other bylaws")
                
                for revoked_info in revoked_bylaws:
                    revoked_number = revoked_info.get("bylawNumber")
                    revocation_reason = revoked_info.get("revocationReason")
                    
                    # Check if already in revoked file
                    if is_bylaw_in_file(revoked_number, revoked_file):
                        logger.warning(f"Bylaw {revoked_number} is already in the revoked file. Skipping.")
                        continue
                    
                    # Find the revoked bylaw in the input data
                    revoked_bylaw = find_bylaw_by_number(bylaws, revoked_number)
                    
                    if revoked_bylaw:
                        # Update revoked bylaw with inactive status
                        revoked_bylaw["isActive"] = False
                        revoked_bylaw["whyNotActive"] = f"Revoked by bylaw {bylaw_number}: {revocation_reason}"
                        
                        # Log the whyNotActive field value
                        logger.info(f"Revocation reason: {revoked_bylaw['whyNotActive']}")
                        
                        # Add to revoked file
                        if append_to_json_file(revoked_file, revoked_bylaw):
                            logger.info(f"Added revoked bylaw {revoked_number} to revoked file")
                            revoked_count += 1
                    else:
                        logger.warning(f"Could not find revoked bylaw {revoked_number} in the input file")
                        all_revoked_bylaws_found = False
            
            # Only add to processed file if we found all revoked bylaws (or if it doesn't revoke any)
            if all_revoked_bylaws_found:
                if append_to_json_file(processed_file, bylaw):
                    logger.info(f"Added bylaw {bylaw_number} to processed file")
            else:
                logger.warning(f"Not adding bylaw {bylaw_number} to processed file because some revoked bylaws were not found")
            
            # Sleep for 5 seconds between calls to not hit rate limits
            logger.info("Pausing for 3 seconds to not hit rate limits...")
            time.sleep(3)
            
            # Move to the next bylaw on success
            i += 1
                
        except Exception as e:
            # Check if it's a rate limit error
            if "429" in str(e) and "exceeded your current quota" in str(e):
                # Extract retry delay if available
                retry_delay = 10  # Default retry delay
                try:
                    # Try to extract the retry delay from the error message
                    import re
                    match = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)\s*}", str(e))
                    if match:
                        retry_delay = int(match.group(1))
                except:
                    pass
                
                logger.warning(f"Rate limit exceeded. Sleeping for {retry_delay} seconds before retrying bylaw {bylaw_number}...")
                time.sleep(retry_delay)
                # Don't increment i to retry the same bylaw
            else:
                # For non-rate-limit errors, log and move to next bylaw
                logger.error(f"Failed to process bylaw {bylaw_number}: {e}")
                logger.error("Skipping to next bylaw...")
                i += 1  # Move to next bylaw after error
            
        # Log progress
        if processed_count % 10 == 0 and processed_count > 0:
            logger.info(f"Processed {processed_count} bylaws so far, identified {revoked_count} revoked bylaws")
    
    # Log final summary
    logger.info(f"Processing complete: {processed_count} bylaws processed")
    logger.info(f"Revoked bylaws identified: {revoked_count} (saved to {revoked_file})")
    logger.info(f"Total bylaws processed: {len(processed_bylaws) + processed_count}")
    
    return 0

if __name__ == "__main__":
    exit(main()) 