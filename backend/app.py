from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import os
import json
import time
from dotenv import load_dotenv
import tiktoken  # Still needed for potential direct use elsewhere

# Import from app package using the simplified imports from __init__.py
from app import (
    ChromaDBRetriever,
    get_gemini_response, 
    transform_query_for_enhanced_search,
    ALLOWED_MODELS,
    count_tokens,
    MODEL_PRICING
)

# Load API keys and environment variables from .env file
load_dotenv()

# Initialize Flask app and enable CORS for frontend integration
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static'))
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
        # Use ChromaDB to find relevant bylaws - now also returns collection existence status
        relevant_bylaws, retrieval_time, collection_exists = chroma_retriever.retrieve_relevant_bylaws(query, limit=10)
        
        # Check if the collection exists
        if not collection_exists:
            return jsonify({"error": "ChromaDB collection does not exist"}), 500
        
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
        response["retrieval_time"] = retrieval_time
        
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
        request_start_time = time.time()  # Start timing entire request processing
        
        query = request.form.get('query', '')
        compare_mode = request.form.get('filter_expired', 'false') == 'true'
        side_by_side = request.form.get('side_by_side', 'false') == 'true'
        model = request.form.get('model', 'gemini-2.0-flash')
        # Get the bylaws limit parameter, default to 10 if not provided
        bylaws_limit = int(request.form.get('bylaws_limit', '10'))
        # Check if enhanced search is enabled
        enhanced_search = request.form.get('enhanced_search', 'false') == 'true'
        
        if query:
            # Try to use ChromaDB to find relevant bylaws
            try:
                # Initialize relevant_bylaws list
                relevant_bylaws = []
                
                # If enhanced search is enabled, perform two searches and combine results
                if enhanced_search:
                    # Transform user query into legal language using the Gemini handler
                    transformed_query, transform_time = transform_query_for_enhanced_search(query, model)
                    
                    # First search with original query - also checks if collection exists
                    original_results, original_time, collection_exists = chroma_retriever.retrieve_relevant_bylaws(query, limit=bylaws_limit)
                    
                    # Check if collection exists
                    if not collection_exists:
                        error_message = "Error: ChromaDB collection does not exist"
                        return render_template('demo.html', question=query, answer=error_message, model=model)
                    
                    # Second search with transformed query - always use 10 documents
                    transformed_results, transformed_time, _ = chroma_retriever.retrieve_relevant_bylaws(transformed_query, limit=10)
                    
                    # Total retrieval time is the sum of both searches
                    retrieval_time = original_time + transformed_time
                    
                    # Combine results and remove duplicates based on bylawNumber
                    seen_bylaws = set()
                    combined_results = []
                    original_bylaw_ids = set()
                    
                    # First add ALL original results
                    for bylaw in original_results:
                        bylaw_id = bylaw.get("bylawNumber", "Unknown")
                        seen_bylaws.add(bylaw_id)
                        original_bylaw_ids.add(bylaw_id)
                        combined_results.append(bylaw)
                    
                    # Then add only NEW transformed results that aren't duplicates
                    for bylaw in transformed_results:
                        bylaw_id = bylaw.get("bylawNumber", "Unknown")
                        if bylaw_id not in seen_bylaws:
                            seen_bylaws.add(bylaw_id)
                            combined_results.append(bylaw)
                    
                    # Use the combined results
                    relevant_bylaws = combined_results
                else:
                    # Standard search - just use the original query
                    # This now also returns collection existence status
                    relevant_bylaws, retrieval_time, collection_exists = chroma_retriever.retrieve_relevant_bylaws(query, limit=bylaws_limit)
                    
                    # Check if collection exists
                    if not collection_exists:
                        error_message = "Error: ChromaDB collection does not exist"
                        return render_template('demo.html', question=query, answer=error_message, model=model)
                        
                    transform_time = 0  # No transform time for standard search
                    original_time = 0  # Initialize for consistent timing display later
                    transformed_time = 0  # Initialize for consistent timing display later
                
                # If no relevant bylaws found, return an error
                if not relevant_bylaws:
                    error_message = f"Error: No relevant bylaws found for query: {query}"
                    return render_template('demo.html', question=query, answer=error_message, model=model)
                
                # Extract bylaw numbers for display
                bylaw_numbers = [bylaw.get("bylawNumber", "Unknown") for bylaw in relevant_bylaws]
                bylaw_numbers_str = ", ".join(bylaw_numbers)
                
                # Get Gemini response using the relevant bylaws
                response = get_gemini_response(query, relevant_bylaws, model)
                
                # Count both input and output tokens and calculate costs
                token_counts = count_tokens(bylaws=relevant_bylaws, response=response, model=model)
                input_token_count = token_counts['input_tokens']
                output_token_count = token_counts['output_tokens']
                input_cost = token_counts['input_cost']
                output_cost = token_counts['output_cost']
                
                # Calculate total pre-render processing time once
                pre_render_time = time.time() - request_start_time
                
                # Only use prompt timings if available in the response
                timing_info = ""
                if 'timings' in response:
                    first_prompt_time = response['timings'].get('first_prompt', 0)
                    second_prompt_time = response['timings'].get('second_prompt', 0)
                    third_prompt_time = response['timings'].get('third_prompt', 0)
                    
                    # Include transform time in enhanced search mode
                    if enhanced_search:
                        timing_info = f"Timings: Transform: {transform_time:.2f}s, Original retrieval: {original_time:.2f}s, Enhanced retrieval: {transformed_time:.2f}s, First prompt: {first_prompt_time:.2f}s, Second prompt: {second_prompt_time:.2f}s, Third prompt: {third_prompt_time:.2f}s, Total processing: {pre_render_time:.2f}s"
                    else:
                        timing_info = f"Timings: Retrieval: {retrieval_time:.2f}s, First prompt: {first_prompt_time:.2f}s, Second prompt: {second_prompt_time:.2f}s, Third prompt: {third_prompt_time:.2f}s, Total processing: {pre_render_time:.2f}s"
                else:
                    # If no detailed timings available, only show retrieval time (and transform time if applicable)
                    if enhanced_search:
                        timing_info = f"Timings: Transform: {transform_time:.2f}s, Original retrieval: {original_time:.2f}s, Enhanced retrieval: {transformed_time:.2f}s, Total processing: {pre_render_time:.2f}s"
                    else:
                        timing_info = f"Timings: Retrieval: {retrieval_time:.2f}s, Total processing: {pre_render_time:.2f}s"
                
                if 'error' in response:
                    answer = f"Error: {response['error']}"
                    return render_template('demo.html', question=query, answer=answer, model=model)
                else:
                    # Prepare the responses with source information
                    source_info = "Source: ChromaDB vector search (using Voyage AI embeddings)"
                    bylaw_info = f"Retrieved By-laws: {bylaw_numbers_str}"
                    token_info = f"Total input tokens: {input_token_count} (${input_cost:.6f})<br>Total output tokens: {output_token_count} (${output_cost:.6f})"
                    model_info = f"Model: {model}"
                    enhanced_info = ""
                    if enhanced_search:
                        # Identify which bylaws came from the enhanced search
                        enhanced_bylaw_ids = []
                        for bylaw_id in bylaw_numbers:
                            if bylaw_id not in original_bylaw_ids:
                                enhanced_bylaw_ids.append(bylaw_id)
                        
                        enhanced_bylaws_str = ", ".join(enhanced_bylaw_ids) if enhanced_bylaw_ids else "None"
                        enhanced_info = f"<br>Bylaws found by Enhanced Search: {enhanced_bylaws_str}"
                    footer = f"<hr><small><i>{source_info}<br>{bylaw_info}{enhanced_info}<br>{token_info}<br>{model_info}<br>{timing_info}</i></small>"
                    
                    if compare_mode:
                        # When comparing, provide only the answers without the footer
                        full_answer = response.get('answer', 'Error: No response') 
                        filtered_answer = response.get('filtered_answer', 'Error: No response')
                        laymans_answer = response.get('laymans_answer', 'Error: No response') + footer
                        
                        return render_template(
                            'demo.html', 
                            question=query, 
                            full_answer=full_answer,
                            filtered_answer=filtered_answer,
                            laymans_answer=laymans_answer,
                            compare_mode=compare_mode,
                            side_by_side=side_by_side,
                            model=model,
                            bylaws_limit=bylaws_limit,
                            enhanced_search=enhanced_search,
                            transformed_query=transformed_query if enhanced_search else None
                        )
                    else:
                        # Default is to show only the layman's answer
                        answer_text = response.get('laymans_answer', 'Error: No response')
                        answer = f"{answer_text}{footer}"
                        
                        return render_template(
                            'demo.html', 
                            question=query, 
                            answer=answer,
                            compare_mode=compare_mode,
                            side_by_side=side_by_side,
                            model=model,
                            bylaws_limit=bylaws_limit,
                            enhanced_search=enhanced_search,
                            transformed_query=transformed_query if enhanced_search else None
                        )
                
            except Exception as e:
                error_message = f"Error: ChromaDB retrieval failed: {str(e)}"
                return render_template('demo.html', question=query, answer=error_message, model=model)
    
    return render_template('demo.html', compare_mode=False, side_by_side=False, model="gemini-2.0-flash", bylaws_limit=10, enhanced_search=False)

@app.route('/api/bylaw/<bylaw_number>')
def get_bylaw_json(bylaw_number):
    """
    API endpoint that returns the full JSON data for a specific bylaw by its number.
    This is used by the bylaw viewer to display detailed information.
    """
    try:
        # Try to retrieve the bylaw using its number as a search query
        relevant_bylaws, _, collection_exists = chroma_retriever.retrieve_relevant_bylaws(bylaw_number, limit=10)
        
        if not collection_exists:
            return jsonify({"error": "ChromaDB collection does not exist"}), 500
            
        if not relevant_bylaws:
            return jsonify({"error": f"No bylaws found matching {bylaw_number}"}), 404
            
        # Find exact match by bylaw number
        exact_match = None
        for bylaw in relevant_bylaws:
            if bylaw.get("bylawNumber") == bylaw_number:
                exact_match = bylaw
                break
                
        if not exact_match:
            # If no exact match, return the first result
            exact_match = relevant_bylaws[0]
            
        # Return the full bylaw data as JSON
        response = jsonify(exact_match)
        
        # Add cache-prevention headers
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        return jsonify({"error": f"Error retrieving bylaw information: {str(e)}"}), 500

if __name__ == '__main__':
    # Run in debug mode for development
    # In production, we should set debug=False and configure a proper WSGI server
    app.run(host='0.0.0.0', port=5000, debug=True)


