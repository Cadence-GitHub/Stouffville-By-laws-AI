"""
Input validation and security utilities for the Stouffville By-laws AI API.
"""

import html
import unicodedata
from typing import Tuple, Any, Optional


def sanitize_query(query: Any) -> Tuple[str, bool, Optional[str]]:
    """
    Sanitize user query input.
    """
    # 1) Must be a string
    if not isinstance(query, str):
        return "", False, "Query must be a string"

    # 2) Strip null bytes, normalize Unicode, trim whitespace
    query = unicodedata.normalize("NFKC", query.replace("\x00", "")).strip()

    # 3) Enforce simple length bounds
    if len(query) < 3:
        return "", False, "Query must be at least 3 characters long"
    if len(query) > 2000:
        return "", False, "Query exceeds maximum length of 2000 characters"

    return query, True, None


def validate_bylaw_status(status: Any) -> Tuple[str, bool, Optional[str]]:
    """
    Validate bylaw status parameter.
    
    Args:
        status: Input status value (any type, will be validated)
        
    Returns:
        tuple: (validated_status, is_valid, error_message)
    """
    # Type validation
    if not isinstance(status, str):
        return 'active', False, "Bylaw status must be a string"
    
    # Normalize input
    status = status.strip().lower()
    
    # Validate allowed values
    allowed_statuses = ['active', 'inactive']
    if status not in allowed_statuses:
        return 'active', False, f"Bylaw status must be one of: {', '.join(allowed_statuses)}"
    
    return status, True, None


def validate_json_request(request_data: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate that the parsed JSON is an object.
    """
    if not isinstance(request_data, dict):
        return False, "Request body must be a JSON object"
    return True, None


def sanitize_for_logging(text: str) -> str:
    """
    Sanitize text for safe logging to prevent log injection.
    
    Args:
        text: Text to sanitize for logging
        
    Returns:
        str: HTML-escaped text safe for logging
    """
    # HTML escape to prevent log injection
    return html.escape(text)


def validate_api_request(request) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Validate content-type and JSON parse, then ensure object shape.
    """
    if not request.is_json:
        return False, "Content-Type must be application/json", None

    try:
        data = request.get_json()
    except Exception:
        return False, "Invalid JSON payload", None

    valid, error = validate_json_request(data)
    if not valid:
        return False, error, None

    return True, None, data


def validate_query_input(data: dict) -> Tuple[bool, Optional[str], str]:
    """
    Extract and validate query from request data.
    
    Args:
        data: Parsed JSON request data
        
    Returns:
        tuple: (is_valid, error_message, sanitized_query)
            - is_valid: True if query is valid
            - error_message: Error description or None if valid
            - sanitized_query: Cleaned query string
    """
    raw_query = data.get('query', '')
    query, query_valid, query_error = sanitize_query(raw_query)
    
    if not query_valid:
        return False, f"Invalid query: {query_error}", ""
    
    return True, None, query


def validate_bylaw_status_input(data: dict) -> Tuple[bool, Optional[str], str]:
    """
    Extract and validate bylaw status from request data.
    
    Args:
        data: Parsed JSON request data
        
    Returns:
        tuple: (is_valid, error_message, validated_status)
            - is_valid: True if status is valid
            - error_message: Error description or None if valid
            - validated_status: Normalized status string
    """
    raw_bylaw_status = data.get('bylaw_status', 'active')
    bylaw_status, status_valid, status_error = validate_bylaw_status(raw_bylaw_status)
    
    if not status_valid:
        return False, f"Invalid bylaw status: {status_error}", "active"
    
    return True, None, bylaw_status


def validate_autocomplete_query(data: dict) -> Tuple[bool, Optional[str], str]:
    """
    Extract and validate partial query for autocomplete with relaxed length requirements.
    
    Args:
        data: Parsed JSON request data
        
    Returns:
        tuple: (is_valid, error_message, sanitized_query)
            - is_valid: True if query is valid (or empty)
            - error_message: Error description or None if valid
            - sanitized_query: Cleaned query string
    """
    raw_partial_query = data.get('query', '')
    
    if not raw_partial_query:
        return True, None, ""
    
    # Use sanitize_query but handle length validation locally for autocomplete
    partial_query, query_valid, query_error = sanitize_query(raw_partial_query)
    
    # Only reject if there's an actual security issue, not just length
    if not query_valid and "potentially malicious content" in query_error:
        return False, f"Invalid query: {query_error}", ""
    
    return True, None, partial_query 