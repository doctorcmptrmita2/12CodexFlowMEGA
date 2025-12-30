"""
CF-X Request Logging Module
Best-effort async logging to Supabase request_logs table
"""
import os
import time
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import logging

from cfx.background import get_background_queue
from cfx.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class RequestLog:
    """Request log entry"""
    
    def __init__(
        self,
        user_id: UUID,
        request_id: str,
        stage: str,
        model: str,
        api_key_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_usd: Optional[float] = None,
        latency_ms: int = 0,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        self.user_id = user_id
        self.api_key_id = api_key_id
        self.request_id = request_id
        self.session_id = session_id
        self.stage = stage
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        self.status = status
        self.error_message = error_message


class RequestLogger:
    """
    Best-effort async request logger
    Logs to Supabase request_logs table without blocking requests
    """
    
    def __init__(self):
        """Initialize request logger"""
        self.background_queue = get_background_queue()
        # Supabase client will be initialized on first use
    
    async def log_request(self, log_entry: RequestLog) -> None:
        """
        Log request asynchronously (best-effort)
        
        Args:
            log_entry: RequestLog entry to save
        """
        # Enqueue logging task (non-blocking)
        await self.background_queue.enqueue(
            self._write_log,
            log_entry
        )
    
    async def _write_log(self, log_entry: RequestLog) -> None:
        """
        Write log to Supabase (internal, called by background queue)
        
        Args:
            log_entry: RequestLog entry to save
        """
        try:
            supabase = get_supabase_client()
            
            # Prepare log data for Supabase insert
            log_data = {
                "user_id": str(log_entry.user_id),
                "request_id": log_entry.request_id,
                "stage": log_entry.stage,
                "model": log_entry.model,
                "latency_ms": log_entry.latency_ms,
                "status": log_entry.status,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Add optional fields if present
            if log_entry.api_key_id:
                log_data["api_key_id"] = str(log_entry.api_key_id)
            
            if log_entry.session_id:
                log_data["session_id"] = log_entry.session_id
            
            if log_entry.input_tokens is not None:
                log_data["input_tokens"] = log_entry.input_tokens
            
            if log_entry.output_tokens is not None:
                log_data["output_tokens"] = log_entry.output_tokens
            
            if log_entry.total_tokens is not None:
                log_data["total_tokens"] = log_entry.total_tokens
            
            if log_entry.cost_usd is not None:
                log_data["cost_usd"] = float(log_entry.cost_usd)
            
            if log_entry.error_message:
                log_data["error_message"] = log_entry.error_message
            
            # Insert into Supabase
            response = supabase.table("request_logs").insert(log_data).execute()
            
            # Log success (debug level)
            logger.debug(
                f"Request log saved: {log_entry.request_id} | "
                f"User: {log_entry.user_id} | Status: {log_entry.status}"
            )
        
        except ValueError as e:
            # Supabase not configured - log to console as fallback
            logger.warning(
                f"Supabase not configured, logging to console: {log_entry.request_id} | "
                f"User: {log_entry.user_id} | Status: {log_entry.status}"
            )
        
        except Exception as e:
            # Log error but don't fail (best-effort)
            logger.error(
                f"Failed to write request log to Supabase: {e} | "
                f"Request ID: {log_entry.request_id}",
                exc_info=True
            )
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Optional[float]:
        """
        Calculate cost in USD based on model and token usage
        
        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
        
        Returns:
            Cost in USD, or None if model pricing unknown
        """
        # Model pricing (per 1K tokens)
        # TODO: Load from config or database
        pricing = {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "deepseek-chat": {"input": 0.000224, "output": 0.00032},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        }
        
        if model not in pricing:
            return None
        
        model_pricing = pricing[model]
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost
    
    def extract_token_usage(self, response_data: Dict[str, Any]) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Extract token usage from LiteLLM response
        
        Args:
            response_data: Response data from LiteLLM
        
        Returns:
            Tuple of (input_tokens, output_tokens, total_tokens)
        """
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        
        return input_tokens, output_tokens, total_tokens


# Global request logger instance (singleton)
_request_logger: Optional[RequestLogger] = None


def get_request_logger() -> RequestLogger:
    """Get global request logger instance"""
    global _request_logger
    if _request_logger is None:
        _request_logger = RequestLogger()
    return _request_logger

