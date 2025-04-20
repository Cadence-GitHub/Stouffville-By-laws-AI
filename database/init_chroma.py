#!/usr/bin/env python3
"""
Initialize ChromaDB with by-laws data using LangChain integration.

This script loads by-laws from JSON files in the database directory and creates embeddings 
using the 'extractedText' field while storing all other fields as metadata.

Usage:
    python init_chroma.py

Requirements:
    - langchain-chroma
    - langchain-voyageai
    - chromadb
    - python-dotenv
"""

import argparse
import json
import os
import glob
import time
from dotenv import load_dotenv
from langchain_voyageai import VoyageAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import chromadb

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Initialize ChromaDB with by-laws data")
    parser.add_argument("--api-key", required=False, help="Voyage AI API key for embeddings (can also be set in .env file)")
    parser.add_argument("--chroma-host", default="localhost", help="ChromaDB host")
    parser.add_argument("--chroma-port", default=8000, type=int, help="ChromaDB port")
    parser.add_argument("--collection", default="by-laws", help="Collection name")
    parser.add_argument("--reset", action="store_true", help="Reset collection if it exists")
    parser.add_argument("--json-dir", default=".", help="Directory containing by-laws JSON files")
    parser.add_argument("--hnsw-M", default="16", help="Maximum number of neighbour connections")
    parser.add_argument("--hnsw-construction_ef", default="100", help="Number of neighbours in the HNSW graph to explore when adding new vectors")
    parser.add_argument("--hnsw-search_ef", default="10", help="Number of neighbours in the HNSW graph to explore when searching")
    
    args = parser.parse_args()
    
    # Use API key from command line if provided, otherwise use from .env
    if args.api_key:
        os.environ["VOYAGE_API_KEY"] = args.api_key
    elif not os.environ.get("VOYAGE_API_KEY"):
        print("Error: VOYAGE_API_KEY not found in environment variables or command line arguments")
        print("Please either provide --api-key parameter or set VOYAGE_API_KEY in your .env file")
        return
    
    # Initialize embedding function
    print("Initializing embedding function...")
    embedding_function = VoyageAIEmbeddings(model="voyage-3-large")
    
    # Connect to ChromaDB server using LangChain's Chroma integration
    print(f"Connecting to ChromaDB at {args.chroma_host}:{args.chroma_port}...")
    
    try:
        # Initialize LangChain's Chroma client
        # For server connection, need to use chromadb.HttpClient instead of client_settings
        chroma_client = chromadb.HttpClient(host=args.chroma_host, port=args.chroma_port)
        
        vector_store = Chroma(
            collection_name=args.collection,
            embedding_function=embedding_function,
            client=chroma_client,
            collection_metadata={"hnsw:M": args.hnsw_M, "hnsw:construction_ef": args.hnsw_construction_ef, "hnsw:search_ef": args.hnsw_search_ef}
        )
        
        # If reset flag is set, clear the collection
        if args.reset:
            print(f"Resetting collection '{args.collection}'...")
            vector_store.delete_collection()
            # Reinitialize after deletion
            vector_store = Chroma(
                collection_name=args.collection,
                embedding_function=embedding_function,
                client=chroma_client
            )
            
        print(f"Successfully connected to ChromaDB collection '{args.collection}'!")
        
        # Get existing bylaw IDs from the collection
        existing_bylaws = set()
        try:
            collection_data = vector_store.get()
            # Extract ID values from metadata
            for metadata in collection_data.get('metadatas', []):
                if metadata and 'id' in metadata:
                    existing_bylaws.add(metadata['id'])
            print(f"Found {len(existing_bylaws)} existing bylaws in the collection")
        except Exception as e:
            print(f"Error getting existing bylaws: {str(e)}")
            existing_bylaws = set()
        
    except Exception as e:
        print(f"Error connecting to ChromaDB: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure the Docker container with ChromaDB is running")
        print("2. Ensure port 8000 is properly exposed in docker-compose.yaml")
        return
    
    # Find all JSON files
    json_pattern = os.path.join(args.json_dir, "*.json")
    json_files = glob.glob(json_pattern)
    print(f"Found {len(json_files)} JSON files")
    
    # Process each file
    total_bylaws = 0
    documents = []
    document_ids = []
    
    for json_file in json_files:
        print(f"Processing {os.path.basename(json_file)}...")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        # Handle both single bylaw and list of bylaws
        bylaws = file_content if isinstance(file_content, list) else [file_content]
        
        for bylaw in bylaws:
            # Use bylawNumber directly as the document ID
            bylaw_id = bylaw.get("bylawNumber", "unknown")
            
            # Extract the text to be embedded - only the extractedText field
            if "extractedText" in bylaw:
                if isinstance(bylaw["extractedText"], list):
                    # Join the list of text elements into a single string
                    text_to_embed = " ".join(bylaw["extractedText"])
                else:
                    text_to_embed = bylaw["extractedText"]
                
                # Create metadata from all bylaw fields
                metadata = {}
                for k, v in bylaw.items():
                    if k != "extractedText": #Do not add embedded text to metadata
                        # Convert lists to strings for metadata
                        if isinstance(v, list):
                            metadata[k] = " ".join(str(item) for item in v)
                        elif isinstance(v, (str, int, float, bool)) or v is None:
                            metadata[k] = v
                        else:
                            # Convert other complex types to strings
                            metadata[k] = str(v)
                
                # Set ID in metadata for retrieval
                metadata["id"] = bylaw_id
                
                print(f"  Creating document for bylaw {bylaw_id}...")
                
                # Create LangChain Document
                document = Document(
                    page_content=text_to_embed,
                    metadata=metadata
                )
                
                if bylaw_id in existing_bylaws:
                    print(f"  Skipping bylaw {bylaw_id} - already exists in collection")
                    continue
                
                documents.append(document)
                total_bylaws += 1
            else:
                print(f"  Warning: Bylaw {bylaw_id} has no extractedText field, skipping")
    
    # Add documents to the vector store in batches to avoid memory issues
    if documents:
        print(f"Adding {len(documents)} documents to ChromaDB...")
        
        # Define batch size
        batch_size = 100
        total_batches = (len(documents) + batch_size - 1) // batch_size  # Ceiling division
        
        try:
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                batch_ids = document_ids[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} documents)...")
                vector_store.add_documents(batch)
                # Small delay to avoid overwhelming the server
                time.sleep(0.5)
            
            print(f"Initialization complete. Added/updated {total_bylaws} bylaws in ChromaDB.")
        except Exception as e:
            print(f"Error adding documents to ChromaDB: {str(e)}")
    else:
        print("No valid documents found to add to ChromaDB.")

    get_stats(vector_store)
 

def get_stats(self) :
        """
        Get statistics about the bylaw vector database.
        
        Returns:
            Dictionary with statistics
        """
        total_docs = self._collection.count()
        
        # Get all metadata to analyze collection contents
        results = self._collection.get()
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
        
        print("Database Statistics:")
        print(f"Total Documents: {total_docs}")
        print(f"Unique Bylaws: {len(unique_bylaws)}")
        print("Bylaw Types:")
        for bylaw_type, count in sorted_types.items():
            print(f"  - {bylaw_type}: {count}")
        print("Bylaw Years:")
        for year, count in sorted_years.items():
            print(f"  - {year}: {count}")

   
if __name__ == "__main__":
    main()

