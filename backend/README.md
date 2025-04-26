# Stouffville By-laws AI Backend

A Flask-based backend service that provides AI-powered responses to questions about Stouffville by-laws using Google's Gemini AI and ChromaDB vector search.

## Features

- REST API for querying the Gemini AI model
- Multiple Gemini model options for different performance/quality needs
- Enhanced search capability that transforms user queries into legal language for better semantic search
- Token counting and cost calculation for each query
- Optimized expired by-laws filtering using a two-step prompting approach for cost efficiency and speed
- Layman's terms conversion that transforms legal language into plain, everyday language accessible to residents
- Comparison mode to see differences between complete, filtered, and layman's terms versions
- Performance metrics showing execution time for bylaw retrieval and each prompt (in demo interface)
- Configurable number of bylaws to retrieve (5, 10, 15, or 20) in the demo interface
- Simple web-based demo interface for testing without the frontend
- Interactive bylaw viewer with detailed information about specific bylaws
- Direct bylaw linking and sidebar viewing from AI responses
- CORS support for frontend integration
- 50-second timeout protection for AI queries
- Customizable temperature settings for different prompt types
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
  "laymans_answer": "The AI-generated response in simple, everyday language without bylaw references",
  "source": "ChromaDB",
  "bylaw_numbers": ["2015-139-RE", "2015-04-RE"],
  "model": "gemini-2.0-flash",
  "retrieval_time": 0.45
}
```

**Response (Error):**
```json
{
  "error": "Error message"
}
```

### GET `/api/bylaw/<bylaw_number>`

Retrieves the full JSON data for a specific bylaw by its number. Intelligently handles different format variations of bylaw numbers.

**Response (Success):**
```json
{
  "bylawNumber": "2023-060-RE",
  "bylawType": "Regulation",
  "bylawYear": "2023",
  "condtionsAndClauses": "...",
  "laymanExplanation": "...",
  "content": "...",
  ...
}
```

**Response (Error):**
```json
{
  "error": "No bylaws found matching 2023-060-RE"
}
```

### GET/POST `/api/demo`

A standalone web demo page with a simple form interface:
- GET: Returns the demo page
- POST: Processes the query and displays the result with source information

The demo page includes:
- Model selection dropdown
- Bylaw limit selection (5, 10, 15, or 20 bylaws)
- Enhanced search option that transforms user queries into legal language
- Token counting and cost calculation for input and output
- Comparison mode to show all three versions of the response (complete, filtered, and layman's terms)
- Side-by-side view option for easier comparison
- Performance metrics showing retrieval and processing times
- Visualization of bylaws found specifically by enhanced search
- Interactive sidebar to view full bylaw details directly from hyperlinks

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
   pip install flask flask-cors langchain langchain-google-genai langchain-chroma langchain-voyageai chromadb python-dotenv tiktoken

   # Run the application
   python app.py
   ```

   The server will run at `http://localhost:5000`

3. **Integration with Frontend**

   - Backend is configured with CORS support for frontend integration
   - Use the `/api/ask` endpoint for all AI queries from your React app
   - Queries should be sent as JSON with a `query` field and optional `model` field
   - Responses will contain `answer`, `filtered_answer`, and `laymans_answer` fields with the AI responses, or an `error` field
   - Responses include a `source` field indicating the data comes from ChromaDB
   - Responses include a `bylaw_numbers` array listing the referenced by-laws

## Project Structure

- `app.py`: Main Flask application
- `app/`: Application package
  - `__init__.py`: Package initialization with simplified imports
  - `prompts.py`: AI prompt templates (including filtered version for active by-laws only, layman's terms conversion, and enhanced search)
  - `chroma_retriever.py`: ChromaDB integration for vector search
  - `gemini_handler.py`: Gemini AI model integration and response processing
  - `token_counter.py`: Token counting and cost calculation utilities
  - `templates/`: HTML templates for web interfaces
    - `demo.html`: Enhanced demo page with improved UI, model selection, and comparison features
  - `static/`: Static assets for web interfaces
    - `demo.css`: CSS styling for the demo interface
    - `demo.js`: JavaScript for the demo interface
    - `bylawViewer.html`: Bylaw viewer interface
    - `bylawViewer.css`: CSS styling for the bylaw viewer
    - `bylawViewer.js`: JavaScript for the bylaw viewer

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
2. If enhanced search is enabled, the system:
   - Transforms the user query into formal, bylaw-oriented language
   - Performs two searches: one with the original query and one with the transformed query
   - Combines results, removing duplicates
3. If relevant documents are found, those specific by-laws are sent to Gemini AI
4. The system generates three different responses:
   - A complete answer using all retrieved by-laws
   - A filtered answer that removes expired by-laws from the first response
   - A layman's terms answer that simplifies the language and removes bylaw references from the filtered response
5. Demo interface provides options to compare all three responses

## Bylaw Viewer Feature

The application includes an interactive bylaw viewer that:

1. Displays detailed information about specific bylaws in a user-friendly format
2. Supports direct linking to bylaws from AI responses using hyperlinks
3. Can open bylaws in a sidebar without leaving the main interface
4. Features a dark mode toggle for better readability
5. Intelligently formats:
   - Tables and lists from bylaw content
   - Location addresses with Google Maps links
   - Links to original PDF documents
   - Formatted text with proper spacing and line breaks
6. Shows comprehensive metadata including:
   - Bylaw number, type, and year
   - Layman's explanation in simple terms
   - Key dates and information
   - Conditions and clauses
   - Legal topics and related legislation
   - Entity and designation information
   - And many more fields when available

## Optimized Three-Step Prompt System

The system uses a cost-efficient multi-step approach for processing by-laws information:

1. **First Prompt**: The complete by-laws content is sent to the Gemini model along with the user question to generate a comprehensive response
2. **Second Prompt**: Instead of sending the by-laws content again, the system sends only the first response to a second prompt that filters out expired by-laws
3. **Third Prompt**: The filtered response is sent to a third prompt that transforms the legal language into plain, everyday language and removes all bylaw references
4. **Benefits**:
   - Significantly reduces token usage and API costs
   - Maintains quality by having each prompt focus on a specific task
   - Preserves formatting while transforming content appropriately at each step
   - Increases speed
   - Makes it possible to choose a more suitable model for each prompt to improve speed, accuracy, and cost

## Gemini AI Models

The backend supports multiple Gemini model options:

- `gemini-mixed`: Uses the best model for each query stage (default)
- `gemini-2.0-flash-lite`: Fastest, lowest cost option
- `gemini-2.0-flash`: Balanced speed and quality
- `gemini-2.5-flash-preview-04-17`: Fast, high quality option
- `gemini-2.5-pro-exp-03-25`: Highest quality, but most expensive

The gemini-mixed option selects different models for different processing stages:
- Query transformation: Uses `gemini-2.0-flash` for efficient query enhancement
- First query (bylaws): Uses `gemini-2.5-flash-preview-04-17` for highest quality initial response
- Second query (filtered): Uses `gemini-2.0-flash` for efficient filtering of expired bylaws
- Third query (layman's terms): Uses `gemini-2.0-flash` for balanced quality/speed in final simplification

Each prompt type uses a specific temperature setting for optimal results:
- Bylaws prompt: 0.0 (consistent, deterministic outputs)
- Filtered prompt: 0.0 (consistent, deterministic outputs)
- Layman's terms prompt: 0.7 (more creative, natural language)
- Enhanced search prompt: 0.2 (slightly varied outputs while maintaining accuracy)

## Token Counting and Cost Calculation

The system includes a token counting utility that:
- Counts input tokens (bylaws content and prompts)
- Counts output tokens (all three responses)
- Calculates costs based on model-specific pricing
- Displays token usage and costs in the demo interface

## Important Implementation Details

- The backend defaults to the `gemini-2.0-flash` model
- A 50-second timeout is applied to all AI queries to prevent long-running requests
- The AI is configured to provide comprehensive HTML-formatted responses 
- Error handling is implemented for API key issues, model selection, and processing errors
- Responses include current date information to help with determining expired by-laws
- Bylaw responses include cache-prevention headers to ensure fresh data

## Development Notes

- Running in debug mode for development (debug=True)
- For production deployment, set debug=False and configure a proper WSGI server 