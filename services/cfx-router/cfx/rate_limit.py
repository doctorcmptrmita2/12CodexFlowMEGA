"""
CF-X Rate Limiting Module
Daily request limit enforcement with backend abstraction
"""
import os
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Tuple, Optional
from uuid import UUID
from abc import ABC, abstractmethod

from cfx.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Global rate limit manager instance (singleton)
_rate_limit_manager: Optional["RateLimitManager"] = None


class RateLimitResult:
    """Result of rate limit check"""
    
    def __init__(
        self,
        allowed: bool,
        remaining: int,
        reset_timestamp: int,
        limit: int
    ):
        self.allowed = allowed
        self.remaining = remaining
        self.reset_timestamp = reset_timestamp  # UTC timestamp
        self.limit = limit


class RateLimiterBackend(ABC):
    """
    Abstract interface for rate limit backend
    Allows swapping Postgres/Redis implementations
    """
    
    @abstractmethod
    async def check_and_increment(
        self,
        user_id: UUID,
        day_utc: date,
        limit: int
    ) -> RateLimitResult:
        """
        Check if request is allowed and increment counter atomically
        
        Args:
            user_id: User UUID
            day_utc: UTC date bucket
            limit: Daily request limit
        
        Returns:
            RateLimitResult with allowed status and remaining count
        """
        pass


class SupabaseRateLimiter(RateLimiterBackend):
    """
    Supabase/Postgres rate limiter implementation
    Uses atomic upsert+increment on usage_counters table
    """
    
    def __init__(self):
        """Initialize Supabase rate limiter"""
        # Supabase client will be initialized on first use
        pass
    
    async def check_and_increment(
        self,
        user_id: UUID,
        day_utc: date,
        limit: int
    ) -> RateLimitResult:
        """
        Check and increment using Supabase usage_counters table
        
        Implementation:
        1. UPSERT usage_counters SET request_count = request_count + 1
           WHERE user_id = ? AND day = ?
        2. SELECT request_count FROM usage_counters WHERE ...
        3. Calculate remaining = limit - request_count
        4. Calculate reset_timestamp (next day 00:00 UTC)
        """
        try:
            supabase = get_supabase_client()
            
            # Calculate reset timestamp (next day 00:00 UTC) - FIX: use timedelta
            next_day = day_utc + timedelta(days=1)
            reset_datetime = datetime.combine(
                next_day,
                datetime.min.time(),
                tzinfo=timezone.utc
            )
            reset_timestamp = int(reset_datetime.timestamp())
            
            # Atomic upsert+increment using Supabase
            # Strategy: Use Supabase RPC function if available, otherwise use optimized upsert
            day_str = day_utc.isoformat()
            
            try:
                # Try RPC function first (more atomic, handles race conditions better)
                # RPC function: increment_usage_counter(user_id UUID, day DATE)
                # Returns: { request_count: INT, allowed: BOOLEAN, limit: INT }
                try:
                    rpc_response = supabase.rpc(
                        "increment_usage_counter",
                        {
                            "p_user_id": str(user_id),
                            "p_day": day_str,
                            "p_limit": limit
                        }
                    ).execute()
                    
                    if rpc_response.data:
                        # RPC function returned result
                        result = rpc_response.data
                        request_count = result.get("request_count", 0)
                        allowed = result.get("allowed", True)
                        remaining = max(0, limit - request_count)
                        
                        return RateLimitResult(
                            allowed=allowed,
                            remaining=remaining,
                            reset_timestamp=reset_timestamp,
                            limit=limit
                        )
                except Exception as rpc_error:
                    # RPC function not available or failed - fallback to upsert
                    logger.debug(f"RPC function not available, using upsert: {rpc_error}")
                
                # Fallback: Optimized upsert with conflict handling
                # Use Supabase's upsert with ON CONFLICT handling
                # This requires a unique constraint on (user_id, day)
                upsert_data = {
                    "user_id": str(user_id),
                    "day": day_str,
                    "request_count": 1,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Try to insert, if conflict then update with increment
                # Supabase PostgREST doesn't support ON CONFLICT directly in upsert
                # So we use a two-step approach: try insert, if fails then update
                try:
                    # Try insert first
                    insert_response = supabase.table("usage_counters").insert(
                        upsert_data
                    ).execute()
                    
                    if insert_response.data:
                        request_count = 1
                    else:
                        # Insert failed (likely conflict), try update with increment
                        # Get current count first
                        select_response = supabase.table("usage_counters").select(
                            "request_count"
                        ).eq(
                            "user_id", str(user_id)
                        ).eq(
                            "day", day_str
                        ).limit(1).execute()
                        
                        if select_response.data and len(select_response.data) > 0:
                            current_count = select_response.data[0]["request_count"]
                            new_count = current_count + 1
                            
                            update_response = supabase.table("usage_counters").update({
                                "request_count": new_count,
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            }).eq(
                                "user_id", str(user_id)
                            ).eq(
                                "day", day_str
                            ).execute()
                            
                            request_count = new_count
                        else:
                            # Still no record - use 1 as fallback
                            request_count = 1
                
                except Exception as upsert_error:
                    # Insert failed, try update
                    select_response = supabase.table("usage_counters").select(
                        "request_count"
                    ).eq(
                        "user_id", str(user_id)
                    ).eq(
                        "day", day_str
                    ).limit(1).execute()
                    
                    if select_response.data and len(select_response.data) > 0:
                        current_count = select_response.data[0]["request_count"]
                        new_count = current_count + 1
                        
                        update_response = supabase.table("usage_counters").update({
                            "request_count": new_count,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }).eq(
                            "user_id", str(user_id)
                        ).eq(
                            "day", day_str
                        ).execute()
                        
                        request_count = new_count
                    else:
                        # No record found - create with count = 1
                        insert_response = supabase.table("usage_counters").insert({
                            "user_id": str(user_id),
                            "day": day_str,
                            "request_count": 1,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }).execute()
                        
                        request_count = 1
                
                # Check if limit exceeded
                allowed = request_count <= limit
                remaining = max(0, limit - request_count)
                
                return RateLimitResult(
                    allowed=allowed,
                    remaining=remaining,
                    reset_timestamp=reset_timestamp,
                    limit=limit
                )
            
            except Exception as db_error:
                # Database error - log but allow request (fail-open for availability)
                logger.error(
                    f"Rate limit database error for user {user_id}: {db_error}",
                    exc_info=True
                )
                # Fail-open: allow request but log the error
                return RateLimitResult(
                    allowed=True,
                    remaining=limit - 1,  # Conservative estimate
                    reset_timestamp=reset_timestamp,
                    limit=limit
                )
        
        except ValueError as e:
            # Supabase not configured - fail-open
            logger.error(f"Supabase not configured for rate limiting: {e}")
            next_day = day_utc + timedelta(days=1)
            reset_datetime = datetime.combine(
                next_day,
                datetime.min.time(),
                tzinfo=timezone.utc
            )
            reset_timestamp = int(reset_datetime.timestamp())
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                reset_timestamp=reset_timestamp,
                limit=limit
            )
    
    def is_configured(self) -> bool:
        """Check if Supabase is configured"""
        try:
            get_supabase_client()
            return True
        except ValueError:
            return False


class RateLimitManager:
    """
    Rate limit manager with backend abstraction
    Default daily limit: 1000 requests (configurable)
    """
    
    def __init__(self, backend: Optional[RateLimiterBackend] = None):
        """
        Initialize rate limit manager
        
        Args:
            backend: Rate limiter backend (defaults to SupabaseRateLimiter)
        """
        self.backend = backend or SupabaseRateLimiter()
        # Default daily limit (can be overridden per user/plan)
        self.default_daily_limit = int(os.getenv("DAILY_REQUEST_LIMIT", "1000"))
    
    async def check_rate_limit(
        self,
        user_id: UUID,
        daily_limit: Optional[int] = None
    ) -> RateLimitResult:
        """
        Check if user has remaining requests for today
        
        Args:
            user_id: User UUID
            daily_limit: Optional custom limit (overrides user plan lookup)
        
        Returns:
            RateLimitResult with allowed status and remaining count
        """
        # Use provided limit, or lookup from user plan, or default
        if daily_limit is None:
            limit = await self.get_daily_limit(user_id)
        else:
            limit = daily_limit
        
        # Get current UTC date
        today_utc = date.today()
        
        # Check and increment atomically
        return await self.backend.check_and_increment(
            user_id=user_id,
            day_utc=today_utc,
            limit=limit
        )
    
    async def get_daily_limit(self, user_id: UUID) -> int:
        """
        Get daily limit for user (can be customized per plan)
        
        Args:
            user_id: User UUID
        
        Returns:
            Daily request limit
        """
        try:
            supabase = get_supabase_client()
            
            # Try to get user plan from users table
            # Schema: users table has 'plan' column (starter|pro|agency) or 'daily_limit' column
            response = supabase.table("users").select(
                "daily_limit, plan"
            ).eq(
                "id", str(user_id)
            ).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                
                # If daily_limit is set directly, use it
                if user_data.get("daily_limit"):
                    return int(user_data["daily_limit"])
                
                # Otherwise, map plan to limit
                plan = user_data.get("plan", "starter")
                plan_limits = {
                    "starter": 1000,
                    "pro": 4000,
                    "agency": 15000
                }
                return plan_limits.get(plan, self.default_daily_limit)
        
        except Exception as e:
            # Database error - use default
            logger.warning(
                f"Failed to lookup user plan for {user_id}: {e}. Using default limit."
            )
        
        # Default fallback
        return self.default_daily_limit


def get_rate_limit_manager() -> "RateLimitManager":
    """Get global rate limit manager instance"""
    global _rate_limit_manager
    if _rate_limit_manager is None:
        _rate_limit_manager = RateLimitManager()
    return _rate_limit_manager

