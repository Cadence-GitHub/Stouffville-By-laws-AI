from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import os
import json
import time
from dotenv import load_dotenv
import tiktoken  # Still needed for potential direct use elsewhere
import re

# Import from app package using the simplified imports from __init__.py
from app import (
    ChromaDBRetriever,
    get_gemini_response, 
    transform_query_for_enhanced_search,
    get_provincial_law_info,
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
    model = 'gemini-mixed'  # Always use gemini-mixed
    bylaw_status = data.get('bylaw_status', 'active')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Try to use ChromaDB to find relevant bylaws
    try:
        # Transform user query into legal language using the Gemini handler
        transformed_query, transform_time = transform_query_for_enhanced_search(query, model)
        
        # First search with original query - also checks if collection exists
        original_results, original_results_all_fields, original_time, collection_exists = chroma_retriever.retrieve_relevant_bylaws(query, limit=10, bylaw_status=bylaw_status)
        
        # Check if the collection exists
        if not collection_exists:
            return jsonify({"error": "ChromaDB collection does not exist"}), 500
        
        # Second search with transformed query
        transformed_results, transformed_results_all_fields, transformed_time, _ = chroma_retriever.retrieve_relevant_bylaws(transformed_query, limit=10, bylaw_status=bylaw_status)
        
        # Combine results and remove duplicates based on bylawNumber
        seen_bylaws = set()
        combined_results = []
        combined_results_all_fields = []
        
        # First add ALL original results
        for i, bylaw in enumerate(original_results):
            bylaw_id = bylaw.get("bylawNumber", "Unknown")
            seen_bylaws.add(bylaw_id)
            combined_results.append(bylaw)
            combined_results_all_fields.append(original_results_all_fields[i])
        
        # Then add only NEW transformed results that aren't duplicates
        for i, bylaw in enumerate(transformed_results):
            bylaw_id = bylaw.get("bylawNumber", "Unknown")
            if bylaw_id not in seen_bylaws:
                seen_bylaws.add(bylaw_id)
                combined_results.append(bylaw)
                combined_results_all_fields.append(transformed_results_all_fields[i])
        
        # Use the combined results
        relevant_bylaws = combined_results
        relevant_bylaws_all_fields = combined_results_all_fields
        
        # If no relevant bylaws found, return an error
        if not relevant_bylaws:
            return jsonify({"error": f"No relevant bylaws found for query: {query}"}), 404
        
        # Get Gemini response using the relevant bylaws
        response = get_gemini_response(query, relevant_bylaws, model, bylaw_status, relevant_bylaws_all_fields)
        
        # Check if there was an error
        if 'error' in response:
            return jsonify(response), 500
        
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
        
        # Get bylaw status filter (active or inactive)
        bylaw_status = request.form.get('bylaw_status', 'active')
        
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
                    original_results, _, original_time, collection_exists = chroma_retriever.retrieve_relevant_bylaws(query, limit=bylaws_limit, bylaw_status=bylaw_status)
                    
                    # Check if collection exists
                    if not collection_exists:
                        error_message = "Error: ChromaDB collection does not exist"
                        return render_template('demo.html', question=query, answer=error_message, model=model)
                    
                    # Second search with transformed query - always use 10 documents
                    transformed_results, _, transformed_time, _ = chroma_retriever.retrieve_relevant_bylaws(transformed_query, limit=10, bylaw_status=bylaw_status)
                    
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
                    relevant_bylaws, _, retrieval_time, collection_exists = chroma_retriever.retrieve_relevant_bylaws(query, limit=bylaws_limit, bylaw_status=bylaw_status)
                    
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
                response = get_gemini_response(query, relevant_bylaws, model, bylaw_status)
                
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
                    
                    # Include transform time in enhanced search mode
                    if enhanced_search:
                        timing_info = f"Timings: Transform: {transform_time:.2f}s, Original retrieval: {original_time:.2f}s, Enhanced retrieval: {transformed_time:.2f}s, First prompt: {first_prompt_time:.2f}s, Second prompt: {second_prompt_time:.2f}s, Total processing: {pre_render_time:.2f}s"
                    else:
                        timing_info = f"Timings: Retrieval: {retrieval_time:.2f}s, First prompt: {first_prompt_time:.2f}s, Second prompt: {second_prompt_time:.2f}s, Total processing: {pre_render_time:.2f}s"
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
                    status_info = f"Bylaw Status Filter: {bylaw_status.capitalize()}"
                    enhanced_info = ""
                    if enhanced_search:
                        # Identify which bylaws came from the enhanced search
                        enhanced_bylaw_ids = []
                        for bylaw_id in bylaw_numbers:
                            if bylaw_id not in original_bylaw_ids:
                                enhanced_bylaw_ids.append(bylaw_id)
                        
                        enhanced_bylaws_str = ", ".join(enhanced_bylaw_ids) if enhanced_bylaw_ids else "None"
                        enhanced_info = f"<br>Bylaws found by Enhanced Search: {enhanced_bylaws_str}"
                    footer = f"<hr><small><i>{source_info}<br>{bylaw_info}{enhanced_info}<br>{token_info}<br>{model_info}<br>{status_info}<br>{timing_info}</i></small>"
                    
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
                            bylaw_status=bylaw_status,
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
                            bylaw_status=bylaw_status,
                            transformed_query=transformed_query if enhanced_search else None
                        )
                
            except Exception as e:
                error_message = f"Error: ChromaDB retrieval failed: {str(e)}"
                return render_template('demo.html', question=query, answer=error_message, model=model)
    
    return render_template('demo.html', compare_mode=False, side_by_side=False, model="gemini-mixed", bylaws_limit=10, enhanced_search=True, bylaw_status="active")

@app.route('/api/bylaw/<bylaw_number>')
def get_bylaw_json(bylaw_number):
    """
    API endpoint that returns the full JSON data for a specific bylaw by its number.
    """
    try:
        # First try with the original bylaw number
        exact_match, retrieval_time, collection_exists = chroma_retriever.retrieve_bylaw_by_number(bylaw_number)
        
        # Handle collection issues
        if not collection_exists:
            return jsonify({"error": "ChromaDB collection does not exist"}), 500
            
        # If no exact match with original number, try with cleaned version
        if exact_match is None:
            # Use regex to remove -XX pattern (dash followed by two capital letters) if present
            clean_bylaw_number = re.sub(r'-[A-Z]{2}$', '', bylaw_number)
            
            # Only try the clean version if it's different from the original
            if clean_bylaw_number != bylaw_number:
                exact_match, retrieval_time, collection_exists = chroma_retriever.retrieve_bylaw_by_number(clean_bylaw_number)
        
        # If still no match after trying both versions, return 404
        if exact_match is None:
            return jsonify({"error": f"No bylaws found matching {bylaw_number}"}), 404
            
        # Prepare response
        response = jsonify(exact_match)
        
        # Add cache-prevention headers
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        return jsonify({"error": f"Error retrieving bylaw information: {str(e)}"}), 500

@app.route('/api/autocomplete', methods=['POST'])
def autocomplete():
    """
    API endpoint that returns autocomplete suggestions for a partial query.
    """
    data = request.get_json()
    partial_query = data.get('query', '')
    
    if not partial_query or len(partial_query) < 3:
        return jsonify({"suggestions": []}), 200
    
    # Try to use ChromaDB to find similar questions
    try:
        suggestions, retrieval_time, collection_exists = chroma_retriever.autocomplete_query(
            partial_query, limit=5)
        
        # If collection doesn't exist, return appropriate message
        if not collection_exists:
            return jsonify({
                "error": "Questions collection does not exist. Run ingest_questions.py first."
            }), 500
        
        # Return suggestions
        return jsonify({
            "suggestions": suggestions,
            "retrieval_time": retrieval_time
        })
            
    except Exception as e:
        return jsonify({"error": f"Autocomplete failed: {str(e)}"}), 500

@app.route('/public-demo')
def public_demo():
    """
    Serve the public demo page for the by-laws AI.
    """
    return app.send_static_file('public_demo.html')


@app.route('/api/provincial_laws', methods=['POST'])
def provincial_laws():
    """API endpoint that provides information about provincial laws with Google Search grounding."""
    data = request.get_json()
    bylaw_type = data.get('bylaw_type', 'general')
    model = data.get('model', 'gemini-2.0-flash')
    
    response = get_provincial_law_info(bylaw_type, model)
    
    if 'error' in response:
        return jsonify({"error": response['error']}), 500
    
    return jsonify(response)

if __name__ == '__main__':
    # Run in debug mode for development
    # In production, we should set debug=False and configure a proper WSGI server
    app.run(host='0.0.0.0', port=5000, debug=True)


