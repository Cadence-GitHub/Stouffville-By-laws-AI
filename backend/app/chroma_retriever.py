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
        
        # Initialize the embedding functions
        self.main_embedding_function = VoyageAIEmbeddings(model="voyage-3-large")
        self.questions_embedding_function = VoyageAIEmbeddings(model="voyage-3-lite")
        
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
                embedding_function=self.main_embedding_function,
                client=self.chroma_client
            )
            
            # Connect to the questions collection for autocomplete with different embedding model
            self.questions_store = Chroma(
                collection_name=self.questions_collection_name,
                embedding_function=self.questions_embedding_function,
                client=self.chroma_client
            )
            
            print(f"Successfully connected to ChromaDB collections")
        except Exception as e:
            print(f"Error connecting to ChromaDB: {str(e)}")
            self.chroma_client = None
            self.vector_store = None
            self.questions_store = None
    
    def retrieve_relevant_bylaws(self, query, limit=10, bylaw_status="active"):
        """
        Retrieve by-laws relevant to the query.
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            bylaw_status (str): "active" or "inactive" to filter bylaws by status
            
        Returns:
            tuple: (list of by-law documents with filtered metadata, list of by-law documents with full metadata, 
                   retrieval_time in seconds, exists_status)
                   where exists_status is a boolean indicating if the collection exists and has documents
        """
        if not self.vector_store:
            print("ChromaDB connection not available")
            return [], [], 0, False
            
        try:
            # Start timing the retrieval
            start_time = time.time()
            
            if bylaw_status == "active":
                # Use similarity_search without filter to improve performance, then filter in memory
                raw_documents = self.vector_store.similarity_search(
                    query,
                    k=limit * 5  # Retrieve more documents than needed to ensure we have enough after filtering
                )
                
                # Filter documents in memory: include docs with isActive=True OR docs without isActive field
                documents = [doc for doc in raw_documents if "isActive" not in doc.metadata or doc.metadata["isActive"]][:limit]
            else:
                # For inactive bylaws, use ChromaDB's filter parameter to retrieve only inactive bylaws
                documents = self.vector_store.similarity_search(
                    query,
                    k=limit,
                    filter={"isActive": False}
                )
            
            # Calculate retrieval time
            retrieval_time = time.time() - start_time
            
            # Process the results - one with filtered fields, one with all fields
            results = []
            results_all_fields = []
            
            for doc in documents:
                # For full metadata version
                full_bylaw_data = dict(doc.metadata)
                full_bylaw_data["content"] = doc.page_content
                results_all_fields.append(full_bylaw_data)
                
                # For filtered version
                filtered_bylaw_data = dict(doc.metadata)
                filtered_bylaw_data["content"] = doc.page_content
                
                # Remove unnecessary fields from each bylaw for the filtered version
                fields_to_remove = ["keywords", "bylawFileName", 
                                   "urlOriginalDocument", "bylawHeader", "newsSources", "entityAndDesignation"]
                
                # Only remove isActive and whyNotActive fields for active bylaws
                if bylaw_status == "active":
                    fields_to_remove.extend(["isActive", "whyNotActive"])
                    
                for field in fields_to_remove:
                    if field in filtered_bylaw_data:
                        del filtered_bylaw_data[field]

                results.append(filtered_bylaw_data)
            
            # Return both filtered and full results, and a flag indicating the collection exists
            return results, results_all_fields, retrieval_time, True
            
        except Exception as e:
            print(f"Error retrieving bylaws: {str(e)}")
            return [], [], 0, False
    
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
        if not self.questions_embedding_function or not self.questions_store:
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