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


def search_bylaws_by_keyword(base_dir, keyword, output_file):
    """
    Search through all JSON files in the base_dir for a specific keyword in the 'keywords' list.
    Print matching filenames and their keywords list, and append the entire JSON content
    to the output file.
    
    Args:
        base_dir (str): The directory to search in (and its subdirectories)
        keyword (str): The keyword to search for (partial matches are included)
        output_file (str): The file to append results to
        
    Returns:
        tuple: (output tokens, source tokens) - token counts for output and source data
    """
    # Always start with fresh output data
    output_data = []
    
    base_path = Path(base_dir)
    matching_files = []
    total_source_tokens = 0
    total_source_files = 0
    
    # Walk through all JSON files in the directory and subdirectories
    for json_file in base_path.glob('**/*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                bylaw_data = json.load(f)
                total_source_files += 1
                
                # Count tokens from the extractedText field (which can be a list or string)
                if 'extractedText' in bylaw_data:
                    if isinstance(bylaw_data['extractedText'], list):
                        # Join all text segments if it's a list
                        extracted_text = " ".join(bylaw_data['extractedText'])
                        file_tokens = count_tokens(extracted_text)
                    elif isinstance(bylaw_data['extractedText'], str):
                        file_tokens = count_tokens(bylaw_data['extractedText'])
                    else:
                        file_tokens = 0
                        
                    total_source_tokens += file_tokens
                
                # Check if 'keywords' exists and is a list
                if 'keywords' in bylaw_data and isinstance(bylaw_data['keywords'], list):
                    # Look for keyword in the keywords list (case-insensitive)
                    if any(keyword.lower() in kw.lower() for kw in bylaw_data['keywords']):
                        print(f"\nFound match in: {json_file}")
                        print(f"Keywords: {bylaw_data['keywords']}")
                        matching_files.append(str(json_file))
                        
                        # Append to the output data
                        output_data.append(bylaw_data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error processing {json_file}: {e}")
    
    # Write the output data to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nTotal source files processed: {total_source_files}")
    print(f"Total matching files: {len(matching_files)}")
    print(f"Results saved to: {output_file}")
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


def main():
    parser = argparse.ArgumentParser(description='Search bylaws by keyword')
    parser.add_argument('keyword', help='Keyword to search for in bylaw keywords')
    parser.add_argument('--dir', default='Stouffville_AI/database/By-laws-by-year', 
                        help='Directory to search in (default: Stouffville_AI/database/By-laws-by-year)')
    parser.add_argument('--output', default=None,
                        help='Output file name (default: {keyword}_related_by-laws.json)')
    
    args = parser.parse_args()
    
    # Set default output filename to include the keyword if not specified
    if args.output is None:
        args.output = f"{args.keyword}_related_by-laws.json"
    
    output_tokens, source_tokens = search_bylaws_by_keyword(args.dir, args.keyword, args.output)
    
    # Display token count and cost information for both source and output
    print_token_info(source_tokens, "Source Data")
    print_token_info(output_tokens, "Output Data")


if __name__ == "__main__":
    main() 