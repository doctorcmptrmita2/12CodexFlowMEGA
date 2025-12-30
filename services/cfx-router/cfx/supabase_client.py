"""
CF-X Supabase Client Module
Singleton Supabase client for router (uses service role key)
"""
import os
from typing import Optional
from supabase import create_client, Client


class SupabaseClientManager:
    """
    Manages Supabase client instance (singleton)
    Uses service role key for privileged operations
    """
    
    def __init__(self):
        """Initialize Supabase client manager"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self._client: Optional[Client] = None
    
    def get_client(self) -> Client:
        """
        Get Supabase client instance (singleton)
        
        Returns:
            Supabase client instance
        
        Raises:
            ValueError: If Supabase credentials are not configured
        """
        if not self.supabase_url or not self.supabase_service_role_key:
            raise ValueError(
                "Supabase credentials not configured: "
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        
        if self._client is None:
            self._client = create_client(
                self.supabase_url,
                self.supabase_service_role_key
            )
        
        return self._client
    
    def is_configured(self) -> bool:
        """
        Check if Supabase is configured
        
        Returns:
            True if credentials are available
        """
        return bool(self.supabase_url and self.supabase_service_role_key)


# Global Supabase client manager instance (singleton)
_supabase_manager: Optional[SupabaseClientManager] = None


def get_supabase_client() -> Client:
    """
    Get global Supabase client instance
    
    Returns:
        Supabase client instance
    
    Raises:
        ValueError: If Supabase credentials are not configured
    """
    global _supabase_manager
    if _supabase_manager is None:
        _supabase_manager = SupabaseClientManager()
    return _supabase_manager.get_client()

