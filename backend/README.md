# Stouffville By-laws AI Backend

A Flask-based backend service that provides AI-powered responses to questions about Stouffville by-laws using Google's Gemini AI.

## Features

- REST API for querying the Gemini AI model
- Simple web-based demo interface for testing without the frontend
- CORS support for frontend integration

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
  "answer": "The AI-generated response about Stouffville by-laws"
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
- POST: Processes the query and displays the result

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
   ```

2. **Running the Backend Locally**

   ```bash
   # Install dependencies
   pip install flask flask-cors langchain langchain-google-genai python-dotenv

   # Run the application
   python app.py
   ```

   The server will run at `http://localhost:5000`

3. **Integration with Frontend**

   - Backend is configured with CORS support for frontend integration
   - Use the `/api/ask` endpoint for all AI queries from your React app
   - Queries should be sent as JSON with a `query` field
   - Responses will contain either an `answer` field with the AI response or an `error` field

## Important Implementation Details

- The AI is configured to provide one-sentence responses by default
- The backend uses the `gemini-2.0-flash-thinking-exp-01-21` model
- Error handling is implemented for both API key issues and model processing errors

## Development Notes

- Running in debug mode for development (debug=True)
- For production deployment, set debug=False and configure a proper WSGI server 