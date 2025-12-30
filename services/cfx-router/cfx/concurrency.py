"""
CF-X Concurrency Control Module
Per-user streaming concurrency cap enforcement
"""
import os
from typing import Dict, Set
from uuid import UUID
from collections import defaultdict
import asyncio


class ConcurrencyManager:
    """
    Manages per-user streaming concurrency limits
    Default cap: 2 concurrent streams per user
    """
    
    def __init__(self):
        """Initialize concurrency manager"""
        # Per-user active stream count
        self._active_streams: Dict[UUID, int] = defaultdict(int)
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Default concurrency cap (configurable per user/plan)
        self.default_cap = int(os.getenv("STREAMING_CONCURRENCY_CAP", "2"))
    
    async def acquire_stream_slot(self, user_id: UUID) -> bool:
        """
        Try to acquire a streaming slot for user
        
        Args:
            user_id: User UUID
        
        Returns:
            True if slot acquired, False if limit reached
        """
        async with self._lock:
            current_count = self._active_streams.get(user_id, 0)
            cap = await self.get_user_cap(user_id)
            
            if current_count >= cap:
                return False
            
            # Increment active count
            self._active_streams[user_id] = current_count + 1
            return True
    
    async def release_stream_slot(self, user_id: UUID) -> None:
        """
        Release a streaming slot for user
        
        Args:
            user_id: User UUID
        """
        async with self._lock:
            current_count = self._active_streams.get(user_id, 0)
            if current_count > 0:
                self._active_streams[user_id] = current_count - 1
            else:
                # Should not happen, but handle gracefully
                self._active_streams[user_id] = 0
    
    async def get_user_cap(self, user_id: UUID) -> int:
        """
        Get concurrency cap for user (can be customized per plan)
        
        Args:
            user_id: User UUID
        
        Returns:
            Concurrency cap (default: 2)
        """
        try:
            from cfx.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Try to get user plan from users table
            response = supabase.table("users").select(
                "streaming_concurrency_cap, plan"
            ).eq(
                "id", str(user_id)
            ).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                
                # If cap is set directly, use it
                if user_data.get("streaming_concurrency_cap"):
                    return int(user_data["streaming_concurrency_cap"])
                
                # Otherwise, map plan to cap
                plan = user_data.get("plan", "starter")
                plan_caps = {
                    "starter": 1,
                    "pro": 2,
                    "agency": 5
                }
                return plan_caps.get(plan, self.default_cap)
        
        except Exception:
            # Database error - use default
            pass
        
        # Default fallback
        return self.default_cap
    
    async def get_active_count(self, user_id: UUID) -> int:
        """
        Get current active stream count for user
        
        Args:
            user_id: User UUID
        
        Returns:
            Number of active streams
        """
        async with self._lock:
            return self._active_streams.get(user_id, 0)
    
    async def cleanup_user(self, user_id: UUID) -> None:
        """
        Cleanup all streams for user (e.g., on disconnect)
        
        Args:
            user_id: User UUID
        """
        async with self._lock:
            if user_id in self._active_streams:
                del self._active_streams[user_id]


# Global concurrency manager instance (singleton)
_concurrency_manager: Optional[ConcurrencyManager] = None


def get_concurrency_manager() -> ConcurrencyManager:
    """Get global concurrency manager instance"""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager()
    return _concurrency_manager

