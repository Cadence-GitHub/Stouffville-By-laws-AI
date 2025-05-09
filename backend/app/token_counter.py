import json
import tiktoken
from app.prompts import (
    BYLAWS_PROMPT_TEMPLATE, 
    LAYMANS_PROMPT_TEMPLATE, 
    ENHANCED_SEARCH_PROMPT_TEMPLATE
)

# Model pricing information (cost per 1M tokens)
MODEL_PRICING = {
    "gemini-mixed": {"input": 0.15, "output": 2.00},  # Estimated cost for gemini-mixed
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.07, "output": 0.30},
    "gemini-2.5-pro-exp-03-25": {"input": 1.25, "output": 10.00}
}

def count_tokens(bylaws=None, response=None, model="gemini-2.0-flash"):
    """
    Count tokens in bylaws data and Gemini responses using tiktoken.
    Also calculates the cost based on the model used.
    
    Args:
        bylaws: The bylaws data to count input tokens for (optional)
        response: The Gemini response to count output tokens for (optional)
        model: The model name used for pricing
        
    Returns:
        dict: Contains input_tokens, output_tokens counts, and associated costs
    """
    try:
        # Use cl100k_base encoding (used by many models including GPT-4)
        encoding = tiktoken.get_encoding("cl100k_base")
        
        token_counts = {
            'input_tokens': 0,
            'output_tokens': 0,
            'input_cost': 0,
            'output_cost': 0,
            'total_cost': 0
        }
        
        # Count input tokens if bylaws are provided
        if bylaws:
            # Convert all bylaws to JSON string (this is what's sent to the LLM)
            bylaws_json = json.dumps(bylaws, indent=2)
            
            # Count tokens in the JSON string
            input_tokens = len(encoding.encode(bylaws_json))
            
            # Calculate prompt template token counts
            bylaws_template = BYLAWS_PROMPT_TEMPLATE.template.replace("{bylaws_content}", "").replace("{question}", "")
            laymans_template = LAYMANS_PROMPT_TEMPLATE.template.replace("{filtered_response}", "").replace("{question}", "")
            enhanced_template = ENHANCED_SEARCH_PROMPT_TEMPLATE.template.replace("{question}", "")

            # Count tokens for each template
            bylaws_template_tokens = len(encoding.encode(bylaws_template))
            laymans_template_tokens = len(encoding.encode(laymans_template))
            enhanced_template_tokens = len(encoding.encode(enhanced_template))
            
            # Calculate total input tokens (input + all templates)
            token_counts['input_tokens'] = input_tokens + bylaws_template_tokens + laymans_template_tokens + enhanced_template_tokens
        
        # Count output tokens if response is provided
        if response:
            # Get all responses
            full_response = response.get('answer', '')
            filtered_response = response.get('filtered_answer', '')
            laymans_response = response.get('laymans_answer', '')
            
            # Count tokens in each response
            full_tokens = len(encoding.encode(full_response))
            filtered_tokens = len(encoding.encode(filtered_response))
            laymans_tokens = len(encoding.encode(laymans_response))
            
            # Calculate total output tokens
            token_counts['output_tokens'] = full_tokens + filtered_tokens + laymans_tokens
        
        # Calculate costs based on model
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gemini-2.0-flash"])
        token_counts['input_cost'] = (token_counts['input_tokens'] / 1000000) * pricing["input"]
        token_counts['output_cost'] = (token_counts['output_tokens'] / 1000000) * pricing["output"]
        token_counts['total_cost'] = token_counts['input_cost'] + token_counts['output_cost']
        
        return token_counts
    except Exception as e:
        return {
            'input_tokens': f"Token count error: {str(e)}",
            'output_tokens': f"Token count error: {str(e)}",
            'input_cost': 0,
            'output_cost': 0,
            'total_cost': 0
        } 