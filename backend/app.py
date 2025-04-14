from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import os
import json
import time  # Add time module import
from dotenv import load_dotenv
from app.prompts import BYLAWS_PROMPT_TEMPLATE, FILTERED_BYLAWS_PROMPT_TEMPLATE, ENHANCED_SEARCH_PROMPT_TEMPLATE
from app.chroma_retriever import ChromaDBRetriever  # Import the simplified ChromaDB retriever
from app.gemini_handler import get_gemini_response, transform_query_for_enhanced_search, ALLOWED_MODELS  # Import the refactored Gemini handler

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
        relevant_bylaws, retrieval_time = chroma_retriever.retrieve_relevant_bylaws(query, limit=10)
        
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
        
        print(f"Request params processing: {time.time() - request_start_time:.2f}s")
        
        if query:
            # Try to use ChromaDB to find relevant bylaws
            try:
                # Check if ChromaDB collection exists
                time_checkpoint = time.time()
                collection_exists = chroma_retriever.collection_exists()
                print(f"Collection existence check: {time.time() - time_checkpoint:.2f}s")
                
                if not collection_exists:
                    error_message = "Error: ChromaDB collection does not exist"
                    return render_template('demo.html', question=query, answer=error_message, model=model)
                
                # Initialize relevant_bylaws list
                relevant_bylaws = []
                
                # If enhanced search is enabled, perform two searches and combine results
                if enhanced_search:
                    # Transform user query into legal language using the Gemini handler
                    transformed_query, transform_time = transform_query_for_enhanced_search(query, model)
                    
                    # First search with original query
                    original_results, original_time = chroma_retriever.retrieve_relevant_bylaws(query, limit=bylaws_limit)
                    
                    # Second search with transformed query - always use 10 documents
                    transformed_results, transformed_time = chroma_retriever.retrieve_relevant_bylaws(transformed_query, limit=10)
                    
                    # Total retrieval time is the sum of both searches
                    retrieval_time = original_time + transformed_time
                    
                    # Time the result combination process
                    time_checkpoint = time.time()
                    
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
                    
                    # Calculate results combination time
                    result_combination_time = time.time() - time_checkpoint
                    print(f"Results combination time: {result_combination_time:.2f}s")
                    
                    # Use the combined results
                    relevant_bylaws = combined_results
                else:
                    # Standard search - just use the original query
                    transform_time = 0  # No transform time for standard search
                    original_time = 0  # Initialize for consistent timing display later
                    transformed_time = 0  # Initialize for consistent timing display later
                    relevant_bylaws, retrieval_time = chroma_retriever.retrieve_relevant_bylaws(query, limit=bylaws_limit)
                
                # If no relevant bylaws found, return an error
                if not relevant_bylaws:
                    error_message = f"Error: No relevant bylaws found for query: {query}"
                    return render_template('demo.html', question=query, answer=error_message, model=model)
                
                # Time the bylaw numbers extraction
                time_checkpoint = time.time()
                
                # Extract bylaw numbers for display
                bylaw_numbers = [bylaw.get("bylawNumber", "Unknown") for bylaw in relevant_bylaws]
                bylaw_numbers_str = ", ".join(bylaw_numbers)
                
                print(f"Bylaw numbers extraction: {time.time() - time_checkpoint:.2f}s")
                
                # Track time for generating responses
                start_prompt_time = time.time()
                
                # Get Gemini response using the relevant bylaws
                response = get_gemini_response(query, relevant_bylaws, model)

                # Calculate total time for generating responses
                end_prompt_time = time.time()
                prompt_time = end_prompt_time - start_prompt_time   

                print(f"Total Gemini prompt time: {prompt_time:.2f}s")
                
                # Time the timing info and footer creation
                time_checkpoint = time.time()
                
                # Only use prompt timings if available in the response
                timing_info = ""
                if 'timings' in response:
                    first_prompt_time = response['timings'].get('first_prompt', 0)
                    second_prompt_time = response['timings'].get('second_prompt', 0)
                    third_prompt_time = response['timings'].get('third_prompt', 0)
                    
                    # Calculate total pre-render processing time
                    pre_render_time = time.time() - request_start_time
                    
                    # Include transform time in enhanced search mode
                    if enhanced_search:
                        timing_info = f"Timings: Transform: {transform_time:.2f}s, Original retrieval: {original_time:.2f}s, Enhanced retrieval: {transformed_time:.2f}s, First prompt: {first_prompt_time:.2f}s, Second prompt: {second_prompt_time:.2f}s, Third prompt: {third_prompt_time:.2f}s, Pre-render processing: {pre_render_time:.2f}s"
                    else:
                        timing_info = f"Timings: Retrieval: {retrieval_time:.2f}s, First prompt: {first_prompt_time:.2f}s, Second prompt: {second_prompt_time:.2f}s, Third prompt: {third_prompt_time:.2f}s, Pre-render processing: {pre_render_time:.2f}s"
                else:
                    # Calculate total pre-render processing time
                    pre_render_time = time.time() - request_start_time
                    
                    # If no detailed timings available, only show retrieval time (and transform time if applicable)
                    if enhanced_search:
                        timing_info = f"Timings: Transform: {transform_time:.2f}s, Original retrieval: {original_time:.2f}s, Enhanced retrieval: {transformed_time:.2f}s, Pre-render processing: {pre_render_time:.2f}s"
                    else:
                        timing_info = f"Timings: Retrieval: {retrieval_time:.2f}s, Pre-render processing: {pre_render_time:.2f}s"
                
                if 'error' in response:
                    answer = f"Error: {response['error']}"
                    print(f"Timing info creation: {time.time() - time_checkpoint:.2f}s")
                    return render_template('demo.html', question=query, answer=answer, model=model)
                else:
                    # Prepare the responses with source information
                    source_info = "Source: ChromaDB vector search (using Voyage AI embeddings)"
                    bylaw_info = f"Retrieved By-laws: {bylaw_numbers_str}"
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
                    footer = f"<hr><small><i>{source_info}<br>{bylaw_info}{enhanced_info}<br>{model_info}<br>{timing_info}</i></small>"
                    
                    print(f"Timing info and footer creation: {time.time() - time_checkpoint:.2f}s")
                    
                    # Time the template rendering
                    render_start_time = time.time()
                    
                    if compare_mode:
                        # When comparing, provide both answers with the footer
                        full_answer = response.get('answer', 'Error: No response') + footer
                        filtered_answer = response.get('filtered_answer', 'Error: No response') + footer
                        laymans_answer = response.get('laymans_answer', 'Error: No response') + footer
                        
                        template = render_template(
                            'demo.html', 
                            question=query, 
                            full_answer=full_answer,
                            filtered_answer=filtered_answer,
                            laymans_answer=laymans_answer,
                            compare_mode=compare_mode,
                            side_by_side=side_by_side,
                            model=model,
                            bylaws_limit=bylaws_limit,
                            enhanced_search=enhanced_search
                        )
                    else:
                        # Default is to show only the layman's answer
                        answer_text = response.get('laymans_answer', 'Error: No response')
                        answer = f"{answer_text}{footer}"
                        
                        template = render_template(
                            'demo.html', 
                            question=query, 
                            answer=answer,
                            compare_mode=compare_mode,
                            side_by_side=side_by_side,
                            model=model,
                            bylaws_limit=bylaws_limit,
                            enhanced_search=enhanced_search
                        )
                    
                    render_time = time.time() - render_start_time
                    print(f"Template rendering time: {render_time:.2f}s")
                    
                    return template
                
            except Exception as e:
                error_message = f"Error: ChromaDB retrieval failed: {str(e)}"
                return render_template('demo.html', question=query, answer=error_message, model=model)
    
    return render_template('demo.html', compare_mode=False, side_by_side=False, model="gemini-2.0-flash", bylaws_limit=10, enhanced_search=False)

if __name__ == '__main__':
    # Run in debug mode for development
    # In production, we should set debug=False and configure a proper WSGI server
    app.run(host='0.0.0.0', port=5000, debug=True)


