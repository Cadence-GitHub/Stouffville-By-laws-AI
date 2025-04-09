from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
from app.prompts import BYLAWS_PROMPT_TEMPLATE, FILTERED_BYLAWS_PROMPT_TEMPLATE
from app.chroma_retriever import ChromaDBRetriever  # Import the simplified ChromaDB retriever
from app.gemini_handler import get_gemini_response, ALLOWED_MODELS  # Import the refactored Gemini handler

# Load API keys and environment variables from .env file
load_dotenv()

# Initialize Flask app and enable CORS for frontend integration
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates'))
CORS(app)

# Define paths to data files relative to the project root
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize ChromaDB retriever
chroma_retriever = ChromaDBRetriever()

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
    model = data.get('model', 'gemini-2.0-flash')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Try to use ChromaDB to find relevant bylaws
    try:
        # Check if the ChromaDB collection exists and has documents
        if not chroma_retriever.collection_exists():
            return jsonify({"error": "ChromaDB collection does not exist"}), 500
        
        # Use ChromaDB to find relevant bylaws
        relevant_bylaws = chroma_retriever.retrieve_relevant_bylaws(query, limit=10)
        
        # If no relevant bylaws found, return an error
        if not relevant_bylaws:
            return jsonify({"error": f"No relevant bylaws found for query: {query}"}), 404
        
        # Extract bylaw numbers for display
        bylaw_numbers = [bylaw.get("bylawNumber", "Unknown") for bylaw in relevant_bylaws]
        
        # Get Gemini response using the relevant bylaws
        response = get_gemini_response(query, relevant_bylaws, model)
        
        # Check if there was an error
        if 'error' in response:
            return jsonify(response), 500
            
        # If successful, add source and bylaw information
        response["source"] = "ChromaDB"
        response["bylaw_numbers"] = bylaw_numbers
        response["model"] = model
        
        return jsonify(response)
            
    except Exception as e:
        return jsonify({"error": f"ChromaDB retrieval failed: {str(e)}"}), 500

@app.route('/api/demo', methods=['GET', 'POST'])
def demo():
    """
    Standalone web demo page with a simple form interface.
    - GET: Returns the demo page
    - POST: Processes the query and displays the result
    """
    if request.method == 'POST':
        query = request.form.get('query', '')
        compare_mode = request.form.get('filter_expired', 'false') == 'true'
        side_by_side = request.form.get('side_by_side', 'false') == 'true'
        model = request.form.get('model', 'gemini-2.0-flash')
        
        if query:
            # Try to use ChromaDB to find relevant bylaws
            try:
                # Check if ChromaDB collection exists
                if not chroma_retriever.collection_exists():
                    error_message = "Error: ChromaDB collection does not exist"
                    return render_template('demo.html', question=query, answer=error_message, model=model)
                
                # Use ChromaDB to find relevant bylaws
                relevant_bylaws = chroma_retriever.retrieve_relevant_bylaws(query, limit=10)
                
                # If no relevant bylaws found, return an error
                if not relevant_bylaws:
                    error_message = f"Error: No relevant bylaws found for query: {query}"
                    return render_template('demo.html', question=query, answer=error_message, model=model)
                
                # Extract bylaw numbers for display
                bylaw_numbers = [bylaw.get("bylawNumber", "Unknown") for bylaw in relevant_bylaws]
                bylaw_numbers_str = ", ".join(bylaw_numbers)
                
                # Get Gemini response using the relevant bylaws
                response = get_gemini_response(query, relevant_bylaws, model)
                
                if 'error' in response:
                    answer = f"Error: {response['error']}"
                    return render_template('demo.html', question=query, answer=answer, model=model)
                else:
                    # Prepare the responses with source information
                    source_info = "Source: ChromaDB vector search (using Voyage AI embeddings)"
                    bylaw_info = f"Referenced By-laws: {bylaw_numbers_str}"
                    model_info = f"Model: {model}"
                    footer = f"<hr><small><i>{source_info}<br>{bylaw_info}<br>{model_info}</i></small>"
                    
                    if compare_mode:
                        # When comparing, provide both answers with the footer
                        full_answer = response.get('answer', 'Error: No response') + footer
                        filtered_answer = response.get('filtered_answer', 'Error: No response') + footer
                        
                        return render_template(
                            'demo.html', 
                            question=query, 
                            full_answer=full_answer,
                            filtered_answer=filtered_answer,
                            compare_mode=compare_mode,
                            side_by_side=side_by_side,
                            model=model
                        )
                    else:
                        # Default is to show only the filtered answer (without expired bylaws)
                        answer_text = response.get('filtered_answer', 'Error: No response')
                        answer = f"{answer_text}{footer}"
                        
                        return render_template(
                            'demo.html', 
                            question=query, 
                            answer=answer,
                            compare_mode=compare_mode,
                            side_by_side=side_by_side,
                            model=model
                        )
                
            except Exception as e:
                error_message = f"Error: ChromaDB retrieval failed: {str(e)}"
                return render_template('demo.html', question=query, answer=error_message, model=model)
    
    return render_template('demo.html', compare_mode=False, side_by_side=False, model="gemini-2.0-flash")

if __name__ == '__main__':
    # Run in debug mode for development
    # In production, we should set debug=False and configure a proper WSGI server
    app.run(host='0.0.0.0', port=5000, debug=True)


