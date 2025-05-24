"""
Input validation and security utilities for the Stouffville By-laws AI API.
"""

import html
import re
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
    """
    if not isinstance(text, str):
        text = str(text)

    # Remove newlines and control characters to prevent log injection
    sanitized = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')

    # HTML escape for additional safety
    return html.escape(sanitized)


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


def validate_bylaw_number(bylaw_number: Any) -> Tuple[str, bool, Optional[str]]:
    """
    Validate and normalize bylaw number format using business logic.

    Args:
        bylaw_number: Input bylaw number (any type, will be validated)

    Returns:
        tuple: (normalized_number, is_valid, error_message)
    """
    if not isinstance(bylaw_number, (str, int)):
        return "", False, "Bylaw number must be a string or integer"

    # Convert to string and normalize
    number_str = str(bylaw_number).strip()

    if not number_str:
        return "", False, "Bylaw number cannot be empty"

    # Basic format validation for Stouffville bylaws
    # Accept: alphanumeric characters and dashes only
    if not re.match(r'^[a-zA-Z0-9\-]+$', number_str):
        return "", False, "Invalid bylaw number format. Only alphanumeric characters and dashes allowed"

    return number_str, True, None


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
    
    if not isinstance(raw_partial_query, str):
        return False, "Query must be a string", ""
    
    # Basic sanitization (same as sanitize_query but without strict length restrictions)
    partial_query = unicodedata.normalize("NFKC", raw_partial_query.replace("\x00", "")).strip()
    
    # More permissive length validation for autocomplete
    if len(partial_query) > 500:
        return False, "Query too long for autocomplete", ""
    
    return True, None, partial_query 