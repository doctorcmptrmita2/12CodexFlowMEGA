"""
CF-X Router - FastAPI Entry Point
Authoritative gateway for AI orchestration: auth, rate limit, routing, SSE
"""
import os
import uuid
import time
import logging
from typing import Optional, Tuple
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logger = logging.getLogger(__name__)

from cfx.config import get_config
from cfx.auth import get_auth_manager, AuthResult
from cfx.rate_limit import get_rate_limit_manager, RateLimitResult
from cfx.concurrency import get_concurrency_manager
from cfx.litellm_client import get_litellm_client, CircuitBreakerOpenError
from cfx.openai_compat import (
    transform_request_to_litellm,
    format_sse_event,
    format_sse_done,
    parse_sse_stream,
    create_error_response,
    validate_request
)
from cfx.logger import get_request_logger, RequestLog
from cfx.background import get_background_queue

# Initialize FastAPI app
app = FastAPI(
    title="CF-X Router",
    description="Plan-Code-Review AI Orchestration Gateway",
    version="0.1.0"
)

# CORS middleware (configure as needed)
# Get allowed origins from environment (comma-separated)
# Default: allow all (for development)
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "*")
cors_origins = cors_origins_env.split(",") if cors_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CFX-Stage"],
)

# Global config instance
config = get_config()
auth_manager = get_auth_manager()
rate_limit_manager = get_rate_limit_manager()
concurrency_manager = get_concurrency_manager()
litellm_client = get_litellm_client()
request_logger = get_request_logger()
background_queue = get_background_queue()


@app.on_event("startup")
async def startup_event():
    """Start background task queue on startup"""
    await background_queue.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background task queue on shutdown"""
    await background_queue.stop()


async def require_auth(authorization: Optional[str] = Header(None)) -> AuthResult:
    """
    Dependency: Require valid API key authentication
    
    Args:
        authorization: Authorization header
    
    Returns:
        AuthResult with user_id and api_key_id
    
    Raises:
        HTTPException 401 if authentication fails
    """
    auth_result = await auth_manager.validate_key_from_header(authorization)
    
    if not auth_result.authenticated:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": auth_result.error or "Invalid API key",
                    "type": "authentication_error",
                    "code": "invalid_api_key"
                }
            }
        )
    
    return auth_result


async def check_rate_limit(auth_result: AuthResult = Depends(require_auth)) -> Tuple[AuthResult, RateLimitResult]:
    """
    Dependency: Check rate limit after authentication
    
    Args:
        auth_result: Authentication result from require_auth
    
    Returns:
        Tuple of (AuthResult, RateLimitResult)
    
    Raises:
        HTTPException 429 if rate limit exceeded
    """
    if not auth_result.user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "User ID not found",
                    "type": "authentication_error",
                    "code": "missing_user_id"
                }
            }
        )
    
    # Check rate limit
    rate_limit_result = await rate_limit_manager.check_rate_limit(
        user_id=auth_result.user_id
    )
    
    if not rate_limit_result.allowed:
        # Calculate reset time for header
        reset_datetime = datetime.fromtimestamp(
            rate_limit_result.reset_timestamp,
            tz=timezone.utc
        )
        reset_iso = reset_datetime.isoformat()
        
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded"
                }
            },
            headers={
                "X-RateLimit-Limit": str(rate_limit_result.limit),
                "X-RateLimit-Remaining": str(rate_limit_result.remaining),
                "X-RateLimit-Reset": str(rate_limit_result.reset_timestamp),
                "Retry-After": str(rate_limit_result.reset_timestamp)
            }
        )
    
    return auth_result, rate_limit_result


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns 200 OK if service is healthy
    """
    return {"status": "ok", "service": "cfx-router"}


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    auth_and_rate_limit: Tuple[AuthResult, RateLimitResult] = Depends(check_rate_limit),
    x_cfx_stage: Optional[str] = Header(None, alias="X-CFX-Stage")
):
    """
    OpenAI-compatible chat completions endpoint
    
    Headers:
    - Authorization: Bearer <api_key> (required)
    - X-CFX-Stage: Optional stage override (plan|code|review|direct)
    
    Returns:
    - 400: Bad request (invalid request body)
    - 401: Unauthorized (if API key invalid)
    - 429: Rate limit exceeded
    - 503: Upstream unavailable (circuit breaker open)
    - 200/200 (streaming): Chat completion response
    - Headers: X-CFX-Request-Id, X-CFX-Stage, X-CFX-Model-Used, X-RateLimit-*
    """
    # Unpack dependencies
    auth_result, rate_limit_result = auth_and_rate_limit
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    
    # Parse request body
    try:
        request_body = await request.json()
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                "invalid_request_error",
                f"Invalid JSON: {str(e)}"
            )
        )
    
    # Validate request
    is_valid, error_msg = validate_request(request_body)
    if not is_valid:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                "invalid_request_error",
                error_msg or "Invalid request"
            )
        )
    
    # Determine stage (from header or default)
    stage = x_cfx_stage or config.get_default_stage()
    
    # Direct mode policy: explicitly disabled in MVP
    if stage == "direct":
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                "invalid_request_error",
                "Direct mode is disabled. Use X-CFX-Stage header with: plan, code, or review"
            )
        )
    
    # Get model for stage
    model_used = config.get_model_for_stage(stage)
    if not model_used:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                "invalid_request_error",
                f"Invalid stage: {stage}. Valid stages: plan, code, review"
            )
        )
    
    # Check if streaming
    is_streaming = request_body.get("stream", False)
    
    # Check concurrency limit for streaming
    if is_streaming:
        if not auth_result.user_id:
            return JSONResponse(
                status_code=401,
                content=create_error_response(
                    "authentication_error",
                    "User ID not found"
                )
            )
        
        # Try to acquire stream slot
        slot_acquired = await concurrency_manager.acquire_stream_slot(auth_result.user_id)
        if not slot_acquired:
            return JSONResponse(
                status_code=429,
                content=create_error_response(
                    "rate_limit_error",
                    "Streaming concurrency limit exceeded"
                ),
                headers={
                    "X-RateLimit-Limit": "2",  # Default cap
                    "X-RateLimit-Remaining": "0"
                }
            )
    
    # Prepare headers
    headers = {
        "X-CFX-Request-Id": request_id,
        "X-CFX-Stage": stage,
        "X-CFX-Model-Used": model_used,
        "X-RateLimit-Limit": str(rate_limit_result.limit),
        "X-RateLimit-Remaining": str(rate_limit_result.remaining),
        "X-RateLimit-Reset": str(rate_limit_result.reset_timestamp)
    }
    
    try:
        # Transform request for LiteLLM
        litellm_request = transform_request_to_litellm(
            request_body,
            model_override=model_used
        )
        
        # Call LiteLLM
        if is_streaming:
            # Streaming response
            try:
                stream = await litellm_client.chat_completions(**litellm_request)
                
                # Track streaming metrics
                stream_start_time = time.time()
                first_chunk_received = False
                
                async def stream_response():
                    nonlocal first_chunk_received
                    last_event_data = None
                    accumulated_content = ""  # Fallback: accumulate content for token estimation
                    try:
                        async for event in parse_sse_stream(stream):
                            # Check if client disconnected (handled via GeneratorExit in except)
                            
                            if event.get("done"):
                                yield format_sse_done()
                                
                                # Log streaming completion (best-effort)
                                if auth_result.user_id:
                                    latency_ms = int((time.time() - stream_start_time) * 1000)
                                    
                                    # Extract token usage from last event if available
                                    usage = last_event_data.get("usage", {}) if last_event_data else {}
                                    input_tokens = usage.get("prompt_tokens")
                                    output_tokens = usage.get("completion_tokens")
                                    total_tokens = usage.get("total_tokens")
                                    
                                    # Fallback: if token usage not in last event, try to estimate
                                    if not output_tokens and accumulated_content:
                                        # Rough estimation: ~4 characters per token (conservative)
                                        estimated_output_tokens = len(accumulated_content) // 4
                                        output_tokens = estimated_output_tokens
                                        total_tokens = (input_tokens or 0) + estimated_output_tokens
                                    
                                    # Fallback: if still no input_tokens, estimate from request
                                    if not input_tokens and request_body.get("messages"):
                                        # Estimate input tokens from messages
                                        total_chars = sum(
                                            len(str(msg.get("content", ""))) 
                                            for msg in request_body.get("messages", [])
                                        )
                                        estimated_input_tokens = total_chars // 4
                                        input_tokens = estimated_input_tokens
                                        if not total_tokens:
                                            total_tokens = estimated_input_tokens + (output_tokens or 0)
                                    
                                    cost_usd = None
                                    if input_tokens and output_tokens:
                                        cost_usd = request_logger.calculate_cost(
                                            model_used,
                                            input_tokens,
                                            output_tokens
                                        )
                                    
                                    log_entry = RequestLog(
                                        user_id=auth_result.user_id,
                                        api_key_id=auth_result.api_key_id,
                                        request_id=request_id,
                                        session_id=None,  # TODO: extract from request if available
                                        stage=stage,
                                        model=model_used,
                                        input_tokens=input_tokens,
                                        output_tokens=output_tokens,
                                        total_tokens=total_tokens,
                                        cost_usd=cost_usd,
                                        latency_ms=latency_ms,
                                        status="success"
                                    )
                                    await request_logger.log_request(log_entry)
                            else:
                                if not first_chunk_received:
                                    first_chunk_received = True
                                
                                # Store last event for token usage extraction
                                if "usage" in event:
                                    last_event_data = event
                                
                                # Fallback: accumulate content for token estimation
                                if "content" in event:
                                    content = event.get("content", "")
                                    if content:
                                        accumulated_content += content
                                
                                yield format_sse_event(event)
                    except GeneratorExit:
                        # Client disconnected - cleanup resources
                        logger.info(f"Client disconnected during stream: {request_id}")
                        # Note: LiteLLM upstream stream will be closed automatically
                        # when httpx.AsyncClient context exits (in litellm_client.py)
                        raise
                    finally:
                        # Release concurrency slot (always executed, even on disconnect)
                        if auth_result.user_id:
                            await concurrency_manager.release_stream_slot(auth_result.user_id)
                
                return StreamingResponse(
                    stream_response(),
                    media_type="text/event-stream",
                    headers=headers
                )
            except Exception as e:
                # Release slot on error
                if auth_result.user_id:
                    await concurrency_manager.release_stream_slot(auth_result.user_id)
                
                # Log error (best-effort)
                if auth_result.user_id:
                    latency_ms = int((time.time() - start_time) * 1000)
                    log_entry = RequestLog(
                        user_id=auth_result.user_id,
                        api_key_id=auth_result.api_key_id,
                        request_id=request_id,
                        session_id=None,
                        stage=stage,
                        model=model_used,
                        latency_ms=latency_ms,
                        status="error",
                        error_message=str(e)
                    )
                    await request_logger.log_request(log_entry)
                
                raise
        
        else:
            # Non-streaming response
            response_data = await litellm_client.chat_completions(**litellm_request)
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract token usage and calculate cost
            input_tokens, output_tokens, total_tokens = request_logger.extract_token_usage(response_data)
            cost_usd = None
            if input_tokens and output_tokens:
                cost_usd = request_logger.calculate_cost(
                    model_used,
                    input_tokens,
                    output_tokens
                )
            
            # Log request (best-effort, non-blocking)
            if auth_result.user_id:
                log_entry = RequestLog(
                    user_id=auth_result.user_id,
                    api_key_id=auth_result.api_key_id,
                    request_id=request_id,
                    session_id=None,  # TODO: extract from request if available
                    stage=stage,
                    model=model_used,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    status="success"
                )
                await request_logger.log_request(log_entry)
            
            return JSONResponse(
                content=response_data,
                headers=headers
            )
    
    except CircuitBreakerOpenError:
        # Circuit breaker is open - return 503 immediately
        if auth_result.user_id:
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = RequestLog(
                user_id=auth_result.user_id,
                api_key_id=auth_result.api_key_id,
                request_id=request_id,
                session_id=None,
                stage=stage,
                model=model_used,
                latency_ms=latency_ms,
                status="error",
                error_message="Circuit breaker is open"
            )
            await request_logger.log_request(log_entry)
        
        return JSONResponse(
            status_code=503,
            content=create_error_response(
                "service_unavailable_error",
                "Upstream service unavailable (circuit breaker open)"
            ),
            headers=headers
        )
    
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors from LiteLLM
        status_code = e.response.status_code if e.response else 500
        
        # Log error (best-effort)
        if auth_result.user_id:
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = RequestLog(
                user_id=auth_result.user_id,
                api_key_id=auth_result.api_key_id,
                request_id=request_id,
                session_id=None,
                stage=stage,
                model=model_used,
                latency_ms=latency_ms,
                status="error",
                error_message=f"Upstream error: {status_code}"
            )
            await request_logger.log_request(log_entry)
        
        if status_code == 503:
            # Circuit breaker open
            return JSONResponse(
                status_code=503,
                content=create_error_response(
                    "service_unavailable_error",
                    "Upstream service unavailable"
                ),
                headers=headers
            )
        
        # Other upstream errors
        error_detail = create_error_response(
            "upstream_error",
            f"Upstream error: {status_code}"
        )
        
        return JSONResponse(
            status_code=502,
            content=error_detail,
            headers=headers
        )
    
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        # Log error (best-effort)
        if auth_result.user_id:
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = RequestLog(
                user_id=auth_result.user_id,
                api_key_id=auth_result.api_key_id,
                request_id=request_id,
                session_id=None,
                stage=stage,
                model=model_used,
                latency_ms=latency_ms,
                status="error",
                error_message=f"Timeout or connection error: {str(e)}"
            )
            await request_logger.log_request(log_entry)
        
        # Timeout or connection error
        return JSONResponse(
            status_code=503,
            content=create_error_response(
                "service_unavailable_error",
                "Upstream service timeout or connection error"
            ),
            headers=headers
        )
    
    except Exception as e:
        # Log error (best-effort)
        if auth_result.user_id:
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = RequestLog(
                user_id=auth_result.user_id,
                api_key_id=auth_result.api_key_id,
                request_id=request_id,
                session_id=None,
                stage=stage,
                model=model_used,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e)
            )
            await request_logger.log_request(log_entry)
        
        # Unexpected error
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                "internal_error",
                f"Internal server error: {str(e)}"
            ),
            headers=headers
        )


if __name__ == "__main__":
    # Development server
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

