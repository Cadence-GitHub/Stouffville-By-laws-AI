# Stouffville By-laws AI Backend

A Flask-based backend service that provides AI-powered responses to questions about Stouffville by-laws using Google's Gemini AI and ChromaDB vector search.

## Features

- REST API for querying the Gemini AI model
- Multiple Gemini model options for different performance/quality needs
- Enhanced search capability that transforms user queries into legal language for better semantic search
- Token counting and cost calculation for each query
- Bylaw status filtering allowing users to search specifically for active or inactive bylaws
- Optimized vector search with direct filtering for bylaw status (active/inactive)
- Specialized prompt template for inactive bylaws that clearly identifies them as no longer in effect and explains why
- Metadata preservation for inactive bylaws to explain their non-active status via the "whyNotActive" field
- Layman's terms conversion that transforms legal language into plain, everyday language accessible to residents
- Comparison mode to see differences between technical and layman's terms versions
- Performance metrics showing execution time for bylaw retrieval and each prompt (in demo interface)
- Configurable number of bylaws to retrieve (5, 10, 15, or 20) in the demo interface
- Intelligent autocomplete feature that provides suggestions as users type their queries (minimum 3 characters)
- Simple web-based demo interface for testing without the frontend
- Interactive bylaw viewer with detailed information about specific bylaws
- Direct bylaw linking and sidebar viewing from AI responses
- XML tag processing for bylaw references that converts them to proper HTML hyperlinks
- One-click bug reporting system with automatic context capture for GitHub Issues
- CORS support for frontend integration
- 50-second timeout protection for AI queries
- Customizable temperature settings for different prompt types
- ChromaDB vector search integration with dual Voyage AI embedding models:
  - `voyage-3-large` for the main by-laws collection for highest quality retrieval
  - `voyage-3-lite` for the questions collection used in autocomplete functionality

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
  "model": "gemini-2.0-flash",
  "bylaw_status": "active"
}
```

**Response (Success):**
```json
{
  "answer": "The AI-generated response about Stouffville by-laws with bylaw references",
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

Retrieves the full JSON data for a specific bylaw by its number. Intelligently handles different format variations of bylaw numbers and automatically removes `-XX` pattern suffixes.

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

### POST `/api/autocomplete`

Returns autocomplete suggestions for a partial query, finding semantically similar questions.

**Request Body:**
```json
{
  "query": "can I park my car"
}
```

**Response (Success):**
```json
{
  "suggestions": [
    "Can I park my car on the street overnight during the winter?",
    "Where can I park my car during snow removal?"
  ],
  "retrieval_time": 0.15
}
```

**Response (Error):**
```json
{
  "error": "Questions collection does not exist. Run ingest_questions.py first."
}
```

Note: This endpoint returns an empty array if the query is less than 3 characters long.

### GET/POST `/api/demo`

A standalone web demo page with a simple form interface:
- GET: Returns the demo page
- POST: Processes the query and displays the result with source information

The demo page includes:
- Model selection dropdown
- Bylaw status filter dropdown (active or inactive bylaws)
- Bylaw limit selection (5, 10, 15, or 20 bylaws)
- Enhanced search option that transforms user queries into legal language
- Intelligent autocomplete that suggests similar questions as you type
- Token counting and cost calculation for input and output
- Comparison mode to show both versions of the response (technical with bylaw references and layman's terms)
- Side-by-side view option for easier comparison
- Performance metrics showing retrieval and processing times
- Visualization of bylaws found specifically by enhanced search
- Interactive sidebar to view full bylaw details directly from hyperlinks
- "Problem? Log a bug!" buttons under each answer type that capture complete context for GitHub Issues

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
  - `prompts.py`: AI prompt templates (including specialized template for inactive bylaws, layman's terms conversion, and enhanced search)
  - `chroma_retriever.py`: ChromaDB integration for vector search with direct active bylaw filtering
  - `gemini_handler.py`: Gemini AI model integration and response processing
  - `token_counter.py`: Token counting and cost calculation utilities
  - `templates/`: HTML templates for web interfaces
    - `demo.html`: Enhanced demo page with improved UI, model selection, and comparison features
  - `static/`: Static assets for web interfaces
    - `demo.css`: CSS styling for the demo interface, including autocomplete styles
    - `demo.js`: JavaScript for the demo interface, including autocomplete functionality and bug report generation
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
   - Contains a "questions" collection for autocomplete functionality, initialized using `../database/ingest_questions.py`

## Vector Search Functionality

The application uses ChromaDB and Voyage AI embeddings to provide intelligent retrieval:

1. When a query is received, the system attempts to find relevant by-laws using vector search
2. The vector search directly filters by bylaw status (active or inactive) based on user selection during retrieval
3. If inactive bylaws are requested, the system preserves the "isActive" and "whyNotActive" metadata fields for proper explanation
4. Unnecessary metadata fields are removed from the results to streamline the response
5. If enhanced search is enabled, the system:
   - Transforms the user query into formal, bylaw-oriented language
   - Performs two searches: one with the original query and one with the transformed query
   - Combines results, removing duplicates
6. If relevant documents are found, those specific by-laws are sent to Gemini AI
7. The system selects the appropriate prompt template based on bylaw status (active or inactive)
8. For inactive bylaws, a special preamble instructs the AI to clearly state that these bylaws are no longer in effect and explain why
9. The system generates two different responses:
   - A technical answer with bylaw references (using XML tags that are converted to HTML links)
   - A layman's terms answer that simplifies the language and removes bylaw references
10. Demo interface provides options to compare both responses

The system uses different embedding models for different collections:
- The main by-laws collection uses `voyage-3-large` for highest quality retrieval
- The questions collection (used for autocomplete) uses `voyage-3-lite` for efficient retrieval of similar questions

## Autocomplete Functionality

The application includes an intelligent autocomplete feature that:

1. Provides real-time suggestions as users type their queries
2. Activates when the user has typed at least 3 characters
3. Uses the ChromaDB "questions" collection to find semantically similar questions
4. Leverages the `voyage-3-lite` embedding model for efficient semantic matching
5. Displays suggestions in a dropdown below the search box
6. Allows navigating suggestions with keyboard arrows or mouse hover
7. Fills the input field with the selected suggestion when clicked or when Enter is pressed
8. Shows no suggestions if the "questions" collection doesn't exist in ChromaDB

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
7. Improved bylaw number handling that automatically removes `-XX` pattern suffixes for better matching

## Inactive Bylaw Handling

The application provides specialized handling for inactive bylaws:

1. **Preserving Crucial Metadata**: For inactive bylaws, the system preserves the "isActive" and "whyNotActive" metadata fields to explain their non-active status
2. **Specialized Prompt Template**: When querying about inactive bylaws, a special prompt template is used with a preamble that:
   - Clearly states at the beginning of responses that information is about bylaws no longer in effect
   - Always includes the reason why the bylaw is inactive using the "whyNotActive" field
   - Instructs the AI to provide the requested historical information rather than redirecting to current regulations
   - Preserves the appropriate tone and formatting for the response
3. **UI Selection**: Users can choose to query active or inactive bylaws through a dropdown in the interface
4. **Direct Vector Search Filtering**: Active/inactive status filtering is performed directly during vector search for efficiency

This feature ensures that when users specifically want information about inactive bylaws, they receive clear historical context with appropriate disclaimers.

## Bug Reporting System

The application includes a streamlined bug reporting system:

1. Each answer container has a "Problem? Log a bug!" button
2. When clicked, the button automatically:
   - Captures the user's query
   - Records the selected Gemini model
   - Notes the bylaws limit setting
   - Identifies if enhanced search was enabled
   - Captures the transformed query (if applicable)
   - Lists all retrieved bylaws
   - Records enhanced search bylaws (if applicable)
   - Captures timing information for all processing steps
   - Includes the specific answer content
3. This information is formatted as Markdown for clear, readable display in GitHub Issues
4. The user is directed to the GitHub issue creation page with all context data pre-populated
5. This helps to accurately track and resolve issues with the AI responses

## Optimized Two-Step Prompt System

The system uses a cost-efficient multi-step approach for processing by-laws information:

1. **Vector Search with Status Filtering**: The system directly filters by bylaw status (active or inactive) during vector search based on user selection
2. **Status-Based Template Selection**: The system selects the appropriate prompt template based on whether active or inactive bylaws are being queried
3. **First Prompt**: The filtered bylaws content is sent to the Gemini model along with the user question, generating a response with bylaw references in XML tags
4. **XML Tag Processing**: The system converts `<BYLAW_URL>By-law 2023-060-RE</BYLAW_URL>` tags to proper HTML hyperlinks (non-LLM step)
5. **Second Prompt**: The processed response with hyperlinks is sent to a second prompt that transforms the legal language into plain, everyday language and removes all bylaw references
6. **Benefits**:
   - Significantly reduces token usage and API costs by eliminating the separate filtering prompt
   - Maintains quality by having each prompt focus on a specific task
   - Preserves formatting while transforming content appropriately at each step
   - Increases speed with fewer LLM calls
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
- Second query (layman's terms): Uses `gemini-2.0-flash` for balanced quality/speed in final simplification

Each prompt type uses a specific temperature setting for optimal results:
- Bylaws prompt: 0.0 (consistent, deterministic outputs)
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