#!/usr/bin/env python3
import os
import json
import argparse
import re
from pathlib import Path


def count_tokens(text):
    """
    Estimate token count using a simple approximation.
    This uses a rough estimate of 4 characters per token, which is common for English text.
    
    Args:
        text (str): The text to count tokens for
        
    Returns:
        int: Estimated token count
    """
    if not text:
        return 0
    
    # Convert to string if it's not already
    if not isinstance(text, str):
        text = json.dumps(text)
        
    # Approximate token count (English text averages ~4 chars per token)
    return len(text) // 4


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
        int: Total token count of the output file
    """
    # Create or clear the output file
    output_data = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
        except json.JSONDecodeError:
            output_data = []
    
    base_path = Path(base_dir)
    matching_files = []
    
    # Walk through all JSON files in the directory and subdirectories
    for json_file in base_path.glob('**/*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                bylaw_data = json.load(f)
                
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
    
    print(f"\nTotal matching files: {len(matching_files)}")
    print(f"Results saved to: {output_file}")
    
    # Calculate token count and costs
    output_str = json.dumps(output_data, indent=2, ensure_ascii=False)
    total_tokens = count_tokens(output_str)
    
    return total_tokens


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


def main():
    parser = argparse.ArgumentParser(description='Search bylaws by keyword')
    parser.add_argument('keyword', help='Keyword to search for in bylaw keywords')
    parser.add_argument('--dir', default='Stouffville_AI/database/By-laws-by-year', 
                        help='Directory to search in (default: Stouffville_AI/database/By-laws-by-year)')
    parser.add_argument('--output', default='parking_related_by-laws.json',
                        help='Output file name (default: parking_related_by-laws.json)')
    
    args = parser.parse_args()
    
    total_tokens = search_bylaws_by_keyword(args.dir, args.keyword, args.output)
    
    # Display token count and cost information
    print(f"\nToken Information:")
    print(f"Total tokens: {total_tokens:,}")
    
    print("\nEstimated LLM costs:")
    costs = calculate_llm_costs(total_tokens)
    for model, cost in costs.items():
        print(f"  {model} (${costs[model]:.2f}/million tokens): ${cost:.4f}")


if __name__ == "__main__":
    main() 