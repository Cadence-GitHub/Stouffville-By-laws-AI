# ChromaDB Initialization for Stouffville By-laws

This document explains how the `init_chroma.py` script works to initialize the ChromaDB vector database for the Stouffville By-laws AI application.

## Overview

The `init_chroma.py` script converts by-law documents from JSON files into a vector database that enables semantic search capabilities. It uses Voyage AI embeddings to create high-quality vector representations of each by-law, allowing the application to find relevant by-laws based on natural language queries.

## Prerequisites

- A running ChromaDB instance (version 0.6.3 via Docker)
- Voyage AI API key for generating embeddings
- JSON files containing by-law data in the database directory

## Key Components

### Embedding Model

The script uses Voyage AI's `voyage-3-large` model to generate high-quality embeddings for the by-law text. These embeddings capture the semantic meaning of the text, allowing for more intelligent retrieval than simple keyword matching.

### Document Processing

For each by-law document:
1. The script extracts the text content from the `extractedText` field
2. All other fields are preserved as metadata
3. A unique LangChain Document is created with the text content and metadata
4. The document is added to the ChromaDB collection

### ChromaDB Integration

The script connects to a running ChromaDB instance (by default at localhost:8000) and:
- Creates or uses an existing collection named "by-laws"
- Uses the Voyage AI embeddings for vector representation
- Stores the complete document metadata for retrieval
- Checks for existing by-laws to avoid duplicates

## Usage

```bash
python init_chroma.py [OPTIONS]
```

### Options

- `--api-key`: Voyage AI API key (alternatively, set in .env file as VOYAGE_API_KEY)
- `--chroma-host`: ChromaDB host (default: localhost)
- `--chroma-port`: ChromaDB port (default: 8000)
- `--collection`: Collection name (default: by-laws)
- `--reset`: Reset collection if it exists
- `--json-dir`: Directory containing by-laws JSON files (default: current directory)
- `--hnsw-M`: Maximum number of neighbour connections (default: 16)
- `--hnsw-construction_ef`: Number of neighbours in the HNSW graph to explore when adding new vectors (default: 100)
- `--hnsw-search_ef`: Number of neighbours in the HNSW graph to explore when searching (default: 10)

### Examples

Basic usage with defaults:
```bash
python init_chroma.py
```

Reset existing collection and specify JSON directory:
```bash
python init_chroma.py --reset --json-dir ./bylaws_data
```

Connect to remote ChromaDB instance:
```bash
python init_chroma.py --chroma-host chroma.example.com --chroma-port 8000
```

## Expected Output

The script will:
1. Connect to the ChromaDB instance
2. Find all JSON files in the specified directory
3. Check existing by-laws in the collection to avoid duplicates
4. Process each by-law document, skipping those already in the database
5. Create embeddings and store only new by-laws in ChromaDB
6. Process documents in batches to avoid memory issues
7. Report the total number of by-laws processed and added
8. Display database statistics including total documents, unique bylaws, bylaw types, and years

Example output:
```
Initializing embedding function...
Connecting to ChromaDB at localhost:8000...
Successfully connected to ChromaDB collection 'by-laws'!
Found 2 existing bylaws in the collection
Found 3 JSON files
Processing parking_related_by-laws.json...
  Creating document for bylaw 2015-139-RE...
  Skipping bylaw 2015-04-RE - already exists in collection
Adding 1 document to ChromaDB...
Processing batch 1/1 (1 documents)...
Initialization complete. Added/updated 1 bylaws in ChromaDB.
Database Statistics:
Total Documents: 3
Unique Bylaws: 3
Bylaw Types:
  - PARKING: 2
  - GENERAL: 1
Bylaw Years:
  - 2015: 2
  - 2018: 1
```

## Troubleshooting

If you encounter errors connecting to ChromaDB:
1. Verify that the ChromaDB Docker container is running
2. Check that port 8000 is properly exposed in docker-compose.yaml
3. Ensure your Voyage AI API key is valid and has sufficient quota
4. Verify you're using the correct ChromaDB version (0.6.3)

## Integration with the Application

After initializing ChromaDB, the Flask application will automatically use it for queries. The application:
1. Attempts to find relevant by-laws using vector search
2. Sends the retrieved by-laws to the Gemini AI model
3. Generates both complete and filtered responses based on by-law status
4. Provides options for users to compare these different responses

This approach improves response quality and provides users with the most relevant and up-to-date information about Stouffville's by-laws. 

## Related Tools

### Data Preparation Tool

The `prepare_json_bylaws_for_db.py` script helps you prepare a subset of JSON by-law files for further processing by the `init_chroma.py` script.

Key features:
- Search by-laws by specific keywords in their metadata
- Filter and collect relevant by-laws into a single output file
- Calculate token usage and estimated LLM costs
- Option to include all by-laws regardless of keywords

Usage:
```bash
python prepare_json_bylaws_for_db.py [KEYWORD] [OPTIONS]
```

Options:
- `KEYWORD`: The keyword to search for in by-laws' keywords field
- `--dir`: Directory to search in (default: Stouffville_AI/database/By-laws-by-year)
- `--output`: Output file name (default: {keyword}_related_by-laws.json or all_by-laws.json)

If no keyword is provided, the script will ask if you want to include all by-laws.

### Search Tool

The `search_bylaws.py` script allows you to search the ChromaDB database using semantic search, keyword search, or a combination of both.

Key features:
- Semantic search using natural language queries
- Keyword search within by-law metadata fields
- Display database statistics including by-law types and years
- Calculate token usage and estimated LLM costs
- Save search results to a JSON file

Usage:
```bash
python search_bylaws.py [OPTIONS]
```

Options:
- `--query`: Natural language query for semantic search
- `--keyword`: Keyword to search for in by-law metadata
- `--limit`: Maximum number of results to return (default: 10)
- `--output`: Output file name (default: search_results.json)
- `--api-key`: Voyage AI API key (can also be set in .env file)
- `--chroma-host`: ChromaDB host (default: localhost)
- `--chroma-port`: ChromaDB port (default: 8000)
- `--collection`: Collection name (default: by-laws)
- `--stats`: Display database statistics

At least one of `--query`, `--keyword`, or `--stats` is required. 