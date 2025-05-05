#!/usr/bin/env python3
import os
import json
import argparse
import re
from pathlib import Path
import tiktoken


def count_tokens(text):
    """
    Count tokens using OpenAI's tiktoken library.

    Args:
        text (str): The text to count tokens for

    Returns:
        int: Exact token count
    """
    if not text:
        return 0

    # Convert to string if it's not already
    if not isinstance(text, str):
        text = json.dumps(text)

    # Use cl100k_base encoding (used by GPT-3.5 and GPT-4)
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def validate_bylaw_number(bylaw_number):
    """
    Validate that the bylaw number follows the format YYYY-NNN
    where YYYY is a year and NNN is a number from 001 to 999.
    Also accepts YYYY-NNNA and YYYY-NNNB formats.
    
    Args:
        bylaw_number (str): The bylaw number to validate
        
    Returns:
        bool: True if the format is valid, False otherwise
    """
    # Regex pattern for YYYY-NNN format
    standard_pattern = r'^(\d{4})-([0-9]{3})$'
    # Regex pattern for YYYY-NNNA or YYYY-NNNB format
    ab_suffix_pattern = r'^(\d{4})-([0-9]{3})([AB])$'
    
    standard_match = re.match(standard_pattern, bylaw_number)
    ab_suffix_match = re.match(ab_suffix_pattern, bylaw_number)
    
    if ab_suffix_match:
        # If it matches the YYYY-NNNA or YYYY-NNNB pattern, check numeric part
        numeric_part = int(ab_suffix_match.group(2))
        if numeric_part < 1 or numeric_part > 999:
            return False
        return True
    
    if not standard_match:
        return False
    
    # Check if the numeric part is between 001-999
    numeric_part = int(standard_match.group(2))
    if numeric_part < 1 or numeric_part > 999:
        return False
        
    return True


def attempt_fix_bylaw_number(bylaw_number):
    """
    Attempt to fix a bylaw number that doesn't match the required format.
    Tries various scenarios to convert the given bylaw number to the correct format.
    Scenarios are applied additively (changes from one scenario are kept for the next).
    
    Args:
        bylaw_number (str): The invalid bylaw number to fix
        
    Returns:
        tuple: (fixed_bylaw_number, is_valid, scenario_applied)
            - fixed_bylaw_number: The potentially fixed bylaw number
            - is_valid: Whether the fixed bylaw number is now valid
            - scenario_applied: Description of the scenario that was applied, or None if no fix worked
    """
    # First check if the bylaw number is already valid
    if validate_bylaw_number(bylaw_number):
        return bylaw_number, True, "Already valid"
        
    original_bylaw_number = bylaw_number
    applied_scenarios = []
    
    # Scenario 1: Handle two-digit years (71-99) by adding "19" prefix
    if len(bylaw_number) >= 2:
        match = re.match(r'^([7-9][0-9])[^a-zA-Z0-9]', bylaw_number)
        if match:
            year_prefix = match.group(1)
            bylaw_number = "19" + bylaw_number
            applied_scenarios.append(f"Scenario 1: Added '19' to two-digit year '{year_prefix}'")
            
            # Check if the fix worked
            if validate_bylaw_number(bylaw_number):
                return bylaw_number, True, ", ".join(applied_scenarios)
    
    # Scenario 1b: Replace space with dash in "YYYY N", "YYYY NN", or "YYYY NNN" formats
    space_pattern = r'^(\d{4})\s+(\d{1,3})$'
    space_match = re.match(space_pattern, bylaw_number)
    if space_match:
        year = space_match.group(1)
        number = space_match.group(2)
        
        # Pad the number with leading zeros if needed
        if len(number) == 1:
            padded_number = "00" + number
            applied_scenarios.append(f"Scenario 1b: Replaced space with dash and padded '{number}' to '{padded_number}'")
        elif len(number) == 2:
            padded_number = "0" + number
            applied_scenarios.append(f"Scenario 1b: Replaced space with dash and padded '{number}' to '{padded_number}'")
        else:
            padded_number = number
            applied_scenarios.append(f"Scenario 1b: Replaced space with dash")
        
        bylaw_number = f"{year}-{padded_number}"
        
        # Check if the fix worked
        if validate_bylaw_number(bylaw_number):
            return bylaw_number, True, ", ".join(applied_scenarios)
    
    # Scenario 2: Remove spaces
    if ' ' in bylaw_number:
        bylaw_number = bylaw_number.replace(' ', '')
        applied_scenarios.append("Scenario 2: Removed spaces")
        
        # Check if the fix worked
        if validate_bylaw_number(bylaw_number):
            return bylaw_number, True, ", ".join(applied_scenarios)
    
    # Scenario 3: Pad numbers with leading zeros for various formats
    # Handle any pattern with a 4-digit year followed by a 1 or 2 digit number
    number_format_pattern = r'^(\d{4})-(\d{1,3})(.*)$'
    match = re.match(number_format_pattern, bylaw_number)
    if match:
        year = match.group(1)
        number = match.group(2)
        remainder = match.group(3) or ""
        
        # Only pad the number if it's 1 or 2 digits
        if len(number) == 1:
            padded_number = "00" + number
            bylaw_number = f"{year}-{padded_number}{remainder}"
            applied_scenarios.append(f"Scenario 3: Padded single digit '{number}' to '{padded_number}'")
        elif len(number) == 2:
            padded_number = "0" + number
            bylaw_number = f"{year}-{padded_number}{remainder}"
            applied_scenarios.append(f"Scenario 3: Padded double digit '{number}' to '{padded_number}'")
        # Don't modify 3-digit numbers
        
        # Check if the fix worked
        if validate_bylaw_number(bylaw_number):
            return bylaw_number, True, ", ".join(applied_scenarios)
    
    # Scenario 4: Remove any suffix after YYYY-NNN format (including non-ASCII characters)
    # But don't remove A or B suffixes in YYYY-NNNA or YYYY-NNNB formats
    
    # First check for YYYY-NNNA or YYYY-NNNB pattern
    ab_suffix_pattern = r'^(\d{4})-([0-9]{3})([AB])$'
    ab_suffix_match = re.match(ab_suffix_pattern, bylaw_number)
    if ab_suffix_match:
        # This is already in the YYYY-NNNA or YYYY-NNNB format, which is now considered valid
        return bylaw_number, True, "Valid with A/B suffix"
    
    # For other suffixes, check for exact YYYY-NNN pattern at the start
    basic_pattern = r'^(\d{4})-([0-9]{3})'
    basic_match = re.match(basic_pattern, bylaw_number)
    if basic_match and len(bylaw_number) > 8:  # 8 chars is exactly YYYY-NNN
        # Extract the year and number parts
        year = basic_match.group(1)
        number = basic_match.group(2)
        removed_part = bylaw_number[8:]  # Everything after YYYY-NNN
        bylaw_number = f"{year}-{number}"
        applied_scenarios.append(f"Scenario 4: Removed suffix '{removed_part}'")
        
        # Check if the fix worked
        if validate_bylaw_number(bylaw_number):
            return bylaw_number, True, ", ".join(applied_scenarios)
    
    # If we've applied any scenarios but still failed, return the last attempt
    if applied_scenarios:
        return bylaw_number, False, ", ".join(applied_scenarios) + " (still invalid)"
    
    # No scenarios applied, return the original with failure status
    return original_bylaw_number, False, None


def search_bylaws_by_keyword(base_dir, keyword, output_file, include_all=False, exclude_invalid=False):
    """
    Search through all JSON files in the base_dir for a specific keyword in the 'keywords' list.
    Print matching filenames and their keywords list, and append the entire JSON content
    to the output file. Handles both single bylaw objects and arrays of bylaws in a file.

    Args:
        base_dir (str): The directory to search in (and its subdirectories) or a specific JSON file
        keyword (str): The keyword to search for (partial matches are included)
        output_file (str): The file to append results to
        include_all (bool): Whether to include all bylaws regardless of keywords
        exclude_invalid (bool): Whether to exclude bylaws with invalid bylaw numbers that can't be fixed

    Returns:
        tuple: (output tokens, source tokens) - token counts for output and source data
    """
    # Always start with fresh output data
    output_data = []

    total_source_tokens = 0
    total_source_files = 0
    total_bylaws_processed = 0
    bylaws_excluded_invalid_number = 0
    files_with_missing_bylaw_number = []
    files_with_parse_errors = []
    files_with_invalid_bylaw_format = []
    files_with_fixed_bylaw_format = []
    files_with_valid_bylaw_format = []
    multi_bylaw_files = []
    matching_files = []

    # For tracking all bylaws
    all_bylaws = []
    consolidated_preferred = []
    all_duplicates = {}  # Track all duplicates

    # Check if base_dir is a file or directory
    base_path = Path(base_dir)
    if base_path.is_file() and base_path.suffix.lower() == '.json':
        # Process a single JSON file
        json_files = [base_path]
        print(f"Processing single JSON file: {base_path}")
    else:
        # Walk through all JSON files in the directory and subdirectories
        json_files = list(base_path.glob('**/*.json'))
        print(f"Processing {len(json_files)} JSON files in directory: {base_path}")

    # Process each JSON file
    for json_file in json_files:
        # Skip status.json files
        if json_file.name == "status.json":
            continue
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                total_source_files += 1
                
                # Determine if the file contains a single bylaw or multiple bylaws
                bylaws_list = []
                if isinstance(file_data, list):
                    bylaws_list = file_data
                    multi_bylaw_files.append(str(json_file))
                    print(f"Found file with multiple bylaws: {json_file} ({len(bylaws_list)} bylaws)")
                else:
                    bylaws_list = [file_data]
                
                total_bylaws_processed += len(bylaws_list)
                file_tokens = 0
                
                # Process each bylaw in the file
                for bylaw_data in bylaws_list:
                    # Store source file and create a copy to avoid reference issues
                    bylaw_data = bylaw_data.copy()  # Create a copy
                    bylaw_data['_source_file'] = str(json_file)
                    
                    # Count tokens from the extractedText field (which can be a list or string)
                    if 'extractedText' in bylaw_data:
                        if isinstance(bylaw_data['extractedText'], list):
                            # Join all text segments if it's a list
                            extracted_text = " ".join(bylaw_data['extractedText'])
                            bylaw_tokens = count_tokens(extracted_text)
                        elif isinstance(bylaw_data['extractedText'], str):
                            bylaw_tokens = count_tokens(bylaw_data['extractedText'])
                        else:
                            bylaw_tokens = 0

                        file_tokens += bylaw_tokens

                    # Process bylaw based on include_all flag or keyword matching
                    should_include = False
                    
                    # If including all bylaws
                    if include_all:
                        should_include = True
                    # Otherwise check for keyword matches
                    elif keyword and 'keywords' in bylaw_data and isinstance(bylaw_data['keywords'], list):
                        # Look for keyword in the keywords list (case-insensitive)
                        if any(keyword.lower() in kw.lower() for kw in bylaw_data['keywords']):
                            should_include = True
                    
                    if should_include:
                        # Check if bylaw has a valid bylaw number
                        if 'bylawNumber' not in bylaw_data or not bylaw_data['bylawNumber']:
                            print(f"Error: Missing bylawNumber in {json_file} for bylaw: {bylaw_data.get('title', 'Unknown title')}")
                            files_with_missing_bylaw_number.append(str(json_file))
                            continue
                        
                        # Validate bylaw number format
                        bylaw_format_valid = validate_bylaw_number(bylaw_data['bylawNumber'])
                        
                        # If not valid, attempt to fix it
                        if not bylaw_format_valid:
                            fixed_bylaw, is_fixed, scenario = attempt_fix_bylaw_number(bylaw_data['bylawNumber'])
                            
                            if is_fixed:
                                status_msg = "Including" if include_all else "Found match in"
                                print(f"{status_msg}: {json_file}   (bylawNumber: {bylaw_data['bylawNumber']} → {fixed_bylaw}) OK (Fixed)")
                                print(f"Fixed with {scenario}")
                                files_with_fixed_bylaw_format.append((str(json_file), bylaw_data['bylawNumber'], fixed_bylaw, scenario))
                                # Update the bylaw number to the fixed version
                                bylaw_data['bylawNumber'] = fixed_bylaw
                            else:
                                format_status = "FAIL"
                                status_msg = "Including" if include_all else "Found match in"
                                print(f"{status_msg}: {json_file}   (bylawNumber: {bylaw_data['bylawNumber']}) {format_status}")
                                warning_msg = f"Warning: Invalid bylawNumber format '{bylaw_data['bylawNumber']}' in {json_file} - Couldn't auto-fix"
                                print(warning_msg)
                                # Store the scenario if any was applied but failed
                                fix_attempt = scenario if scenario else "No applicable fix scenario"
                                files_with_invalid_bylaw_format.append((str(json_file), bylaw_data['bylawNumber'], fix_attempt))
                                
                                # Skip adding this bylaw to output_data if exclude_invalid is True
                                if exclude_invalid:
                                    print(f"Excluding bylaw with invalid number format: {bylaw_data['bylawNumber']}")
                                    bylaws_excluded_invalid_number += 1
                                    continue
                        else:
                            format_status = "OK"
                            files_with_valid_bylaw_format.append(str(json_file))
                            status_msg = "Including" if include_all else "Found match in"
                            print(f"{status_msg}: {json_file}   (bylawNumber: {bylaw_data['bylawNumber']}) {format_status}")
                        
                        if not include_all and 'keywords' in bylaw_data:
                            print(f"Keywords: {bylaw_data['keywords']}")
                        
                        if str(json_file) not in matching_files:
                            matching_files.append(str(json_file))
                        
                        # Add to our all_bylaws list
                        all_bylaws.append(bylaw_data)
                        
                        # Track duplicates
                        if 'bylawNumber' in bylaw_data and bylaw_data['bylawNumber']:
                            bylaw_number = bylaw_data['bylawNumber']
                            if bylaw_number not in all_duplicates:
                                all_duplicates[bylaw_number] = []
                            all_duplicates[bylaw_number].append(str(json_file))
                
                # Add the file tokens to the total
                total_source_tokens += file_tokens
                
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error processing {json_file}: {e}")
            files_with_parse_errors.append((str(json_file), str(e)))

    # Process duplicates and consolidate versions
    final_bylaws = []
    handled_sources = set()  # Track which source files we've already handled
    
    # Find duplicates (bylaws with same number but different source files)
    duplicate_numbers = {num: files for num, files in all_duplicates.items() if len(files) > 1}
    
    # First handle consolidated versions
    for bylaw in all_bylaws:
        bylaw_number = bylaw.get('bylawNumber')
        source_file = bylaw.get('_source_file', '')
        
        # Skip if we've already handled this source file
        if source_file in handled_sources:
            continue
            
        # Check if this bylaw has duplicates
        if bylaw_number in duplicate_numbers:
            # Get all duplicates for this bylaw number
            duplicate_files = duplicate_numbers[bylaw_number]
            
            # Check if any duplicates have "consolidated" in the name
            consolidated_files = [f for f in duplicate_files if "consolidated" in f.lower()]
            non_consolidated_files = [f for f in duplicate_files if "consolidated" not in f.lower()]
            
            if consolidated_files and non_consolidated_files:
                # We have both consolidated and non-consolidated versions
                # For each consolidated file, add to final_bylaws and track
                for consol_file in consolidated_files:
                    # Find the bylaw with this source file
                    for b in all_bylaws:
                        if b.get('_source_file') == consol_file and b.get('bylawNumber') == bylaw_number:
                            final_bylaws.append(b)
                            handled_sources.add(consol_file)
                            # Log the consolidation preference
                            for non_consol_file in non_consolidated_files:
                                consolidated_preferred.append((bylaw_number, consol_file, non_consol_file))
                            break
                
                # Mark all non-consolidated files as handled
                for f in non_consolidated_files:
                    handled_sources.add(f)
            elif bylaw_number in duplicate_numbers:
                # No consolidation preference, use filenames as bylaw numbers
                for dup_file in duplicate_files:
                    # Find the bylaw with this source file
                    for b in all_bylaws:
                        if b.get('_source_file') == dup_file and b.get('bylawNumber') == bylaw_number:
                            # Make a copy to avoid modifying the original
                            b_copy = b.copy()
                            
                            # Use filename as bylaw number
                            filename = os.path.basename(dup_file)
                            if filename.endswith('.json'):
                                filename = filename[:-5]  # Remove .json extension
                            
                            print(f"\nRenaming duplicate bylawNumber for file {dup_file}:")
                            print(f"  - Original bylawNumber: {bylaw_number}")
                            print(f"  - New bylawNumber: {filename}")
                            
                            b_copy['bylawNumber'] = filename
                            final_bylaws.append(b_copy)
                            handled_sources.add(dup_file)
                            break
        
    # Add all non-duplicate bylaws
    for bylaw in all_bylaws:
        source_file = bylaw.get('_source_file', '')
        if source_file not in handled_sources:
            final_bylaws.append(bylaw)
            handled_sources.add(source_file)
    
    # Set output_data to our final_bylaws list
    output_data = final_bylaws
    
    # Verify counts
    print(f"\nAfter duplicate processing:")
    print(f"Total bylaws in final output: {len(output_data)}")
    print(f"Total source bylaws processed: {len(all_bylaws)}")
    print(f"Total unique source files: {len(handled_sources)}")

    # Write the output data to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Remove temporary _source_file field before saving
        output_data_clean = []
        for bylaw in output_data:
            bylaw_copy = bylaw.copy()
            if '_source_file' in bylaw_copy:
                del bylaw_copy['_source_file']
            output_data_clean.append(bylaw_copy)
        json.dump(output_data_clean, f, indent=2, ensure_ascii=False)

    # Print reports
    
    if files_with_missing_bylaw_number:
        print("\nFiles with missing bylawNumber:")
        for file in files_with_missing_bylaw_number:
            print(f"  - {file}")
    
    if files_with_parse_errors:
        print("\nFiles with parse errors:")
        for file, error in files_with_parse_errors:
            print(f"  - {file}: {error}")
    
    if files_with_fixed_bylaw_format:
        print("\nFiles with auto-fixed bylawNumber format:")
        for file, original, fixed, scenario in files_with_fixed_bylaw_format:
            print(f"  - {file}: '{original}' → '{fixed}' ({scenario})")

    if files_with_invalid_bylaw_format:
        print("\nFiles with invalid bylawNumber format (couldn't fix):")
        for file, bylaw_number, fix_attempt in files_with_invalid_bylaw_format:
            print(f"  - {file}: '{bylaw_number}' (Fix attempt: {fix_attempt})")
    
    if multi_bylaw_files:
        print("\nFiles with multiple bylaws:")
        for file in multi_bylaw_files:
            print(f"  - {file}")
    
    if consolidated_preferred:
        print("\nConsolidated versions preferred for duplicate bylaws:")
        for bylaw_number, kept_file, skipped_file in consolidated_preferred:
            print(f"  - {bylaw_number}:")
            print(f"    * Kept: {kept_file}")
            print(f"    * Skipped: {skipped_file}")
    
    print(f"\nTotal source files processed: {total_source_files}")
    print(f"Total bylaws processed: {total_bylaws_processed}")
    print(f"Total matching files: {len(matching_files)}")
    print(f"Total files with multiple bylaws: {len(multi_bylaw_files)}")
    if all_duplicates:
        print(f"Total bylaws with duplicate numbers (before consolidation): {len(all_duplicates)}")
    if consolidated_preferred:
        print(f"Total bylaws where consolidated version was preferred: {len(consolidated_preferred)}")
    print(f"Total files with valid bylawNumber format (originally valid): {len(files_with_valid_bylaw_format)}")
    print(f"Total files with invalid bylawNumber format (couldn't fix): {len(files_with_invalid_bylaw_format)}")
    if exclude_invalid:
        print(f"Total bylaws excluded due to invalid bylaw numbers: {bylaws_excluded_invalid_number}")
    print(f"Total files with auto-fixed bylawNumber format: {len(files_with_fixed_bylaw_format)}")
    print(f"Sum of valid, fixed, and invalid bylawNumbers: {len(files_with_valid_bylaw_format) + len(files_with_fixed_bylaw_format) + len(files_with_invalid_bylaw_format)}")
    print(f"Total files with missing bylawNumber: {len(files_with_missing_bylaw_number)}")
    print(f"Total files with parse errors: {len(files_with_parse_errors)}")
    print(f"\nResults saved to: {output_file}")
    print(f"Output file size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")

    # Calculate token count for output data extractedText fields
    output_tokens = 0
    for item in output_data:
        if 'extractedText' in item:
            if isinstance(item['extractedText'], list):
                # Join all text segments if it's a list
                extracted_text = " ".join(item['extractedText'])
                output_tokens += count_tokens(extracted_text)
            elif isinstance(item['extractedText'], str):
                output_tokens += count_tokens(item['extractedText'])

    return (output_tokens, total_source_tokens)


def calculate_llm_costs(token_count):
    """
    Calculate estimated costs for processing tokens with different LLM pricing tiers.

    Args:
        token_count (int): The number of tokens

    Returns:
        dict: Cost estimates for different pricing tiers
    """
    # Cost per million tokens
    price_tiers = {
        "Budget LLM": 0.10,
        "Standard LLM": 0.15,
        "Premium LLM": 0.25,
        "Advanced LLM": 3.00
    }

    costs = {}
    tokens_in_millions = token_count / 1_000_000

    for model, price in price_tiers.items():
        costs[model] = tokens_in_millions * price

    return costs


def print_token_info(token_count, label=""):
    """Print token count and cost information."""
    prefix = f"{label} " if label else ""
    print(f"\n{prefix}Token Information (extractedText field only):")
    print(f"Total tokens in extractedText: {token_count:,}")

    print(f"\n{prefix}Estimated LLM costs for extractedText:")
    costs = calculate_llm_costs(token_count)
    for model, cost in costs.items():
        print(f"  {model} (${costs[model]:.2f}/million tokens): ${cost:.4f}")


def check_duplicate_bylaw_numbers(bylaws_data):
    """
    Check for duplicate bylaw numbers in the processed data.
    
    Args:
        bylaws_data (list): List of bylaw objects
        
    Returns:
        tuple: (duplicates_dict, consolidated_preferred_count)
            - duplicates_dict: Dictionary with bylaw numbers as keys and lists of file paths as values for duplicates
            - consolidated_preferred_count: Count of bylaws where consolidated version was preferred
    """
    bylaw_number_map = {}
    duplicates = {}
    consolidated_preferred_count = 0
    
    for bylaw in bylaws_data:
        if 'bylawNumber' in bylaw and bylaw.get('_source_file'):
            bylaw_number = bylaw['bylawNumber']
            source_file = bylaw['_source_file']
            
            if bylaw_number in bylaw_number_map:
                # Add to duplicates if this is the first duplicate found
                if bylaw_number not in duplicates:
                    duplicates[bylaw_number] = [bylaw_number_map[bylaw_number]]
                duplicates[bylaw_number].append(source_file)
            else:
                bylaw_number_map[bylaw_number] = source_file
                
    return duplicates, consolidated_preferred_count


def main():
    parser = argparse.ArgumentParser(description='Search bylaws by keyword')
    parser.add_argument('keyword', nargs='?', help='Keyword to search for in bylaw keywords (optional)')
    parser.add_argument('--input', default='Stouffville_AI/database/By-laws-by-year',
                        help='Directory to search in or a specific JSON file (default: Stouffville_AI/database/By-laws-by-year)')
    parser.add_argument('--output', default=None,
                        help='Output file name (default: {keyword}_related_by-laws.json or all_by-laws.json)')
    parser.add_argument('--exclude-invalid', action='store_true', 
                        help='Exclude bylaws with invalid bylaw numbers that cannot be fixed')

    args = parser.parse_args()

    include_all = False

    # If keyword is not provided, ask user if they want to include all bylaws
    if args.keyword is None:
        response = input("No keyword provided. Do you want to include all bylaws in the output file? (y/n): ")
        if response.lower() in ['y', 'yes']:
            include_all = True
            print("Including all bylaws in the output.")
            # Set a default keyword for output filename
            if args.output is None:
                args.output = "all_by-laws.json"
        else:
            keyword = input("Please enter a keyword to search for: ")
            args.keyword = keyword
            if not args.keyword:
                print("No keyword provided. Exiting.")
                return

    # Set default output filename to include the keyword if not specified
    if args.output is None:
        args.output = f"{args.keyword}_related_by-laws.json"

    output_tokens, source_tokens = search_bylaws_by_keyword(
        args.input, args.keyword, args.output, include_all, args.exclude_invalid)

    # Display token count and cost information for both source and output
    print_token_info(source_tokens, "Source Data")
    print_token_info(output_tokens, "Output Data")

if __name__ == "__main__":
    main()

    