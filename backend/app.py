from flask import Flask, jsonify, request, render_template_string, render_template
from flask_cors import CORS
import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from dotenv import load_dotenv
from app.prompts import BYLAWS_PROMPT_TEMPLATE

# Load API keys and environment variables from .env file
load_dotenv()

# Initialize Flask app and enable CORS for frontend integration
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates'))
CORS(app)

# Define paths to data files relative to the project root
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the absolute path to the database file
BYLAWS_JSON_PATH = os.path.join(BACKEND_DIR, '..', 'database', 'parking_related_by-laws.json')

def get_gemini_response(query):
    """
    Process user queries through the Gemini AI model.
    
    Args:
        query (str): The user's question about Stouffville by-laws
        
    Returns:
        dict: Contains either the AI response or error information
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY environment variable is not set"}
    
    try:
        # Initialize Gemini model with the specified version and 10 second timeout
        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=api_key,
            timeout=30  # Add 30 second timeout
        )
        
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
    
    response = get_gemini_response(query)
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
            response = get_gemini_response(query)
            answer = response.get('answer', 'Error: No response')
            if 'error' in response:
                answer = f"Error: {response['error']}"
            return render_template('demo.html', question=query, answer=answer)
    
    return render_template('demo.html')

if __name__ == '__main__':
    # Run in debug mode for development
    # In production, we should set debug=False and configure a proper WSGI server
    app.run(host='0.0.0.0', port=5000, debug=True)


