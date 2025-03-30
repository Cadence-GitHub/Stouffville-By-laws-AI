from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.output_parser import StrOutputParser
from dotenv import load_dotenv
from app.prompts import BYLAWS_PROMPT_TEMPLATE
from app.chroma_retriever import ChromaDBRetriever  # Import the simplified ChromaDB retriever

# Load API keys and environment variables from .env file
load_dotenv()

# Initialize Flask app and enable CORS for frontend integration
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates'))
CORS(app)

# Define paths to data files relative to the project root
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the absolute path to the database file (fallback if ChromaDB is unavailable)
BYLAWS_JSON_PATH = os.path.join(BACKEND_DIR, '..', 'database', 'parking_related_by-laws.json')

# Initialize ChromaDB retriever
chroma_retriever = ChromaDBRetriever()

def get_gemini_response(query, relevant_bylaws=None):
    """
    Process user queries through the Gemini AI model.
    
    Args:
        query (str): The user's question about Stouffville by-laws
        relevant_bylaws (list, optional): List of by-laws relevant to the query
        
    Returns:
        dict: Contains either the AI response or error information
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY environment variable is not set"}
    
    try:
        # Initialize Gemini model with the specified version and 30 second timeout
        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=api_key,
            timeout=30
        )
        
        # If relevant bylaws are provided, use those instead of loading all bylaws
        if relevant_bylaws:
            bylaws_content = json.dumps(relevant_bylaws, indent=2)
        else:
            # Load the by-laws data from the JSON file
            try:
                with open(BYLAWS_JSON_PATH, 'r') as file:
                    bylaws_data = json.load(file)
                    bylaws_content = json.dumps(bylaws_data, indent=2)
            except Exception as file_error:
                return {"error": f"Failed to load by-laws data: {str(file_error)}"}
        
        # Use the imported prompt template from app/prompts.py
        prompt = BYLAWS_PROMPT_TEMPLATE
        
        # Build the processing pipeline using LangChain's composition syntax
        chain = prompt | model | StrOutputParser()
        
        # Execute the chain and get the AI's response
        response = chain.invoke({"bylaws_content": bylaws_content, "question": query})
        
        return {"answer": response}
    except Exception as e:
        return {"error": str(e)}

@app.route('/api/hello', methods=['GET'])
def hello():
    """Simple endpoint to verify the API is running"""
    return jsonify({
        "message": "Hello from the Stouffville By-laws AI backend!"
    })

@app.route('/api/ask', methods=['POST'])
def ask():
    """
    Main API endpoint for the React frontend to query the AI.
    Expects a JSON payload with a 'query' field.
    """
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Try to use ChromaDB to find relevant bylaws
    try:
        # Check if the ChromaDB collection exists and has documents
        if chroma_retriever.collection_exists():
            # Use ChromaDB to find relevant bylaws
            relevant_bylaws = chroma_retriever.retrieve_relevant_bylaws(query, limit=10)
            
            # If no relevant bylaws found, fall back to the standard approach
            if not relevant_bylaws:
                print(f"No relevant bylaws found in ChromaDB for query: {query}")
                response = get_gemini_response(query)
            else:
                print(f"Found {len(relevant_bylaws)} relevant bylaws in ChromaDB for query: {query}")
                response = get_gemini_response(query, relevant_bylaws)
                
            # Add the source info to the response (for transparency/debugging)
            if "answer" in response:
                response["source"] = "chroma" if relevant_bylaws else "file"
                
            return jsonify(response)
        else:
            # Fall back to the standard approach
            response = get_gemini_response(query)
            response["source"] = "file"
            return jsonify(response)
            
    except Exception as e:
        # Fall back to the standard approach if ChromaDB retrieval fails
        response = get_gemini_response(query)
        response["source"] = "file"
        response["fallback_reason"] = str(e)
        return jsonify(response)

@app.route('/api/demo', methods=['GET', 'POST'])
def demo():
    """
    Standalone web demo page with a simple form interface.
    - GET: Returns the demo page
    - POST: Processes the query and displays the result
    """
    if request.method == 'POST':
        query = request.form.get('query', '')
        if query:
            # Try to use ChromaDB to find relevant bylaws
            try:
                # Check if ChromaDB collection exists
                if chroma_retriever.collection_exists():
                    # Use ChromaDB to find relevant bylaws
                    relevant_bylaws = chroma_retriever.retrieve_relevant_bylaws(query, limit=10)
                    
                    # If relevant bylaws found, use them
                    if relevant_bylaws:
                        response = get_gemini_response(query, relevant_bylaws)
                        source_info = "Source: ChromaDB vector search (using Voyage AI embeddings)"
                    else:
                        response = get_gemini_response(query)
                        source_info = "Source: Default JSON file (no relevant bylaws found in ChromaDB)"
                else:
                    # Fall back to the standard approach
                    response = get_gemini_response(query)
                    source_info = "Source: Default JSON file (ChromaDB not available)"
                
                answer = response.get('answer', 'Error: No response')
                if 'error' in response:
                    answer = f"Error: {response['error']}"
                    
                # Add source info at the bottom of the response
                answer = f"{answer}<hr><small><i>{source_info}</i></small>"
                
                return render_template('demo.html', question=query, answer=answer)
                
            except Exception as e:
                # Fall back to the standard approach if ChromaDB search fails
                response = get_gemini_response(query)
                answer = response.get('answer', 'Error: No response')
                if 'error' in response:
                    answer = f"Error: {response['error']}"
                    
                # Add fallback info
                answer = f"{answer}<hr><small><i>Source: Default JSON file (ChromaDB error: {str(e)})</i></small>"
                
                return render_template('demo.html', question=query, answer=answer)
    
    return render_template('demo.html')

if __name__ == '__main__':
    # Run in debug mode for development
    # In production, we should set debug=False and configure a proper WSGI server
    app.run(host='0.0.0.0', port=5000, debug=True)


