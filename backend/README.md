# Stouffville By-laws AI Backend

A Flask-based backend service that provides AI-powered responses to questions about Stouffville by-laws using Google's Gemini AI and ChromaDB vector search.

## Features

- REST API for querying the Gemini AI model
- Multiple Gemini model options for different performance/quality needs
- Expired by-laws filtering to show only currently active regulations
- Comparison mode to see differences between filtered and unfiltered answers
- Simple web-based demo interface for testing without the frontend
- CORS support for frontend integration
- 50-second timeout protection for AI queries
- ChromaDB vector search integration with Voyage AI embeddings for intelligent retrieval

## API Endpoints

### GET `/api/hello`

Simple health check endpoint that confirms the API is running.

**Response:**
```json
{
  "message": "Hello from the Stouffville By-laws AI backend!"
}
```

### POST `/api/ask`

Main endpoint for the React frontend to query the AI.

**Request Body:**
```json
{
  "query": "What are the noise restrictions in Stouffville?",
  "model": "gemini-2.0-flash" 
}
```

**Response (Success):**
```json
{
  "answer": "The AI-generated response about all Stouffville by-laws",
  "filtered_answer": "The AI-generated response about only active Stouffville by-laws",
  "source": "ChromaDB",
  "bylaw_numbers": ["2015-139-RE", "2015-04-RE"],
  "model": "gemini-2.0-flash"
}
```

**Response (Error):**
```json
{
  "error": "Error message"
}
```

### GET/POST `/api/demo`

A standalone web demo page with a simple form interface:
- GET: Returns the demo page
- POST: Processes the query and displays the result with source information

The demo page includes:
- Model selection dropdown
- Comparison mode to show both filtered and unfiltered answers
- Side-by-side view option for easier comparison

## Setup for Frontend Developers

### Production Backend

A production backend is available at:
```
http://bylaws.freemyip.com:5000
```

Frontend developers can directly use this production backend if they don't want to set up their own local server.

### Local Development Setup

1. **Environment Setup**

   The backend requires a `.env` file with the following variables:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   VOYAGE_AI_KEY=your_voyage_api_key_here
   ```

2. **Running the Backend Locally**

   ```bash
   # Install dependencies
   pip install flask flask-cors langchain langchain-google-genai langchain-chroma langchain-voyageai chromadb python-dotenv

   # Run the application
   python app.py
   ```

   The server will run at `http://localhost:5000`

3. **Integration with Frontend**

   - Backend is configured with CORS support for frontend integration
   - Use the `/api/ask` endpoint for all AI queries from your React app
   - Queries should be sent as JSON with a `query` field and optional `model` field
   - Responses will contain either an `answer`/`filtered_answer` field with the AI response or an `error` field
   - Responses include a `source` field indicating the data comes from ChromaDB
   - Responses include a `bylaw_numbers` array listing the referenced by-laws

## Project Structure

- `app.py`: Main Flask application
- `app/`: Application package
  - `__init__.py`: Package initialization
  - `prompts.py`: AI prompt templates (including filtered version for active by-laws only)
  - `chroma_retriever.py`: ChromaDB integration for vector search
  - `gemini_handler.py`: Gemini AI model integration and response processing
  - `templates/`: HTML templates for web interfaces
    - `demo.html`: Enhanced demo page with improved UI, model selection, and comparison features

## Database

The application uses ChromaDB as the primary database for by-laws:

- **Vector Database (ChromaDB)**:
   - Stores vector embeddings for efficient semantic search
   - Uses Voyage AI embeddings for high-quality semantic understanding
   - Located in `../database/chroma-data/` directory
   - Initialized using `../database/init_chroma.py` script

## Vector Search Functionality

The application uses ChromaDB and Voyage AI embeddings to provide intelligent retrieval:

1. When a query is received, the system attempts to find relevant by-laws using vector search
2. If relevant documents are found, those specific by-laws are sent to Gemini AI
3. The system generates two different responses:
   - A complete answer using all retrieved by-laws
   - A filtered answer using only currently active by-laws
4. Demo interface provides options to compare both responses

## Gemini AI Models

The backend supports multiple Gemini model options:

- `gemini-2.0-flash-lite`: Fastest, lowest cost option
- `gemini-2.0-flash`: Default model with balanced speed and quality
- `gemini-2.0-flash-thinking-exp-01-21`: Better reasoning capabilities
- `gemini-2.5-pro-exp-03-25`: Highest quality, but most expensive

## Important Implementation Details

- The backend defaults to the `gemini-2.0-flash` model
- A 50-second timeout is applied to all AI queries to prevent long-running requests
- The AI is configured to provide comprehensive HTML-formatted responses 
- Error handling is implemented for API key issues, model selection, and processing errors
- Responses include current date information to help with determining expired by-laws

## Development Notes

- Running in debug mode for development (debug=True)
- For production deployment, set debug=False and configure a proper WSGI server 