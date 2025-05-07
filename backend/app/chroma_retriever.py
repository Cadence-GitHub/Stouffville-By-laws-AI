from langchain_chroma import Chroma
import os
import chromadb
from langchain_voyageai import VoyageAIEmbeddings
import re
import time

class ChromaDBRetriever:
    """
    A lightweight retriever class for ChromaDB operations, focused only on retrieving data.
    This class does not modify the database - it's designed for read-only operations.
    """
    
    def __init__(self):
        # Get ChromaDB connection details from environment or use defaults
        self.chroma_host = os.environ.get("CHROMA_HOST", "localhost")
        self.chroma_port = int(os.environ.get("CHROMA_PORT", "8000"))
        
        # Initialize the embedding function - using the Voyage AI model
        self.embedding_function = VoyageAIEmbeddings(model="voyage-3-large")
        
        # Collection name for by-laws
        self.collection_name = "by-laws"
        
        # Initialize vector store
        try:
            # Create the ChromaDB client
            chroma_client = chromadb.HttpClient(host=self.chroma_host, port=self.chroma_port)
            
            # Connect to the existing ChromaDB collection
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_function,
                client=chroma_client
            )
            print(f"Successfully connected to ChromaDB collection '{self.collection_name}'")
        except Exception as e:
            print(f"Error connecting to ChromaDB: {str(e)}")
            # Create a fallback empty collection if needed
            self.vector_store = None
    
    def retrieve_relevant_bylaws(self, query, limit=10):
        """
        Retrieve by-laws relevant to the query.
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            
        Returns:
            tuple: (list of by-law documents with their metadata, retrieval_time in seconds, exists_status)
                   where exists_status is a boolean indicating if the collection exists and has documents
        """
        if not self.vector_store:
            print("ChromaDB connection not available")
            return [], 0, False
            
        try:
            # Start timing the retrieval
            start_time = time.time()
            
            # Use similarity_search without filter to improve performance, then filter in memory
            raw_documents = self.vector_store.similarity_search(
                query,
                k=limit * 5  # Retrieve more documents than needed to ensure we have enough after filtering
            )
            
            # Filter documents in memory: include docs with isActive=True OR docs without isActive field
            documents = [doc for doc in raw_documents if "isActive" not in doc.metadata or doc.metadata["isActive"]][:limit]
            
            # Calculate retrieval time
            retrieval_time = time.time() - start_time
            
            # Process the results
            results = []
            for doc in documents:
                # Extract the by-law data from metadata
                bylaw_data = doc.metadata
                
                # Also add the page content separately if needed
                bylaw_data["content"] = doc.page_content
                
                # Remove keywords field from each bylaw
                if "keywords" in bylaw_data:
                    del bylaw_data["keywords"]
                
                # Remove isActive, whyNotActive, urlOriginalDocument, bylawHeader, newsSources, entityAndDesignation and bylawFileName fields from each bylaw
                if "isActive" in bylaw_data:
                    del bylaw_data["isActive"]
                if "whyNotActive" in bylaw_data:
                    del bylaw_data["whyNotActive"]
                if "bylawFileName" in bylaw_data:
                    del bylaw_data["bylawFileName"]
                if "urlOriginalDocument" in bylaw_data:
                    del bylaw_data["urlOriginalDocument"]
                if "bylawHeader" in bylaw_data:
                    del bylaw_data["bylawHeader"]
                if "newsSources" in bylaw_data:
                    del bylaw_data["newsSources"]
                if "entityAndDesignation" in bylaw_data:
                    del bylaw_data["entityAndDesignation"]


                results.append(bylaw_data)
            
            # Return the results and a flag indicating the collection exists
            return results, retrieval_time, True
            
        except Exception as e:
            print(f"Error retrieving bylaws: {str(e)}")
            return [], 0, False
    
    def retrieve_bylaw_by_number(self, bylaw_number):
        """
        Retrieve a specific bylaw by its number, trying different format variations.
        
        Returns:
            tuple: (bylaw document or None, retrieval_time in seconds, collection_exists)
        """
        if not self.vector_store:
            return None, 0, False
            
        try:
            start_time = time.time()
            
            # Get the direct collection access
            collection = self.vector_store._collection
            
            # Try the original format first (fastest when it works)
            direct_match = collection.get(
                where={"bylawNumber": bylaw_number},
                limit=1
            )
            
            # If exact match found, return it
            if direct_match and direct_match['metadatas'] and len(direct_match['metadatas']) > 0:
                bylaw_data = direct_match['metadatas'][0]
                if 'documents' in direct_match and direct_match['documents']:
                    bylaw_data["content"] = direct_match['documents'][0]
                    
                return bylaw_data, time.time() - start_time, True
            
            # Generate variations of the bylaw number format
            variations = []
            
            # Check if we have multiple parts separated by dashes
            if '-' in bylaw_number:
                # Split on dash and clean up each part
                parts = [part.strip() for part in bylaw_number.split('-')]
                
                # Handle both simple formats (like "72-17") and complex ones (like "2001-01-LI")
                if len(parts) == 2:  # Simple case: number-number
                    variations = [
                        f"{parts[0]}-{parts[1]}",       # No spaces
                        f"{parts[0]} -{parts[1]}",      # Space before dash
                        f"{parts[0]}- {parts[1]}",      # Space after dash
                        f"{parts[0]} - {parts[1]}"      # Spaces on both sides
                    ]
                elif len(parts) >= 3:  # Complex case: number-number-letter or more parts
                    # For three parts (like "2001-01-LI")
                    variations = [
                        f"{parts[0]}-{parts[1]}-{parts[2]}",         # No spaces
                        f"{parts[0]} - {parts[1]} - {parts[2]}",     # Spaces around dashes
                        f"{parts[0]}-{parts[1]} - {parts[2]}",       # Mixed spaces
                        f"{parts[0]} - {parts[1]}-{parts[2]}",       # Mixed spaces
                        f"{parts[0]}-{parts[1]}-{parts[2]}",         # No spaces
                        # Join all parts with spaces around dashes
                        " - ".join(parts)
                    ]
                    
                    # Also try without any dashes for cases where spaces are used instead
                    variations.append(" ".join(parts))
                    
                # Add variations where all dashes are replaced by spaces
                no_dash_version = bylaw_number.replace('-', ' ')
                variations.append(no_dash_version)
                
                # Also try completely removing spaces and dashes
                compact_version = bylaw_number.replace('-', '').replace(' ', '')
                variations.append(compact_version)
            else:
                # If there are no dashes, try adding them between groups of numbers/letters
                # For formats like "72 17" that might be in database as "72-17"
                parts = bylaw_number.split()
                if len(parts) == 2:
                    variations = [
                        f"{parts[0]}-{parts[1]}",       # With dash
                        f"{parts[0]} - {parts[1]}"      # With dash and spaces
                    ]
            
            # Try each variation
            for variant in variations:
                if variant == bylaw_number:  # Skip if already tried
                    continue
                    
                variant_match = collection.get(
                    where={"bylawNumber": variant},
                    limit=1
                )
                
                if variant_match and variant_match['metadatas'] and len(variant_match['metadatas']) > 0:
                    bylaw_data = variant_match['metadatas'][0]
                    if 'documents' in variant_match and variant_match['documents']:
                        bylaw_data["content"] = variant_match['documents'][0]
                        
                    print(f"Found bylaw via variation match: '{bylaw_data.get('bylawNumber')}'")
                    return bylaw_data, time.time() - start_time, True
            
            # If we got here, no match was found
            return None, time.time() - start_time, True
            
        except Exception as e:
            return None, 0, False
    
    def autocomplete_query(self, partial_query, limit=10):
        """
        Find semantically similar questions to the partial query for autocomplete.
        
        Args:
            partial_query (str): The partial query string typed by the user
            limit (int): Maximum number of suggestions to return
                
        Returns:
            tuple: (list of suggestion strings, retrieval_time in seconds, exists_status)
        """
        if not self.embedding_function:
            print("Embedding function not available")
            return [], 0, False
                
        try:
            # Start timing the retrieval
            start_time = time.time()
            
            # Create a client for the questions collection
            chroma_client = chromadb.HttpClient(host=self.chroma_host, port=self.chroma_port)
            
            # Initialize vector store for questions collection
            questions_store = Chroma(
                collection_name="questions",  # Use a separate collection for questions
                embedding_function=self.embedding_function,
                client=chroma_client
            )
            
            # Use the vector store as a retriever
            retriever = questions_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": limit}
            )
            
            # Retrieve similar questions
            results = retriever.invoke(partial_query)
            
            # Extract questions from results
            suggestions = [doc.metadata.get("question", "") for doc in results]
            
            # Calculate retrieval time
            retrieval_time = time.time() - start_time
            
            return suggestions, retrieval_time, True
            
        except Exception as e:
            print(f"Error retrieving autocomplete suggestions: {str(e)}")
            return [], 0, False