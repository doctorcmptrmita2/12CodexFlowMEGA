"""
CF-X OpenAI Compatibility Module
Request/response transformation for OpenAI-compatible API
"""
import json
from typing import Dict, Any, Optional, AsyncIterator
from uuid import UUID


def transform_request_to_litellm(
    request_body: Dict[str, Any],
    model_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transform OpenAI-compatible request to LiteLLM format
    
    Args:
        request_body: Original request body from client
        model_override: Model to use (overrides client's model parameter)
    
    Returns:
        Transformed request body for LiteLLM
    """
    # Start with original request
    transformed = request_body.copy()
    
    # Override model if provided (CF-X routing)
    if model_override:
        transformed["model"] = model_override
    
    # Ensure required fields
    if "messages" not in transformed:
        raise ValueError("Missing 'messages' field in request")
    
    # Stream defaults to False if not specified
    if "stream" not in transformed:
        transformed["stream"] = False
    
    return transformed


def format_sse_event(data: Dict[str, Any]) -> str:
    """
    Format data as SSE event
    
    Args:
        data: Data to format
    
    Returns:
        SSE-formatted string: "data: {...}\n\n"
    """
    json_str = json.dumps(data)
    return f"data: {json_str}\n\n"


def format_sse_done() -> str:
    """
    Format SSE done event
    
    Returns:
        SSE done string: "data: [DONE]\n\n"
    """
    return "data: [DONE]\n\n"


async def parse_sse_stream(
    stream: AsyncIterator[str]
) -> AsyncIterator[Dict[str, Any]]:
    """
    Parse SSE stream from LiteLLM into JSON objects
    
    Args:
        stream: Async iterator of SSE lines
    
    Yields:
        Parsed JSON objects from SSE events
    """
    buffer = ""
    
    async for line in stream:
        if not line:
            continue
        
        # SSE format: "data: {...}\n"
        if line.startswith("data: "):
            data_str = line[6:].strip()  # Remove "data: " prefix
            
            # Check for [DONE]
            if data_str == "[DONE]":
                yield {"done": True}
                continue
            
            # Try to parse JSON
            try:
                data = json.loads(data_str)
                yield data
            except json.JSONDecodeError:
                # Skip malformed JSON
                continue
        
        # Handle multi-line SSE (shouldn't happen, but handle gracefully)
        elif line.startswith(":"):
            # SSE comment, skip
            continue


def create_error_response(
    error_type: str,
    message: str,
    code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create OpenAI-compatible error response
    
    Args:
        error_type: Error type (e.g., "invalid_request_error")
        message: Error message
        code: Optional error code
    
    Returns:
        Error response dict
    """
    error = {
        "message": message,
        "type": error_type
    }
    
    if code:
        error["code"] = code
    
    return {"error": error}


def extract_model_from_request(request_body: Dict[str, Any]) -> Optional[str]:
    """
    Extract model from request (for direct mode, if enabled)
    
    Args:
        request_body: Request body
    
    Returns:
        Model name if present, None otherwise
    """
    return request_body.get("model")


def validate_request(request_body: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate OpenAI-compatible request
    
    Args:
        request_body: Request body to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if "messages" not in request_body:
        return False, "Missing 'messages' field"
    
    if not isinstance(request_body["messages"], list):
        return False, "'messages' must be a list"
    
    if len(request_body["messages"]) == 0:
        return False, "'messages' cannot be empty"
    
    # Validate message format
    for msg in request_body["messages"]:
        if not isinstance(msg, dict):
            return False, "Each message must be a dict"
        
        if "role" not in msg or "content" not in msg:
            return False, "Each message must have 'role' and 'content' fields"
    
    return True, None

