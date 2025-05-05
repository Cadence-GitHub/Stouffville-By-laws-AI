#!/usr/bin/env python3
"""
Search by-laws using ChromaDB with LangChain integration.

This script connects to a ChromaDB instance and allows searching by-laws using:
1. Semantic search with natural language queries
2. Keyword search within metadata fields
3. Combined search with both methods
4. Search by bylaw number (case insensitive)

Results are displayed with relevance scores and can be saved to a JSON file.

Usage:
    python search_bylaws.py --query "parking regulations" --output results.json
    python search_bylaws.py --keyword "parking" --output results.json
    python search_bylaws.py --query "parking regulations" --keyword "parking" --output results.json
    python search_bylaws.py --bylaw-number "33" --output results.json

Requirements:
    - langchain-chroma
    - langchain-voyageai
    - chromadb
    - python-dotenv
"""

import os
import json
import argparse
import re
from pathlib import Path
import tiktoken
from dotenv import load_dotenv
from langchain_voyageai import VoyageAIEmbeddings
from langchain_chroma import Chroma
import chromadb

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

def search_bylaws(args):
    """
    Search through bylaws using ChromaDB with both semantic and keyword search capabilities.
    
    Args:
        args: Command-line arguments parsed by argparse
        
    Returns:
        list: List of matching by-law documents
        int: Total token count of the results
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Use API key from command line if provided, otherwise use from .env
    if args.api_key:
        os.environ["VOYAGE_API_KEY"] = args.api_key
    elif not os.environ.get("VOYAGE_API_KEY"):
        print("Error: VOYAGE_API_KEY not found in environment variables or command line arguments")
        print("Please either provide --api-key parameter or set VOYAGE_API_KEY in your .env file")
        return [], 0
    
    # Initialize embedding function
    print("Initializing embedding function...")
    embedding_function = VoyageAIEmbeddings(model="voyage-3-large")
    
    # Connect to ChromaDB server
    print(f"Connecting to ChromaDB at {args.chroma_host}:{args.chroma_port}...")
    
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.HttpClient(host=args.chroma_host, port=args.chroma_port)
        
        # Connect to the collection using LangChain's Chroma integration
        vector_store = Chroma(
            collection_name=args.collection,
            embedding_function=embedding_function,
            client=chroma_client
        )
        
        print(f"Successfully connected to ChromaDB collection '{args.collection}'!")
        
    except Exception as e:
        print(f"Error connecting to ChromaDB: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure the Docker container with ChromaDB is running")
        print("2. Ensure port 8000 is properly exposed in docker-compose.yaml")
        return [], 0
    
    matching_bylaws = []
    
    # Perform semantic search if a query is provided
    if args.query:
        print(f"\nPerforming semantic search for: '{args.query}'")
        
        # Use similarity_search_with_score to get both documents and scores
        results = vector_store.similarity_search_with_score(
            query=args.query,
            k=args.limit
        )
        
        if results:
            print(f"Found {len(results)} relevant documents")
            
            for doc, score in results:
                # Extract the document content and metadata
                bylaw_data = {
                    "page_content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": float(score)  # Convert to float for JSON serialization
                }
                
                # Store the result
                matching_bylaws.append(bylaw_data)
                
                # Display some information about the match
                bylaw_id = doc.metadata.get("bylawNumber", "Unknown ID")
                bylaw_type = doc.metadata.get("bylawType", "Unknown Type")
                
                print(f"\nFound match: {bylaw_id} ({bylaw_type})")
                print(f"Relevance score: {score:.4f}")
                print(f"Keywords: {doc.metadata.get('keywords', [])}")
        else:
            print("No matches found for the semantic search query.")
    
    # Perform keyword search if a keyword is provided
    if args.keyword:
        print(f"\nPerforming keyword search for: '{args.keyword}'")
        
        # ChromaDB doesn't support $contains - let's use a different approach
        # First, retrieve all documents and filter locally
        print("Retrieving documents from ChromaDB to perform keyword search...")
        all_results = vector_store.get()
        
        keyword_matches = []
        docs = all_results.get("documents", [])
        metadatas = all_results.get("metadatas", [])
        ids = all_results.get("ids", [])
        
        keyword_lower = args.keyword.lower()
        
        # Manually filter documents based on metadata
        for i in range(len(docs)):
            metadata = metadatas[i]
            found_match = False
            
            # Check in keywords field - handle both list and string formats
            if "keywords" in metadata:
                # Handle keywords as a list
                if isinstance(metadata["keywords"], list):
                    for kw in metadata["keywords"]:
                        if isinstance(kw, str) and keyword_lower in kw.lower():
                            found_match = True
                            break
                # Handle keywords as a space-separated string
                elif isinstance(metadata["keywords"], str):
                    if keyword_lower in metadata["keywords"].lower():
                        found_match = True
            
            # Check in other text fields
            if not found_match:
                for field in ["bylawHeader", "bylawType", "condtionsAndClauses"]:
                    if field in metadata and isinstance(metadata[field], str):
                        if keyword_lower in metadata[field].lower():
                            found_match = True
                            break
            
            if found_match:
                keyword_matches.append({
                    "document": docs[i],
                    "metadata": metadata,
                    "id": ids[i]
                })
        
        # Process the keyword matches
        if keyword_matches:
            # Limit the number of results if necessary
            keyword_matches = keyword_matches[:args.limit]
            print(f"Found {len(keyword_matches)} documents matching the keyword")
            
            for match in keyword_matches:
                # Create a document with metadata
                bylaw_data = {
                    "page_content": match["document"],
                    "metadata": match["metadata"],
                    "id": match["id"]
                }
                
                # Only add if not already in results (to avoid duplicates when using both search methods)
                if not any(b.get("metadata", {}).get("id") == match["metadata"].get("id") for b in matching_bylaws):
                    matching_bylaws.append(bylaw_data)
                    
                    # Display some information about the match
                    bylaw_id = match["metadata"].get("bylawNumber", "Unknown ID")
                    bylaw_type = match["metadata"].get("bylawType", "Unknown Type")
                    
                    print(f"\nFound match: {bylaw_id} ({bylaw_type})")
                    print(f"Keywords: {match['metadata'].get('keywords', [])}")
        else:
            print("No matches found for the keyword search.")
    
    # Perform bylaw number search if a bylaw number string is provided
    if args.bylaw_number:
        print(f"\nPerforming bylaw number search for: '{args.bylaw_number}'")
        
        # Retrieve all documents and filter locally
        print("Retrieving documents from ChromaDB to perform bylaw number search...")
        all_results = vector_store.get()
        
        bylaw_number_matches = []
        docs = all_results.get("documents", [])
        metadatas = all_results.get("metadatas", [])
        ids = all_results.get("ids", [])
        
        bylaw_number_lower = args.bylaw_number.lower()
        
        # Manually filter documents based on bylaw number
        for i in range(len(docs)):
            metadata = metadatas[i]
            
            # Check if bylawNumber contains the search string (case insensitive)
            if "bylawNumber" in metadata and isinstance(metadata["bylawNumber"], str):
                if bylaw_number_lower in metadata["bylawNumber"].lower():
                    bylaw_number_matches.append({
                        "document": docs[i],
                        "metadata": metadata,
                        "id": ids[i]
                    })
        
        # Process the bylaw number matches
        if bylaw_number_matches:
            # Limit the number of results if necessary
            bylaw_number_matches = bylaw_number_matches[:args.limit]
            print(f"Found {len(bylaw_number_matches)} documents matching the bylaw number")
            
            for match in bylaw_number_matches:
                # Create a document with metadata
                bylaw_data = {
                    "page_content": match["document"],
                    "metadata": match["metadata"],
                    "id": match["id"]
                }
                
                # Only add if not already in results (to avoid duplicates when using multiple search methods)
                if not any(b.get("metadata", {}).get("id") == match["metadata"].get("id") for b in matching_bylaws):
                    matching_bylaws.append(bylaw_data)
                    
                    # Display some information about the match
                    bylaw_id = match["metadata"].get("bylawNumber", "Unknown ID")
                    bylaw_type = match["metadata"].get("bylawType", "Unknown Type")
                    
                    print(f"\nFound match: {bylaw_id} ({bylaw_type})")
                    print(f"Keywords: {match['metadata'].get('keywords', [])}")
        else:
            print("No matches found for the bylaw number search.")
    
    # Write results to the output file
    if matching_bylaws:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(matching_bylaws, f, indent=2, ensure_ascii=False)
        
        print(f"\nTotal matching bylaws: {len(matching_bylaws)}")
        print(f"Results saved to: {args.output}")
    else:
        print("\nNo matching bylaws found.")
    
    # Calculate token count and costs
    output_str = json.dumps(matching_bylaws, indent=2, ensure_ascii=False)
    total_tokens = count_tokens(output_str)
    
    return matching_bylaws, total_tokens

def get_database_stats(args):
    """
    Get and display statistics about the bylaw vector database.
    
    Args:
        args: Command-line arguments parsed by argparse
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Use API key from command line if provided, otherwise use from .env
    if args.api_key:
        os.environ["VOYAGE_API_KEY"] = args.api_key
    
    # Initialize embedding function
    embedding_function = VoyageAIEmbeddings(model="voyage-3-large")
    
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.HttpClient(host=args.chroma_host, port=args.chroma_port)
        
        # Connect to the collection using LangChain's Chroma integration
        vector_store = Chroma(
            collection_name=args.collection,
            embedding_function=embedding_function,
            client=chroma_client
        )
        
        # Get all metadata to analyze collection contents
        results = vector_store._collection.get()
        
        total_docs = vector_store._collection.count()
        unique_bylaws = set()
        bylaw_types = {}
        bylaw_years = {}
        
        for metadata in results.get("metadatas", []):
            if metadata and "bylawNumber" in metadata:
                unique_bylaws.add(metadata["bylawNumber"])
            
            if metadata and "bylawType" in metadata:
                bylaw_type = metadata["bylawType"]
                bylaw_types[bylaw_type] = bylaw_types.get(bylaw_type, 0) + 1
            
            if metadata and "bylawYear" in metadata:
                bylaw_year = metadata["bylawYear"]
                bylaw_years[bylaw_year] = bylaw_years.get(bylaw_year, 0) + 1
        
        # Sort years chronologically and types by frequency
        sorted_years = dict(sorted(bylaw_years.items()))
        sorted_types = dict(sorted(bylaw_types.items(), key=lambda x: x[1], reverse=True))
        
        print("\nDatabase Statistics:")
        print(f"Total Documents: {total_docs}")
        print(f"Unique Bylaws: {len(unique_bylaws)}")
        print("Bylaw Types:")
        for bylaw_type, count in sorted_types.items():
            print(f"  - {bylaw_type}: {count}")
        print("Bylaw Years:")
        for year, count in sorted_years.items():
            print(f"  - {year}: {count}")
            
    except Exception as e:
        print(f"Error getting database statistics: {str(e)}")

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
    parser = argparse.ArgumentParser(description='Search bylaws using ChromaDB')
    
    # Search parameters
    search_group = parser.add_argument_group('Search Parameters')
    search_group.add_argument('--query', help='Natural language query for semantic search')
    search_group.add_argument('--keyword', help='Keyword to search for in bylaw metadata')
    search_group.add_argument('--bylaw-number', help='Search for bylaws containing this string in their bylaw number (case insensitive)')
    search_group.add_argument('--limit', type=int, default=10, help='Maximum number of results to return (default: 10)')
    search_group.add_argument('--output', default='search_results.json', help='Output file name (default: search_results.json)')
    
    # ChromaDB connection parameters
    db_group = parser.add_argument_group('ChromaDB Connection')
    db_group.add_argument('--api-key', help='Voyage AI API key for embeddings (can also be set in .env file)')
    db_group.add_argument('--chroma-host', default='localhost', help='ChromaDB host (default: localhost)')
    db_group.add_argument('--chroma-port', default=8000, type=int, help='ChromaDB port (default: 8000)')
    db_group.add_argument('--collection', default='by-laws', help='Collection name (default: by-laws)')
    
    # Other functionality
    other_group = parser.add_argument_group('Other Functionality')
    other_group.add_argument('--stats', action='store_true', help='Display database statistics')
    
    args = parser.parse_args()
    
    # Check if at least one search parameter or --stats is provided
    if not (args.query or args.keyword or args.bylaw_number or args.stats):
        parser.error("At least one of --query, --keyword, --bylaw-number, or --stats is required")
    
    # Show database statistics if requested
    if args.stats:
        get_database_stats(args)
        return
    
    # Perform the search
    _, total_tokens = search_bylaws(args)
    
    # Display token count and cost information if results were found
    if total_tokens > 0:
        print(f"\nToken Information:")
        print(f"Total tokens: {total_tokens:,}")
        
        print("\nEstimated LLM costs:")
        costs = calculate_llm_costs(total_tokens)
        for model, cost in costs.items():
            print(f"  {model} (${costs[model]:.2f}/million tokens): ${cost:.4f}")

if __name__ == "__main__":
    main()
    