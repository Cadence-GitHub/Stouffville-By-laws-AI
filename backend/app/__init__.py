# Stouffville By-laws AI Assistant
# This package contains utility modules for the backend Flask application 

from app.chroma_retriever import ChromaDBRetriever
from app.gemini_handler import get_gemini_response, transform_query_for_enhanced_search, ALLOWED_MODELS
from app.prompts import BYLAWS_PROMPT_TEMPLATE, FILTERED_BYLAWS_PROMPT_TEMPLATE, LAYMANS_PROMPT_TEMPLATE, ENHANCED_SEARCH_PROMPT_TEMPLATE
from app.token_counter import count_tokens, MODEL_PRICING 