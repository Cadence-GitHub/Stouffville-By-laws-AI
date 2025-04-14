from langchain_chroma import Chroma
import os
import chromadb
from langchain_voyageai import VoyageAIEmbeddings

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
        self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """Initialize the vector store connection. """
        try:
            # Create the ChromaDB client directly using the HttpClient
            chroma_client = chromadb.HttpClient(host=self.chroma_host, port=self.chroma_port)
            
            # Connect to the existing ChromaDB collection using LangChain's Chroma
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
            import time
            start_time = time.time()
            
            # Use the vector store as a retriever
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": limit}
            )
            
            # Retrieve relevant documents
            documents = retriever.invoke(query)
            
            # Calculate retrieval time
            retrieval_time = time.time() - start_time
            
            # Process the results
            results = []
            for doc in documents:
                # Extract the by-law data from metadata
                bylaw_data = doc.metadata
                
                # Also add the page content separately if needed
                bylaw_data["content"] = doc.page_content
                
                results.append(bylaw_data)
            
            # Return the results and a flag indicating the collection exists
            return results, retrieval_time, True
            
        except Exception as e:
            print(f"Error retrieving bylaws: {str(e)}")
            return [], 0, False
    
    def collection_exists(self):
        """
        Check if the collection exists and has documents.
        
        This function is maintained for backward compatibility.
        It's more efficient to use retrieve_relevant_bylaws which returns an exists_status.
        """
        if not self.vector_store:
            return False
            
        try:
            # Instead of getting all ids, just try to get a single document
            # This is much more efficient for large collections
            retriever = self.vector_store.as_retriever(
                search_type="similarity", 
                search_kwargs={"k": 1}
            )
            
            # Use a simple but effective query that should match any document
            # The _client.count() would be ideal but isn't directly accessible through LangChain's API
            query = "document"
            results = retriever.invoke(query)
            
            # If we got any results, the collection exists and has documents
            return len(results) > 0
        except Exception as e:
            print(f"Error checking collection existence: {str(e)}")
            return False

