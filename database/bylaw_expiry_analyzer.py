#!/usr/bin/env python3
"""
Bylaw Activity Analyzer

This script analyzes JSON bylaw data to determine if bylaws are still active or have expired.
It uses Gemini API via Langchain to analyze the extracted text and determine the bylaw's status.

The script reads bylaws from an input JSON file, determines their active status,
and distributes them to separate output files for active and inactive bylaws.
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
        logging.FileHandler("bylaw_activity_analyzer.log"),
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

# Define the prompt template for checking if a bylaw is active
EXPIRY_CHECK_PROMPT = ChatPromptTemplate.from_template("""
You are a legal expert in Canadian municipal bylaws. Your task is to analyze the text of a bylaw
and determine if it has expired based on today's date: **{current_date}**.

Here is the bylaw text to analyze:
<bylaw_text>
{bylaw_text}
</bylaw_text>

First, carefully search for any expiration date, sunset clause, repeal notice, or any indication
that would limit the time validity or current effect of this bylaw. Look for phrases like:
- "This by-law shall be in effect until..."
- "This by-law expires on..."
- "This by-law is repealed on..." or "repealed by bylaw X"
- "This by-law is valid for a period of..."
- Terms linked to council periods (e.g., "for the 2022-2026 term")
- Terms linked to specific events (e.g., "for the 2026 election")
- Conditions for becoming null/void (e.g., "null and void if not registered", "until successor appointed")
- Any specific end dates mentioned

IMPORTANT: Consider bylaw number: {bylaw_number}, bylaw year: {bylaw_year}, and bylaw type: {bylaw_type} in your analysis.

**Key Rules for Determining Status:**

1.  **Temporal Check:** If you find a specific expiry date, end-of-period date, or event date, you **MUST** compare it against today's date: **{current_date}**. The bylaw is only inactive due to time expiration if that date is definitively **BEFORE** {current_date}. An expiry date that is *on* or *after* {current_date} means the bylaw is currently active.
2.  **Conditional Check:** If expiry depends on a condition (e.g., registration, appointment of a successor, completion of an action) and the `<bylaw_text>` does **NOT** provide confirmation that the condition causing expiry *has actually occurred*, then you must treat the bylaw as **active**. Do not assume the condition was met unless the text confirms it.
3.  **Repeal Check:** If the text explicitly states the bylaw has been repealed (e.g., "repealed by bylaw X"), then it is inactive.

If, applying the rules above, the bylaw has clearly and verifiably expired or been repealed based *only* on the provided text and the comparison with {current_date}, respond with:
{{
  "isActive": false,
  "whyNotActive": "[Provide the specific, verifiable reason based *only* on the text. Cite the exact clause, date, or repeal notice identified. Do NOT mention assumptions about unverified conditions. Do NOT mention today's date or the comparison logic in this explanation.]"
}}
*Example: "Section 5 states the by-law expires on December 31, 2023."*
*Example: "The text indicates this bylaw was repealed by bylaw number XXXX."*

If, applying the rules above, the bylaw appears to still be active (no expiry found, expiry is in the future, or expiry condition is unverified in the text), respond with:
{{
  "isActive": true,
  "whyNotActive": null
}}

Respond ONLY with this JSON format and nothing else.
""")

def load_json_file(file_path):
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return []

def get_processed_bylaws(active_file, inactive_file):
    """
    Get a set of bylaw numbers that have already been processed.
    
    Args:
        active_file: Path to the active bylaws output file
        inactive_file: Path to the inactive bylaws output file
        
    Returns:
        tuple: (set of processed bylaw numbers, count of active, count of inactive)
    """
    processed = set()
    active_count = 0
    inactive_count = 0
    
    # Check active bylaws file
    if os.path.exists(active_file):
        active_bylaws = load_json_file(active_file)
        active_count = len(active_bylaws)
        for bylaw in active_bylaws:
            if 'bylawNumber' in bylaw:
                processed.add(bylaw['bylawNumber'])
    
    # Check inactive bylaws file
    if os.path.exists(inactive_file):
        inactive_bylaws = load_json_file(inactive_file)
        inactive_count = len(inactive_bylaws)
        for bylaw in inactive_bylaws:
            if 'bylawNumber' in bylaw:
                processed.add(bylaw['bylawNumber'])
    
    return processed, active_count, inactive_count

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

def analyze_bylaw_activity(bylaw, model_name, api_key):
    """
    Analyze a bylaw to determine if it's still active using Gemini API.
    
    Args:
        bylaw: JSON bylaw data
        model_name: Name of the Gemini model to use
        api_key: Google API key
        
    Returns:
        dict: The bylaw data with isActive and whyNotActive fields added
        
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
    
    # Get current date for the prompt
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Set up the LLM
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.2
        )
        
        # Create the chain
        chain = EXPIRY_CHECK_PROMPT | llm | StrOutputParser()
        
        # Run the chain
        result = chain.invoke({
            "bylaw_text": bylaw_text,
            "current_date": current_date,
            "bylaw_number": bylaw_number,
            "bylaw_year": bylaw_year,
            "bylaw_type": bylaw_type
        })
        
        # Clean the result of markdown formatting before parsing
        cleaned_result = clean_llm_response(result)
        
        # Parse the cleaned result
        try:
            logger.debug(f"Cleaned LLM response: {cleaned_result}")
            status_data = json.loads(cleaned_result)
            
            # Add the status data to the bylaw
            bylaw["isActive"] = status_data.get("isActive", True)
            bylaw["whyNotActive"] = status_data.get("whyNotActive")
            
            return bylaw
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

def main():
    parser = argparse.ArgumentParser(description='Analyze bylaws to determine if they are still active')
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
    active_file = f"{base_name}.ACTIVE_ONLY.json"
    inactive_file = f"{base_name}.NOT_ACTIVE_ONLY.json"
    
    # Load input bylaws
    bylaws = load_json_file(input_file)
    if not bylaws:
        logger.error(f"No bylaws found in {input_file}")
        return 1
        
    logger.info(f"Loaded {len(bylaws)} bylaws from {input_file}")
    
    # Get already processed bylaws
    processed_bylaws, previously_active, previously_inactive = get_processed_bylaws(active_file, inactive_file)
    total_processed = len(processed_bylaws)
    logger.info(f"Found {total_processed} already processed bylaws ({previously_active} active, {previously_inactive} inactive)")
    
    # Apply the limit if specified
    if args.limit and args.limit > 0:
        bylaws = bylaws[:args.limit]
        logger.info(f"Limited processing to {args.limit} bylaws")
    
    # Process each bylaw
    processed_count = 0
    active_count = 0
    inactive_count = 0
    
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
            # Analyze the bylaw
            processed_bylaw = analyze_bylaw_activity(bylaw, args.model, api_key)
            processed_count += 1
            
            file_updated = False
            
            # Append to the appropriate output file
            if processed_bylaw.get("isActive", True):
                logger.info(f"Bylaw {bylaw_number} is active")
                if append_to_json_file(active_file, processed_bylaw):
                    active_count += 1
                    file_updated = True
            else:
                logger.info(f"Bylaw {bylaw_number} is NOT active: {processed_bylaw.get('whyNotActive')}")
                if append_to_json_file(inactive_file, processed_bylaw):
                    inactive_count += 1
                    file_updated = True
                    
            # Sleep for 5 seconds after writing to output file
            if file_updated:
                logger.info("Pausing for 5 seconds to not hit rate limits...")
                time.sleep(4)
            
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
            logger.info(f"Processed {processed_count} bylaws so far ({active_count} active, {inactive_count} inactive)")
    
    # Log final summary
    logger.info(f"Processing complete: {processed_count} bylaws processed")
    logger.info(f"Active bylaws: {active_count} (saved to {active_file})")
    logger.info(f"Inactive bylaws: {inactive_count} (saved to {inactive_file})")
    logger.info(f"Total bylaws classified: {total_processed + processed_count} ({previously_active + active_count} active, {previously_inactive + inactive_count} inactive)")
    
    return 0

if __name__ == "__main__":
    exit(main()) 