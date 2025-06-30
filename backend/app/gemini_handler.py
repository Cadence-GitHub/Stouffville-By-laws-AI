import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.output_parser import StrOutputParser
from app.prompts import (
    get_bylaws_prompt_template, 
    LAYMANS_PROMPT_TEMPLATE, ENHANCED_SEARCH_PROMPT_TEMPLATE,
    TEMPERATURES, VOICE_PROMPT_TEMPLATE
)
import time
import re
from langchain_core.messages import HumanMessage

# Define allowed models
ALLOWED_MODELS = [
    "gemini-mixed",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite", 
    "gemini-2.5-flash"
]

def invoke_model_with_timing(prompt_type, model_config, prompt_template, prompt_args):
    """
    Helper function to invoke a model with a prompt template and return the response and timing.
    
    Args:
        prompt_type: Type of prompt to determine temperature
        model_config: Configuration for LLM model
        prompt_template: The prompt template to use
        prompt_args (dict): The arguments to pass to the prompt template
    
    Returns:
        tuple: (cleaned_response, execution_time)
    """
    start_time = time.time()
    
    # Get temperature for this prompt type
    temperature = TEMPERATURES.get(prompt_type, 0.0)
    
    # Create model instance with the appropriate temperature
    model_instance = ChatGoogleGenerativeAI(
        model=model_config['model'],
        google_api_key=model_config['api_key'],
        timeout=model_config['timeout'],
        temperature=temperature
    )
    
    # Create and invoke the chain
    chain = prompt_template | model_instance | StrOutputParser()
    response = chain.invoke(prompt_args)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Clean the response
    cleaned_response = clean_response(response)
    
    return cleaned_response, execution_time

def convert_bylaw_tags_to_links(text):
    """
    Convert <BYLAW_URL> tags to proper HTML hyperlinks.
    
    Args:
        text (str): Text with <BYLAW_URL> tags
        
    Returns:
        str: Text with proper HTML hyperlinks
    """
    # Find all instances of <BYLAW_URL>...</BYLAW_URL>
    pattern = r'<BYLAW_URL>(.*?)</BYLAW_URL>'
    
    def replace_with_link(match):
        bylaw_text = match.group(1)
        # Extract just the bylaw number for the URL parameter
        # Split on space and take the last part - this handles various formats like:
        # "By-law 2024-103", "bylaw 2024-103", "by law 2024-103", "Bylaw 2024-103", etc.
        parts = bylaw_text.split()
        if len(parts) > 1:
            # Take the last part as the bylaw number
            bylaw_number = parts[-1]
        else:
            # If no spaces, use the entire text as the bylaw number
            bylaw_number = bylaw_text

        return f'<a href="/static/bylawViewer.html?bylaw={bylaw_number}" target="_blank" rel="noopener noreferrer">{bylaw_text}</a>'
    
    # Replace all instances of the pattern with proper hyperlinks
    result = re.sub(pattern, replace_with_link, text)
    
    return result

def get_gemini_response(query, relevant_bylaws, model="gemini-2.0-flash", bylaw_status="active"):
    """
    Process user queries through the Gemini AI model.
    
    Args:
        query (str): The user's question about Stouffville by-laws
        relevant_bylaws (list): List of by-laws relevant to the query
        model (str): The Gemini model to use (default: gemini-2.0-flash)
        bylaw_status (str): Status of bylaws being queried (default: "active")
        
    Returns:
        dict: Contains either the AI response(s) or error information
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY environment variable is not set"}
    
    if not relevant_bylaws:
        return {"error": "No relevant bylaws found in ChromaDB"}
    
    # Validate model
    if model not in ALLOWED_MODELS:
        return {"error": f"Invalid model: {model}. Only these models are allowed: {', '.join(ALLOWED_MODELS)}"}
    
    try:
        # Define models to use for each step based on selection
        if model == "gemini-mixed":
            # For gemini-mixed option, use specific models for each step
            models = {
                "bylaws": "gemini-2.5-flash",  # Best model for first query
                "laymans": "gemini-2.0-flash"                # Balanced model for second query
            }
        else:
            # For all other options, use the selected model for all steps
            models = {
                "bylaws": model,
                "laymans": model
            }
        
        bylaws_content = json.dumps(relevant_bylaws, indent=2)
        
        # Helper function to perform a model invocation step
        def run_model_step(prompt_type, prompt_template, prompt_args):
            model_config = {
                'model': models[prompt_type],
                'api_key': api_key,
                'timeout': 50
            }
            return invoke_model_with_timing(
                prompt_type,
                model_config,
                prompt_template,
                prompt_args
            )
        
        # 1. Get response with all bylaws
        cleaned_full_response, first_prompt_time = run_model_step(
            "bylaws",
            get_bylaws_prompt_template(bylaw_status),
            {"bylaws_content": bylaws_content, "question": query}
        )
        
        # Process XML tags in the full response to convert them to HTML links (non-LLM step)
        cleaned_filtered_response = convert_bylaw_tags_to_links(cleaned_full_response)
        
        # 2. Get layman's terms response using the filtered response as input
        laymans_response, second_prompt_time = run_model_step(
            "laymans",
            LAYMANS_PROMPT_TEMPLATE,
            {"filtered_response": cleaned_filtered_response, "question": query}
        )
        
        return {
            "answer": cleaned_full_response,
            "filtered_answer": cleaned_filtered_response,
            "laymans_answer": laymans_response,
            "timings": {
                "first_prompt": first_prompt_time,
                "second_prompt": second_prompt_time
            }
        }
    except Exception as e:
        return {"error": str(e)}

def transform_query_for_enhanced_search(query, model="gemini-2.0-flash"):
    """
    Transform a user query into formal, bylaw-oriented language for enhanced search.
    
    Args:
        query (str): Original user query
        model (str): The Gemini model to use for transformation
        
    Returns:
        tuple: (transformed_query, transform_time) or (original_query, 0) if transformation fails
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY environment variable is not set")
        return query, 0
    
    try:
        # For the gemini-mixed option, always use gemini-2.0-flash for query transformation
        transform_model = "gemini-2.0-flash" if model == "gemini-mixed" else model
        
        model_config = {
            'model': transform_model,
            'api_key': api_key,
            'timeout': 30
        }
        
        # Transform user query to formal bylaw language
        return invoke_model_with_timing(
            "enhanced_search",
            model_config,
            ENHANCED_SEARCH_PROMPT_TEMPLATE,
            {"question": query}
        )
    except Exception as e:
        print(f"Query transformation failed: {str(e)}")
        # Fall back to original query if transformation fails
        return query, 0

def clean_response(response):
    """
    Clean up LLM responses by removing markdown code block indicators while preserving HTML content.
    
    Args:
        response (str): The raw response from the LLM
        
    Returns:
        str: Cleaned response without markdown formatting
    """
    # Remove ```html at the beginning if present
    if response.strip().startswith("```html"):
        response = response.strip()[7:]
    elif response.strip().startswith("```"):
        response = response.strip()[3:]
        
    # Remove ``` at the end if present
    if response.strip().endswith("```"):
        response = response.strip()[:-3]
    
    # Final trim to remove any extra whitespace
    response = response.strip()
    
    return response 

def get_provincial_law_info(bylaw_type, model="gemini-2.0-flash"):
    """Get information about provincial laws using Google Search grounding."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY environment variable is not set"}
    
    if model not in ALLOWED_MODELS:
        return {"error": f"Invalid model: {model}. Only these models are allowed: {', '.join(ALLOWED_MODELS)}"}
    
    try:
        # Define model to use
        if model == "gemini-mixed":
            model_to_use = "gemini-2.0-flash"
        else:
            model_to_use = model
            
        # Start timing
        start_time = time.time()
        

        ## TODO: rewrite this in Langchain
        # Construct request URL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_to_use}:generateContent?key={api_key}"
        
        # Prepare request payload
        # TODO: we need to use the prompt from the prompts.py file instead of hardcoding it
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"""Provide information about how {bylaw_type} bylaws in Whitchurch-Stouffville, Ontario, Canada 
                        are informed or regulated by Ontario provincial laws and regulations.
                        
                        Your response should:
                        1. Identify the key provincial statutes and regulations that govern municipal authority in this area
                        2. Explain how provincial laws establish the framework and limitations for municipal bylaws
                        3. Highlight any recent changes to provincial legislation that affect municipal bylaws
                        4. Format your response using HTML for better presentation
                        5. Be concise, informative, and focused on the relationship between provincial and municipal legislation"""}
                    ]
                }
            ],
            "tools": [
                {
                    "google_search": {}
                }
            ],
            "generationConfig": {
                "temperature": TEMPERATURES.get("provincial_law", 0.2),
                "topP": 0.8,
                "maxOutputTokens": 1024
            }
        }
        
        # Send request
        import requests
        response = requests.post(
            url=url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Parse JSON response
        result = response.json()
        

        # Debug print to console - add this
        import json
        print(f"PROVINCIAL LAW API RESPONSE ({bylaw_type}):")
        print(json.dumps(result, indent=2))

        ## TODO: rewrite this so that the links match what the Gemini refers to in its response
        # Extract the provincial info from response
        provincial_info = ""
        sources = []
        search_queries = []
        
        if "candidates" in result and result["candidates"]:
            candidate = result["candidates"][0]
            
            # Extract content
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        provincial_info += part["text"]
            
            # Extract grounding metadata
            if "groundingMetadata" in candidate:
                # Extract search queries
                if "webSearchQueries" in candidate["groundingMetadata"]:
                    search_queries = candidate["groundingMetadata"]["webSearchQueries"]
                
                # Try to extract sources from groundingChunks if available
                if "groundingChunks" in candidate["groundingMetadata"]:
                    for chunk in candidate["groundingMetadata"]["groundingChunks"]:
                        if "web" in chunk:
                            sources.append({
                                "title": chunk["web"].get("title", ""),
                                "url": chunk["web"].get("uri", "")
                            })
                
                # If no sources found and searchEntryPoint available, parse HTML
                if not sources and "searchEntryPoint" in candidate["groundingMetadata"]:
                    if "renderedContent" in candidate["groundingMetadata"]["searchEntryPoint"]:
                        html_content = candidate["groundingMetadata"]["searchEntryPoint"]["renderedContent"]
                        
                        # Simple regex-based extraction to avoid requiring BeautifulSoup
                        import re
                        chip_pattern = r'<a class="chip" href="(https://vertexaisearch[^"]+)">([^<]+)</a>'
                        for match in re.finditer(chip_pattern, html_content):
                            sources.append({
                                "url": match.group(1),
                                "title": match.group(2)
                            })
        
        # Clean the response
        provincial_info = clean_response(provincial_info)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            "provincial_info": provincial_info,
            "sources": sources,
            "timings": {
                "processing_time": execution_time
            }
        }
    except Exception as e:
        return {"error": str(e)}

# Process voice queries
def process_voice_query(encoded_audio: str, mime_type: str, model: str = "gemini-2.0-flash"):
    """
    Process a voice query audio using the VOICE_PROMPT_TEMPLATE and return the reformulated question
    or NO_BYLAW_QUESTION_DETECTED.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "Error: GOOGLE_API_KEY environment variable is not set"

    # Initialize the LLM for voice transcription
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        timeout=30
    )

    # Create a HumanMessage with the template and audio media
    message = HumanMessage(
        content=[
            {"type": "text", "text": VOICE_PROMPT_TEMPLATE.template},
            {"type": "media", "data": encoded_audio, "mime_type": mime_type}
        ]
    )

    # Invoke the model
    response = llm.invoke([message])

    # Return the content of the response
    return response.content