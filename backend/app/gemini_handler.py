import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.output_parser import StrOutputParser
from app.prompts import BYLAWS_PROMPT_TEMPLATE, FILTERED_BYLAWS_PROMPT_TEMPLATE, LAYMANS_PROMPT_TEMPLATE, ENHANCED_SEARCH_PROMPT_TEMPLATE
import time

# Define allowed models
ALLOWED_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite", 
    "gemini-2.0-flash-thinking-exp-01-21",
    "gemini-2.5-pro-exp-03-25"
]

def invoke_model_with_timing(model_instance, prompt_template, prompt_args):
    """
    Helper function to invoke a model with a prompt template and return the response and timing.
    
    Args:
        model_instance: The initialized LLM model instance
        prompt_template: The prompt template to use
        prompt_args (dict): The arguments to pass to the prompt template
    
    Returns:
        tuple: (cleaned_response, execution_time)
    """
    start_time = time.time()
    
    # Create and invoke the chain
    chain = prompt_template | model_instance | StrOutputParser()
    response = chain.invoke(prompt_args)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Clean the response
    cleaned_response = clean_response(response)
    
    return cleaned_response, execution_time

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
        
        # 1. Get response with all bylaws (original behavior)
        cleaned_full_response, first_prompt_time = invoke_model_with_timing(
            model_instance, 
            BYLAWS_PROMPT_TEMPLATE, 
            {"bylaws_content": bylaws_content, "question": query}
        )
        
        # 2. Get filtered response using the first response as input instead of the full bylaws content
        cleaned_filtered_response, second_prompt_time = invoke_model_with_timing(
            model_instance,
            FILTERED_BYLAWS_PROMPT_TEMPLATE,
            {"first_response": cleaned_full_response, "question": query}
        )
        
        # 3. Get layman's terms response using the filtered response as input
        laymans_response, third_prompt_time = invoke_model_with_timing(
            model_instance,
            LAYMANS_PROMPT_TEMPLATE,
            {"filtered_response": cleaned_filtered_response, "question": query}
        )
        
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
        # Initialize model for enhanced query transformation
        transform_model = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            timeout=30
        )
        
        # Transform user query to formal bylaw language using the helper function
        transformed_query, transform_time = invoke_model_with_timing(
            transform_model,
            ENHANCED_SEARCH_PROMPT_TEMPLATE,
            {"question": query}
        )
        
        return transformed_query, transform_time
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