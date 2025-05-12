import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.output_parser import StrOutputParser
from app.prompts import (
    get_bylaws_prompt_template, 
    LAYMANS_PROMPT_TEMPLATE, ENHANCED_SEARCH_PROMPT_TEMPLATE,
    TEMPERATURES
)
import time
import re

# Define allowed models
ALLOWED_MODELS = [
    "gemini-mixed",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite", 
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro-exp-03-25"
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

def convert_bylaw_tags_to_links(text, relevant_bylaws_all_fields=None):
    """
    Convert <BYLAW_URL> tags to proper HTML hyperlinks.
    
    Args:
        text (str): Text with <BYLAW_URL> tags
        relevant_bylaws_all_fields (list, optional): List of bylaws with all fields, including urlOriginalDocument
        
    Returns:
        str: Text with proper HTML hyperlinks
    """
    # Find all instances of <BYLAW_URL>...</BYLAW_URL>
    pattern = r'<BYLAW_URL>(.*?)</BYLAW_URL>'
    
    def replace_with_link(match):
        bylaw_text = match.group(1)
        # Extract just the bylaw number for the URL parameter
        # We need to handle various formats like "By-law 2024-103" or just "2024-103"
        bylaw_number = bylaw_text
        if "By-law" in bylaw_text:
            bylaw_parts = bylaw_text.split("By-law")
            if len(bylaw_parts) > 1:
                bylaw_number = bylaw_parts[1].strip()
        
        # If we have relevant_bylaws_all_fields and it contains this bylaw number, use its urlOriginalDocument
        """if relevant_bylaws_all_fields:
            for bylaw in relevant_bylaws_all_fields:
                if bylaw.get("bylawNumber") == bylaw_number and bylaw.get("urlOriginalDocument"):
                    return f'<a href="{bylaw["urlOriginalDocument"]}" target="_blank" rel="noopener noreferrer">{bylaw_text}</a>'"""
        
        # Default fallback to the bylawViewer.html if no urlOriginalDocument found
        return f'<a href="/static/bylawViewer.html?bylaw={bylaw_number}" target="_blank" rel="noopener noreferrer">{bylaw_text}</a>'
    
    # Replace all instances of the pattern with proper hyperlinks
    result = re.sub(pattern, replace_with_link, text)
    
    return result

def get_gemini_response(query, relevant_bylaws, model="gemini-2.0-flash", bylaw_status="active", relevant_bylaws_all_fields=None):
    """
    Process user queries through the Gemini AI model.
    
    Args:
        query (str): The user's question about Stouffville by-laws
        relevant_bylaws (list): List of by-laws relevant to the query
        model (str): The Gemini model to use (default: gemini-2.0-flash)
        bylaw_status (str): Status of bylaws being queried (default: "active")
        relevant_bylaws_all_fields (list, optional): List of bylaws with all fields, for linking to original documents
        
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
                "bylaws": "gemini-2.5-flash-preview-04-17",  # Best model for first query
                "filtered": "gemini-2.0-flash",              # Balanced model for second query
                "laymans": "gemini-2.0-flash"                # Balanced model for third query
            }
        else:
            # For all other options, use the selected model for all steps
            models = {
                "bylaws": model,
                "filtered": model,
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
        cleaned_filtered_response = convert_bylaw_tags_to_links(cleaned_full_response, relevant_bylaws_all_fields)
        
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