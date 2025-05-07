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
        
        # Collection names
        self.bylaw_collection_name = "by-laws"
        self.questions_collection_name = "questions"
        
        # Initialize client and vector stores
        try:
            # Create a single ChromaDB client to be reused
            self.chroma_client = chromadb.HttpClient(host=self.chroma_host, port=self.chroma_port)
            
            # Connect to the existing ChromaDB by-laws collection
            self.vector_store = Chroma(
                collection_name=self.bylaw_collection_name,
                embedding_function=self.embedding_function,
                client=self.chroma_client
            )
            
            # Connect to the questions collection for autocomplete
            self.questions_store = Chroma(
                collection_name=self.questions_collection_name,
                embedding_function=self.embedding_function,
                client=self.chroma_client
            )
            
            print(f"Successfully connected to ChromaDB collections")
        except Exception as e:
            print(f"Error connecting to ChromaDB: {str(e)}")
            self.chroma_client = None
            self.vector_store = None
            self.questions_store = None
    
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
            
            # Use similarity_search directly instead of retriever
            documents = self.vector_store.similarity_search(
                query,
                k=limit,
                filter={"isActive": True}
            )
            
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
        Retrieve a specific bylaw by its number.
        
        Returns:
            tuple: (bylaw document or None, retrieval_time in seconds, collection_exists)
        """
        if not self.vector_store:
            return None, 0, False
            
        try:
            start_time = time.time()
            
            # Get the direct collection access
            collection = self.vector_store._collection
            
            # Get exact match only
            direct_match = collection.get(
                where={"bylawNumber": bylaw_number},
                limit=1
            )
            
            # If match found, return it
            if direct_match and direct_match['metadatas'] and len(direct_match['metadatas']) > 0:
                bylaw_data = direct_match['metadatas'][0]
                if 'documents' in direct_match and direct_match['documents']:
                    bylaw_data["content"] = direct_match['documents'][0]
                    
                return bylaw_data, time.time() - start_time, True
            
            # No match found
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
        if not self.embedding_function or not self.questions_store:
            print("Embedding function or questions store not available")
            return [], 0, False
                
        try:
            # Start timing the retrieval
            start_time = time.time()
            
            # Use similarity_search directly instead of retriever - consistent with retrieve_relevant_bylaws
            documents = self.questions_store.similarity_search(
                partial_query,
                k=limit
            )
            
            # Extract questions from results
            suggestions = [doc.metadata.get("question", "") for doc in documents]
            
            # Calculate retrieval time
            retrieval_time = time.time() - start_time
            
            return suggestions, retrieval_time, True
            
        except Exception as e:
            print(f"Error retrieving autocomplete suggestions: {str(e)}")
            return [], 0, False