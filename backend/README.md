# Stouffville By-laws AI Backend

A Flask-based backend service that provides AI-powered responses to questions about Stouffville by-laws using Google's Gemini AI and ChromaDB vector search.

## Features

- REST API for querying the Gemini AI model
- Simple web-based demo interface for testing without the frontend
- CORS support for frontend integration
- 30-second timeout protection for AI queries
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
  "query": "What are the noise restrictions in Stouffville?"
}
```

**Response (Success):**
```json
{
  "answer": "The AI-generated response about Stouffville by-laws",
  "source": "chroma"
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
   - Queries should be sent as JSON with a `query` field
   - Responses will contain either an `answer` field with the AI response or an `error` field
   - Responses now include a `source` field indicating whether the data came from ChromaDB or the JSON file

## Project Structure

- `app.py`: Main Flask application
- `app/`: Application package
  - `__init__.py`: Package initialization
  - `prompts.py`: AI prompt templates
  - `chroma_retriever.py`: ChromaDB integration for vector search
  - `templates/`: HTML templates for web interfaces
    - `demo.html`: Enhanced demo page with improved UI

## Database

The application uses two database approaches for by-laws:

1. **JSON Database**:
   - `parking_related_by-laws.json`: Contains by-laws related to parking regulations
   - `search_bylaws.py`: Utility script for searching and extracting by-laws by keyword

2. **Vector Database (ChromaDB)**:
   - Stores vector embeddings for efficient semantic search
   - Uses Voyage AI embeddings for high-quality semantic understanding
   - Located in `../database/chroma-data/` directory
   - Initialized using `../database/init_chroma.py` script

## Vector Search Functionality

The application uses ChromaDB and Voyage AI embeddings to provide intelligent retrieval:

1. When a query is received, the system first attempts to find relevant by-laws using vector search
2. If relevant documents are found, only those specific by-laws are sent to Gemini AI
3. If ChromaDB is unavailable or no relevant documents are found, falls back to using the JSON database
4. Demo interface shows source information for transparency

## Important Implementation Details

- The backend uses the `gemini-2.0-flash` model
- A 30-second timeout is applied to all AI queries to prevent long-running requests
- The AI is configured to provide comprehensive HTML-formatted responses 
- Error handling is implemented for both API key issues and model processing errors, including timeouts
- ChromaDB fallbacks ensure the system works even if vector search is unavailable

## Development Notes

- Running in debug mode for development (debug=True)
- For production deployment, set debug=False and configure a proper WSGI server 