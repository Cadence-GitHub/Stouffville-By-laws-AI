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
        """Initialize the vector store connection."""
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
            list: List of by-law documents with their metadata
        """
        if not self.vector_store:
            print("ChromaDB connection not available")
            return []
            
        try:
            # Use the vector store as a retriever
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": limit}
            )
            
            # Retrieve relevant documents
            documents = retriever.invoke(query)
            
            # Process the results
            results = []
            for doc in documents:
                # Extract the by-law data from metadata
                bylaw_data = doc.metadata
                
                # Also add the page content separately if needed
                bylaw_data["content"] = doc.page_content
                
                results.append(bylaw_data)
            
            return results
            
        except Exception as e:
            print(f"Error retrieving bylaws: {str(e)}")
            return []
    
    def collection_exists(self):
        """Check if the collection exists and has documents."""
        if not self.vector_store:
            return False
            
        try:
            # Try to get collection info - if it returns data, collection exists
            collection_data = self.vector_store.get()
            # In LangChain Chroma implementation, this will return a dict with keys like 'ids', 'documents', etc.
            return len(collection_data.get('ids', [])) > 0
        except Exception as e:
            print(f"Error checking collection existence: {str(e)}")
            return False

