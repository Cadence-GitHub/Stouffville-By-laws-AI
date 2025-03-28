from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from dotenv import load_dotenv

# Load API keys and environment variables from .env file
load_dotenv()

# Initialize Flask app and enable CORS for frontend integration
app = Flask(__name__)
CORS(app)

# HTML template for the simple web demo interface
# This allows testing the AI without requiring the full React frontend
DEMO_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Stouffville By-laws AI Demo</title>
</head>
<body>
    <h1>Stouffville By-laws AI Demo</h1>
    
    <form action="/api/demo" method="post">
        <label for="query">Ask a question:</label>
        <input type="text" id="query" name="query" required>
        <input type="submit" value="Submit">
    </form>
    
    {% if question %}
    <div>
        <p><b>Question:</b> {{ question }}</p>
        <p><b>Answer:</b> {{ answer }}</p>
    </div>
    {% endif %}
</body>
</html>
"""

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
            timeout=10  # Add 10 second timeout
        )
        
        # Define how the AI should process the query
        # Currently restricting to one-sentence responses
        prompt = PromptTemplate(
            input_variables=["question"],
            template="Respond to this query in one sentence: {question}"
        )
        
        # Build the processing pipeline using LangChain's composition syntax
        chain = prompt | model | StrOutputParser()
        
        # Execute the chain and get the AI's response
        response = chain.invoke({"question": query})
        
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
            return render_template_string(DEMO_TEMPLATE, question=query, answer=answer)
    
    return render_template_string(DEMO_TEMPLATE)

if __name__ == '__main__':
    # Run in debug mode for development
    # In production, we should set debug=False and configure a proper WSGI server
    app.run(host='0.0.0.0', port=5000, debug=True)


