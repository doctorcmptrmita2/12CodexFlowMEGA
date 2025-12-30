"""
CF-X LiteLLM Client Module
Upstream LiteLLM communication with timeout, retry, circuit breaker
"""
import os
import time
import asyncio
from typing import Optional, Dict, Any, AsyncIterator
from enum import Enum
import httpx
from datetime import datetime, timedelta


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if upstream recovered


class CircuitBreaker:
    """
    Simple circuit breaker for upstream failures
    Opens after threshold failures, closes after recovery period
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
    
    def record_success(self) -> None:
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # Require 2 successes to close
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def is_open(self) -> bool:
        """Check if circuit is open"""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return False  # Can try again
            return True  # Still open
        
        return False
    
    def can_proceed(self) -> bool:
        """Check if request can proceed"""
        return not self.is_open()


class LiteLLMClient:
    """
    Client for communicating with LiteLLM upstream
    Handles timeouts, retries, circuit breaker, streaming
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 120,
        connect_timeout: int = 10
    ):
        """
        Initialize LiteLLM client
        
        Args:
            base_url: LiteLLM base URL (defaults to http://litellm:4000)
            timeout: Request timeout in seconds
            connect_timeout: Connection timeout in seconds
        """
        self.base_url = base_url or os.getenv(
            "LITELLM_BASE_URL",
            "http://litellm:4000"
        )
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        
        # HTTP client with timeouts
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=timeout,
                write=timeout,
                pool=connect_timeout
            )
        )
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
    
    async def chat_completions(
        self,
        model: str,
        messages: list[Dict[str, Any]],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Send chat completion request to LiteLLM
        
        Args:
            model: Model name
            messages: Chat messages
            stream: Whether to stream response
            temperature: Temperature parameter
            max_tokens: Max tokens parameter
            **kwargs: Additional parameters
        
        Returns:
            Response (dict for non-streaming, async iterator for streaming)
        
        Raises:
            HTTPException 503 if circuit breaker is open
            HTTPException 502/503/504 for upstream errors (after retry)
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_proceed():
            # Use custom exception instead of HTTPStatusError with None values
            raise CircuitBreakerOpenError("Circuit breaker is open")
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        payload.update(kwargs)
        
        # Retry logic: max 1 retry for transient errors
        max_retries = 1
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if stream:
                    # Streaming request
                    async with self.client.stream(
                        "POST",
                        "/v1/chat/completions",
                        json=payload
                    ) as response:
                        response.raise_for_status()
                        self.circuit_breaker.record_success()
                        
                        # Return async iterator for SSE events
                        async def stream_generator():
                            async for line in response.aiter_lines():
                                if line:
                                    yield line
                        
                        return stream_generator()
                else:
                    # Non-streaming request
                    response = await self.client.post(
                        "/v1/chat/completions",
                        json=payload
                    )
                    response.raise_for_status()
                    self.circuit_breaker.record_success()
                    return response.json()
            
            except httpx.HTTPStatusError as e:
                last_error = e
                status_code = e.response.status_code if e.response else 0
                
                # Only retry transient 5xx errors
                if status_code in (502, 503, 504) and attempt < max_retries:
                    # Wait a bit before retry
                    await asyncio.sleep(0.5)
                    continue
                
                # Record failure
                self.circuit_breaker.record_failure()
                raise
            
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(0.5)
                    continue
                
                self.circuit_breaker.record_failure()
                raise
        
        # Should not reach here, but handle anyway
        if last_error:
            raise last_error
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()


# Global LiteLLM client instance (singleton)
_litellm_client: Optional["LiteLLMClient"] = None


def get_litellm_client() -> "LiteLLMClient":
    """Get global LiteLLM client instance"""
    global _litellm_client
    if _litellm_client is None:
        _litellm_client = LiteLLMClient()
    return _litellm_client

