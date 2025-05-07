# ingest_questions.py
import argparse
import json
import os
import time
from dotenv import load_dotenv
from langchain_voyageai import VoyageAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import chromadb

def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Ingest questions into ChromaDB for autocomplete")
    parser.add_argument("--input", default="AI-generated_Q&A.json", help="Input JSON file with questions")
    parser.add_argument("--api-key", required=False, help="Voyage AI API key")
    parser.add_argument("--chroma-host", default="localhost", help="ChromaDB host")
    parser.add_argument("--chroma-port", default=8000, type=int, help="ChromaDB port")
    parser.add_argument("--collection", default="questions", help="Collection name for questions")
    parser.add_argument("--reset", action="store_true", help="Reset collection if it exists")
    
    args = parser.parse_args()
    
    # Now it's safe to use args
    chroma_host = os.environ.get("CHROMA_HOST", args.chroma_host)
    chroma_port = int(os.environ.get("CHROMA_PORT", args.chroma_port))
    
    # Configure API key
    if args.api_key:
        os.environ["VOYAGE_API_KEY"] = args.api_key
        
    # Initialize embedding function
    print("Initializing Voyage AI embedding function...")
    embedding_function = VoyageAIEmbeddings(model="voyage-3-large")
    
    # Connect to ChromaDB
    print(f"Connecting to ChromaDB at {args.chroma_host}:{args.chroma_port}...")
    chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    
    vector_store = Chroma(
        collection_name=args.collection,
        embedding_function=embedding_function,
        client=chroma_client
    )
    
    # Reset collection if requested
    if args.reset:
        print(f"Resetting collection '{args.collection}'...")
        vector_store.delete_collection()
        vector_store = Chroma(
            collection_name=args.collection,
            embedding_function=embedding_function,
            client=chroma_client
        )
    
    # Load questions from input file
    print(f"Loading questions from {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract questions and answers
    questions_and_answers = data["questions_and_answers"]
    
    # Prepare documents for ChromaDB
    documents = []
    for i, qa in enumerate(questions_and_answers):
        question = qa.get("question", "")
        if not question:
            continue
            
        # Create document with question as content and metadata
        document = Document(
            page_content=question,
            metadata={
                "id": f"question_{i}",
                "question": question,
                "answer": qa.get("answer", "")
            }
        )
        documents.append(document)
    
    # Add documents to vector store
    if documents:
        print(f"Adding {len(documents)} questions to ChromaDB...")
        add_documents_in_batches(vector_store, documents, batch_size=10)
        print(f"Successfully added {len(documents)} questions to ChromaDB")

def add_documents_in_batches(vector_store, documents, batch_size=10):
    """Add documents to the vector store with tiny batches to respect severe rate limits."""
    print(f"Adding {len(documents)} documents in tiny batches of {batch_size}...")
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)...")
        try:
            vector_store.add_documents(batch)
            print(f"Successfully added batch {batch_num}")
            # Add a much longer delay between batches to respect the 3 RPM limit
            print(f"Waiting 25 seconds before next batch...")
            time.sleep(25)
        except Exception as e:
            print(f"Error adding batch {batch_num}: {str(e)}")
            # Wait even longer after an error
            print(f"Error encountered, waiting 60 seconds before retrying...")
            time.sleep(60)
    
if __name__ == "__main__":
    main()