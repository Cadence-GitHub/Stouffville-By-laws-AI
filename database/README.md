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
3. Process each by-law document
4. Create embeddings and store them in ChromaDB
5. Report the total number of by-laws processed

Example output:
```
Initializing embedding function...
Connecting to ChromaDB at localhost:8000...
Successfully connected to ChromaDB collection 'by-laws'!
Found 3 JSON files
Processing parking_related_by-laws.json...
  Creating document for bylaw 2015-139-RE...
  Creating document for bylaw 2015-04-RE...
Adding 2 documents to ChromaDB...
Initialization complete. Added 2 bylaws to ChromaDB.
```

## Expired By-laws Processing

The vector database stores all by-laws, regardless of their status (active, expired, temporary, etc.). This comprehensive approach ensures that:

1. All by-law data remains accessible for historical reference and comparison
2. The application can filter by-laws at query time based on their expiration status
3. Users can compare responses with and without expired by-laws included

While the database itself doesn't filter by-laws during storage, the application implements an optimized two-step filtering process:

1. First, a complete response is generated using all retrieved by-laws
2. Then, a second prompt processes only this first response (not the full by-laws content) to filter out expired by-laws
3. This approach significantly reduces token usage and API costs while maintaining quality

This cost-efficient method allows the application to:
- Use the current date information to determine by-law status
- Focus the second prompt solely on filtering out expired content
- Maintain consistent formatting and style between responses
- Provide side-by-side comparison of responses with and without expired by-laws

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