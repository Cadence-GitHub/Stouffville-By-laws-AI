# ChromaDB Initialization for Stouffville By-laws

This document explains how to process and initialize the ChromaDB vector database for the Stouffville By-laws AI application.

## Overview

The database initialization process involves several scripts that process by-law documents from raw JSON files into a structured vector database that enables semantic search capabilities. The process follows these steps:

1. Data preparation with `prepare_json_bylaws_for_db.py` 
2. Expiry analysis with `bylaw_expiry_analyzer.py`
3. Revocation analysis with `bylaw_revocation_analysis.py`
4. Final data enrichment with `prepare_final_json.py`
5. Vector database initialization with `init_chroma.py`
6. Question ingestion for autocomplete with `ingest_questions.py`

## Prerequisites

- A running ChromaDB instance (version 0.6.3 via Docker)
- Voyage AI API key for generating embeddings
- Google API key for Gemini AI (for analysis scripts)
- JSON files containing by-law data in the database directory
- JSON file containing sample questions and answers for autocomplete functionality

## Data Processing Tools

### Data Preparation Tool

The `prepare_json_bylaws_for_db.py` script helps you prepare a subset of JSON by-law files for further processing.

Key features:
- Search by-laws by specific keywords in their metadata
- Filter and collect relevant by-laws into a single output file
- Calculate token usage and estimated LLM costs
- Option to include all by-laws regardless of keywords
- Validate bylaw numbers to ensure they follow the YYYY-NNN format
- Auto-fix invalid bylaw numbers using various correction scenarios
- Generate detailed reports on validation and correction outcomes
- Support for files containing both single bylaw objects and arrays of multiple bylaws
- Handle duplicate bylaws (preferring consolidated versions when available)

Usage:
```bash
python prepare_json_bylaws_for_db.py [KEYWORD] [OPTIONS]
```

Options:
- `KEYWORD`: The keyword to search for in by-laws' keywords field
- `--input`: Directory to search in or a specific JSON file (default: Stouffville_AI/database/By-laws-by-year)
- `--output`: Output file name (default: {keyword}_related_by-laws.json or all_by-laws.json)
- `--exclude-invalid`: Exclude bylaws with invalid bylaw numbers that cannot be fixed

If no keyword is provided, the script will ask if you want to include all by-laws.

The script validates each bylaw number against the standard format (YYYY-NNN) where YYYY is a year and NNN is a three-digit number. If an invalid format is detected, it attempts to auto-fix it using several strategies:
- Adding "19" prefix to two-digit years (71-99)
- Converting space-separated formats (YYYY NNN) to dash format
- Padding numbers with leading zeros to ensure three digits
- Removing spaces in bylaw numbers
- Removing invalid suffixes after the YYYY-NNN format

### Bylaw Expiry Analyzer

The `bylaw_expiry_analyzer.py` script uses the Gemini API to analyze bylaws and determine whether they are still active or have expired based on their content.

Key features:
- Reads bylaw data from JSON files created by the `prepare_json_bylaws_for_db.py` script
- Uses Gemini AI via Langchain to analyze the bylaw text for expiration information
- Adds `isActive` and `whyNotActive` fields to each bylaw
- Separates bylaws into active and inactive output files
- Resumes processing from where it left off if interrupted

Workflow:
1. First use `prepare_json_bylaws_for_db.py` to create a consolidated JSON file of bylaws
2. Then run `bylaw_expiry_analyzer.py` on this file to analyze and classify bylaws
3. The tool produces two output files:
   - `[input_filename].ACTIVE_ONLY.json` containing bylaws that are still active
   - `[input_filename].NOT_ACTIVE_ONLY.json` containing expired bylaws with reasons

Usage:
```bash
python bylaw_expiry_analyzer.py --input [JSON_FILE] [OPTIONS]
```

Options:
- `--input` or `-i`: Input JSON file containing bylaws (required)
- `--model` or `-m`: Gemini model to use (default: gemini-2.0-flash)
- `--limit` or `-l`: Limit number of bylaws to process
- `--env-file` or `-e`: Path to .env file with your GOOGLE_API_KEY

Example:
```bash
python bylaw_expiry_analyzer.py --input parking_related_by-laws.json --model gemini-2.0-flash
```

This tool helps build a more accurate bylaw database by identifying which bylaws are still applicable and which have expired.

### Bylaw Revocation Analyzer

The `bylaw_revocation_analysis.py` script uses the Gemini API to analyze bylaws and identify those that revoke other bylaws.

Key features:
- Reads bylaw data from JSON files created by the `prepare_json_bylaws_for_db.py` script
- Uses Gemini AI via Langchain to identify revocation language in bylaw text
- Detects which bylaws fully revoke, repeal, or replace other bylaws
- Updates the status of revoked bylaws with `isActive=false` and reasons
- Maintains a list of processed bylaws to avoid duplicated work
- Outputs revoked bylaws to a separate file for further processing

Workflow:
1. First use `prepare_json_bylaws_for_db.py` to create a consolidated JSON file of bylaws
2. Then run `bylaw_revocation_analysis.py` on this file to analyze and identify revocation relationships
3. The tool produces three output files:
   - `[input_filename].PROCESSED_FOR_REVOCATION.json` containing bylaws that have been successfully analyzed
   - `[input_filename].REVOKED.json` containing bylaws that have been revoked with reasons
   - `[input_filename].ERRORED.json` containing bylaws that encountered errors during processing (such as when revoked bylaws were not found in the input file)

Usage:
```bash
python bylaw_revocation_analysis.py --input [JSON_FILE] [OPTIONS]
```

Options:
- `--input` or `-i`: Input JSON file containing bylaws (required)
- `--model` or `-m`: Gemini model to use (default: gemini-2.0-flash)
- `--limit` or `-l`: Limit number of bylaws to process
- `--env-file` or `-e`: Path to .env file with your GOOGLE_API_KEY
- `--api-key` or `-k`: Google API key (overrides the key in .env file if provided)

Example:
```bash
python bylaw_revocation_analysis.py --input parking_related_by-laws.json --model gemini-2.0-flash
```

Combined with the Bylaw Expiry Analyzer, this tool creates a more complete picture of which bylaws are active by identifying both expired bylaws and those explicitly revoked by other bylaws.

### Final JSON Preparation Tool

The `prepare_final_json.py` script processes bylaws JSON file and enriches it with status data from auxiliary JSON files created by the previous analysis tools.

Key features:
- Takes the main bylaws JSON file as input
- Loads auxiliary files created by the expiry and revocation analyzers
- Enriches each bylaw with status information (isActive, whyNotActive)
- Creates a final JSON file ready for database import
- Provides a detailed summary of the processing results

Workflow:
1. After running the expiry analyzer and revocation analyzer, run this script to consolidate all information
2. The script reads from these auxiliary files:
   - `[input_filename].NOT_ACTIVE_ONLY.json` (from expiry analyzer)
   - `[input_filename].REVOKED.json` (from revocation analyzer) 
   - `[input_filename].ACTIVE_ONLY.json` (from expiry analyzer)
   - `[input_filename].PROCESSED_FOR_REVOCATION.json` (from revocation analyzer)
3. The script produces one final output file:
   - `[input_filename].FOR_DB.json` containing all bylaws with their complete status information

Usage:
```bash
python prepare_final_json.py [INPUT_FILE]
```

Example:
```bash
python prepare_final_json.py parking_related_by-laws.json
```

The script will generate a summary after completion, showing:
- Total bylaws processed
- Number of bylaws found in each auxiliary file
- Any errors encountered (bylaws not found in auxiliary files)

This tool creates the final data file that should be used for the ChromaDB import process.

### Questions Ingestion Tool

The `ingest_questions.py` script loads a set of questions and answers into ChromaDB for the autocomplete functionality.

Key features:
- Reads question and answer pairs from a JSON file
- Creates vector embeddings using Voyage AI's `voyage-3-large` model
- Stores questions in a separate "questions" collection in ChromaDB
- Handles rate limits by processing in small batches with delays
- Preserves both the question text and answer text as metadata
- Enables semantic search for finding similar questions

Workflow:
1. Create or obtain a JSON file containing question and answer pairs (like `AI-generated_Q&A.json`)
2. Run `ingest_questions.py` to process these questions and add them to ChromaDB
3. The script connects to the ChromaDB instance and creates/updates a collection named "questions"
4. Questions are processed in small batches to respect API rate limits
5. The application's autocomplete endpoint can then use this collection to find semantically similar questions

Usage:
```bash
python ingest_questions.py [OPTIONS]
```

Options:
- `--input`: Input JSON file with questions (default: AI-generated_Q&A.json)
- `--api-key`: Voyage AI API key (can also be set in .env file)
- `--chroma-host`: ChromaDB host (default: localhost)
- `--chroma-port`: ChromaDB port (default: 8000)
- `--collection`: Collection name (default: questions)
- `--reset`: Reset collection if it exists

Example:
```bash
python ingest_questions.py --input AI-generated_Q&A.json --reset
```

Expected Output:
```
Initializing Voyage AI embedding function...
Connecting to ChromaDB at localhost:8000...
Resetting collection 'questions'...
Loading questions from AI-generated_Q&A.json...
Adding 4 questions to ChromaDB...
Processing batch 1/1 (4 documents)...
Successfully added batch 1
Successfully added 4 questions to ChromaDB
```

This tool enables the autocomplete functionality in the application's search interface, which helps users discover relevant questions as they type.

## ChromaDB Integration

### Database Initialization

The `init_chroma.py` script converts by-law documents from JSON files into a vector database that enables semantic search capabilities. It uses Voyage AI embeddings to create high-quality vector representations of each by-law, allowing the application to find relevant by-laws based on natural language queries.

Key Components:

#### Embedding Model

The script uses Voyage AI's `voyage-3-large` model to generate high-quality embeddings for the by-law text. These embeddings capture the semantic meaning of the text, allowing for more intelligent retrieval than simple keyword matching.

#### Document Processing

For each by-law document:
1. The script extracts the text content from the `extractedText` field
2. All other fields are preserved as metadata
3. A unique LangChain Document is created with the text content and metadata
4. The document is added to the ChromaDB collection

#### ChromaDB Integration

The script connects to a running ChromaDB instance (by default at localhost:8000) and:
- Creates or uses an existing collection named "by-laws"
- Uses the Voyage AI embeddings for vector representation
- Stores the complete document metadata for retrieval
- Checks for existing by-laws to avoid duplicates

Usage:

```bash
python init_chroma.py [OPTIONS]
```

Options:

- `--api-key`: Voyage AI API key (alternatively, set in .env file as VOYAGE_API_KEY)
- `--chroma-host`: ChromaDB host (default: localhost)
- `--chroma-port`: ChromaDB port (default: 8000)
- `--collection`: Collection name (default: by-laws)
- `--reset`: Reset collection if it exists
- `--input-file`: Single JSON file to process (like the .FOR_DB.json file from prepare_final_json.py)
- `--json-dir`: Directory containing by-laws JSON files (default: current directory, not used if --input-file is specified)
- `--hnsw-M`: Maximum number of neighbour connections (default: 16)
- `--hnsw-construction_ef`: Number of neighbours in the HNSW graph to explore when adding new vectors (default: 100)
- `--hnsw-search_ef`: Number of neighbours in the HNSW graph to explore when searching (default: 10)

Examples:

Basic usage with the consolidated FOR_DB.json file:
```bash
python init_chroma.py --input-file parking_related_by-laws.FOR_DB.json
```

Reset existing collection and use the consolidated .FOR_DB.json file:
```bash
python init_chroma.py --reset --input-file parking_related_by-laws.FOR_DB.json
```

For backward compatibility, you can still process a directory of JSON files:
```bash
python init_chroma.py --json-dir ./bylaws_data
```

Connect to remote ChromaDB instance:
```bash
python init_chroma.py --chroma-host chroma.example.com --chroma-port 8000 --input-file parking_related_by-laws.FOR_DB.json
```

Expected Output:

The script will:
1. Connect to the ChromaDB instance
2. Load the specified input file or scan the directory for JSON files
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
Processing single input file: parking_related_by-laws.FOR_DB.json...
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

### Direct Bylaw Retrieval

The ChromaDB integration includes a robust function to retrieve specific bylaws by their number:

```python
def retrieve_bylaw_by_number(self, bylaw_number):
    """
    Retrieve a specific bylaw by its number, trying different format variations.
    
    Returns:
        tuple: (bylaw document or None, retrieval_time in seconds, collection_exists)
    """
```

This function:
1. Attempts an exact match using the bylaw number as provided
2. If no match is found, generates multiple format variations:
   - Different spacing around dashes (e.g., "2015-139-RE", "2015 - 139 - RE")
   - Different dash placements for multi-part numbers
   - Completely removing dashes or spaces
3. Searches for each variation until a match is found
4. Returns the complete bylaw metadata along with timing information

This robust matching system ensures users can find bylaws regardless of formatting differences in how the bylaw number is entered.

### Autocomplete Integration

The ChromaDB retriever includes a function for autocomplete suggestions:

```python
def autocomplete_query(self, partial_query, limit=10):
    """
    Find semantically similar questions to the partial query for autocomplete.
    
    Args:
        partial_query (str): The partial query string typed by the user
        limit (int): Maximum number of suggestions to return
            
    Returns:
        tuple: (list of suggestion strings, retrieval_time in seconds, exists_status)
    """
```

This function:
1. Takes a partial query string that the user is typing
2. Requires at least 3 characters to activate
3. Generates embeddings for the partial query using Voyage AI
4. Searches the "questions" collection for semantically similar questions
5. Returns a list of suggested complete questions sorted by relevance
6. Returns timing information for performance monitoring

This functionality powers the autocomplete feature in the application's search interface, helping users discover relevant questions as they type.

### Search Tool

The `search_bylaws.py` script allows you to search the ChromaDB database using semantic search, keyword search, or a combination of both.

Key features:
- Semantic search using natural language queries
- Keyword search within by-law metadata fields
- Search by-laws by their bylaw number (case insensitive)
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
- `--bylaw-number`: Search for bylaws containing this string in their bylaw number (case insensitive)
- `--limit`: Maximum number of results to return (default: 10)
- `--output`: Output file name (default: search_results.json)
- `--api-key`: Voyage AI API key (can also be set in .env file)
- `--chroma-host`: ChromaDB host (default: localhost)
- `--chroma-port`: ChromaDB port (default: 8000)
- `--collection`: Collection name (default: by-laws)
- `--stats`: Display database statistics

At least one of `--query`, `--keyword`, `--bylaw-number`, or `--stats` is required.

## Integration with the Application

After initializing ChromaDB, the Flask application will automatically use it for queries. The application:
1. Attempts to find relevant by-laws using vector search
2. With enhanced search enabled, transforms the user query into legal language and performs dual searches
3. Sends the retrieved by-laws to the Gemini AI model
4. Generates complete, filtered, and layman's terms responses
5. Provides options for users to compare these different responses
6. Allows direct access to specific bylaws through the `/api/bylaw/<bylaw_number>` endpoint
7. Integrates with an interactive bylaw viewer to display comprehensive bylaw information
8. Offers autocomplete suggestions as users type their queries using the "questions" collection

The bylaw viewer uses the direct retrieval function to fetch complete bylaw data and displays it in a user-friendly format with:
- Comprehensive metadata display
- Linked locations (Google Maps integration)
- Original document links
- Formatted content with proper spacing and structure
- Dark mode support for better readability

The autocomplete feature uses the questions collection in ChromaDB to provide intelligent suggestions as users type, improving the user experience and helping users discover relevant questions they might want to ask.

This approach improves response quality and provides users with the most relevant and up-to-date information about Stouffville's by-laws.

## Troubleshooting

If you encounter errors connecting to ChromaDB:
1. Verify that the ChromaDB Docker container is running
2. Check that port 8000 is properly exposed in docker-compose.yaml
3. Ensure your Voyage AI API key is valid and has sufficient quota
4. Verify you're using the correct ChromaDB version (0.6.3) 

If the autocomplete functionality is not working:
1. Make sure you've run `ingest_questions.py` to populate the "questions" collection
2. Check that the "questions" collection exists in ChromaDB
3. Verify that your input has at least 3 characters (shorter queries return empty results) 