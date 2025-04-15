import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.output_parser import StrOutputParser
from app.prompts import BYLAWS_PROMPT_TEMPLATE, FILTERED_BYLAWS_PROMPT_TEMPLATE, LAYMANS_PROMPT_TEMPLATE
import time

# Define allowed models
ALLOWED_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite", 
    "gemini-2.0-flash-thinking-exp-01-21",
    "gemini-2.5-pro-exp-03-25"
]

def get_gemini_response(query, relevant_bylaws, model="gemini-2.0-flash"):
    """
    Process user queries through the Gemini AI model.
    
    Args:
        query (str): The user's question about Stouffville by-laws
        relevant_bylaws (list): List of by-laws relevant to the query
        model (str): The Gemini model to use (default: gemini-2.0-flash)
        
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
        # Initialize Gemini model with the specified version and 50 second timeout
        model_instance = ChatGoogleGenerativeAI(
            model=model, 
            google_api_key=api_key,
            timeout=50
        )
        
        bylaws_content = json.dumps(relevant_bylaws, indent=2)
        
        # Track timing for the first prompt
        start_first_prompt = time.time()
        
        # 1. Get response with all bylaws (original behavior)
        full_prompt = BYLAWS_PROMPT_TEMPLATE
        full_chain = full_prompt | model_instance | StrOutputParser()
        full_response = full_chain.invoke({"bylaws_content": bylaws_content, "question": query})
        
        # Calculate first prompt time
        first_prompt_time = time.time() - start_first_prompt
        
        # Clean up the first response to remove markdown code block indicators
        cleaned_full_response = clean_response(full_response)
        
        # Track timing for the second prompt
        start_second_prompt = time.time()
        
        # 2. Get filtered response using the first response as input instead of the full bylaws content
        filtered_prompt = FILTERED_BYLAWS_PROMPT_TEMPLATE
        filtered_chain = filtered_prompt | model_instance | StrOutputParser()
        filtered_response = filtered_chain.invoke({"first_response": cleaned_full_response, "question": query})
        
        # Calculate second prompt time
        second_prompt_time = time.time() - start_second_prompt
        
        # Clean up the filtered response
        cleaned_filtered_response = clean_response(filtered_response)
        
        # Track timing for the third prompt (layman's terms)
        start_third_prompt = time.time()
        
        # 3. Get layman's terms response using the filtered response as input
        laymans_prompt = LAYMANS_PROMPT_TEMPLATE
        laymans_chain = laymans_prompt | model_instance | StrOutputParser()
        laymans_response = laymans_chain.invoke({"filtered_response": cleaned_filtered_response, "question": query})
        
        # Calculate third prompt time
        third_prompt_time = time.time() - start_third_prompt
        
        # Final cleanup of responses
        laymans_response = clean_response(laymans_response)
        
        return {
            "answer": cleaned_full_response,
            "filtered_answer": cleaned_filtered_response,
            "laymans_answer": laymans_response,
            "timings": {
                "first_prompt": first_prompt_time,
                "second_prompt": second_prompt_time,
                "third_prompt": third_prompt_time
            }
        }
    except Exception as e:
        return {"error": str(e)}

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