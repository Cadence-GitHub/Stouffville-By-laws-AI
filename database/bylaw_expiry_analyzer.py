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
You are a meticulous legal analyst specializing in Canadian municipal bylaws. Your task is to analyze the text of a bylaw and determine if it is currently active or has expired based on today's date: **{current_date}**.

Here is the bylaw text to analyze:
<bylaw_text>
{bylaw_text}
</bylaw_text>

Consider the following information during your analysis:
- Bylaw Number: {bylaw_number}
- Bylaw Year: {bylaw_year}
- Bylaw Type: {bylaw_type}
- Today's Date: {current_date}

**Follow these steps precisely:**

1.  **Identify Potential Expiry or Repeal Conditions:** Carefully scan the `<bylaw_text>` for any clauses, phrases, specific dates, terms of office, event dependencies, repeal notices, or sunset clauses that limit the bylaw's duration or define when it ceases to be in effect. Look for indicators like:
    *   "This by-law shall be in effect until..."
    *   "This by-law expires on..."
    *   "This by-law is repealed on..." or "repealed by bylaw X"
    *   "This by-law is valid for a period of..." (calculate end date based on enactment date if available)
    *   Specific end dates (e.g., "December 31, 2024", "November 30, 2026")
    *   Terms tied to events (e.g., "for the 2026 Municipal Election")
    *   Terms tied to council periods (e.g., "for the 2022-2026 Term of Council")
    *   Conditions for becoming null/void (e.g., "shall become null and void if...", "expires upon appointment of successor", "until completion of works")

2.  **Determine the Expiry Point and Verification Status:**
    *   For each condition found in Step 1, determine the potential Expiry Point (a specific date, end of a term, occurrence of an event).
    *   **Crucially, assess if the expiry condition is:**
        *   **(a) Stated definitively and verifiably within the text:** (e.g., a specific date, a completed term based on {current_date}, a notice of repeal *within the text*). This is a **Verified Expiry**.
        *   **(b) Dependent on an external condition or future event not confirmed within the text:** (e.g., "null and void *if* not registered", "expires upon appointment of successor", "until completion of works", a future election date, a future term end date). This is an **Unverified or Future Expiry**.
    *   If **no** potential expiry conditions are found, assume the bylaw is active.
    *   If **only** Unverified or Future Expiry conditions are found, assume the bylaw is currently active.

3.  **Compare Verified Expiry Point with Today's Date:**
    *   **Only if** a **Verified Expiry** point (type 2a) was determined **AND** its associated date is clearly identifiable, compare that date **strictly** against **{current_date}**.

4.  **Decide Activation Status:**
    *   **IF** a Verified Expiry Point (type 2a) was found **AND** its date is **BEFORE** {current_date}, the bylaw is **inactive**.
    *   **ELSE (including cases where the Verified Expiry Point is ON or AFTER {current_date}, OR only Unverified/Future Expiry Points were found, OR no expiry points were found)**, the bylaw is **active**.

5.  **Format the Output:** Respond ONLY with the JSON format below.

    *   If the bylaw is **inactive** (Verified Expiry Point's date is before {current_date}):
        ```json
        {{
          "isActive": false,
          "whyNotActive": "[Provide the specific reason based *only* on the confirmed expiry condition stated in the text. Reference the exact clause, date, or repeal notice from the bylaw text. Do NOT speculate or mention unverified conditions. Do NOT mention today's date or the comparison logic in this explanation.]"
        }}
        ```
        *Example whyNotActive: "Section 5 states the by-law expires on December 31, 2023."*
        *Example whyNotActive: "The bylaw appoints members for the 2018-2022 Term of Council, which concluded in 2022."*
        *Example whyNotActive: "The text indicates this bylaw was repealed by bylaw number XXXX."*
        *Example whyNotActive: "Section 10.1 states: 'This By-law will expire at 12:01 AM on September 1st, 2009'."*

    *   If the bylaw is **active**:
        ```json
        {{
          "isActive": true,
          "whyNotActive": null
        }}
        ```

Respond ONLY with the specified JSON format and nothing else.
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