"""
CF-X Authentication Module
API key validation and user lookup
"""
import os
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from cfx.security import get_security_manager, SecurityManager
from cfx.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class AuthResult:
    """Result of authentication attempt"""
    
    def __init__(
        self,
        authenticated: bool,
        user_id: Optional[UUID] = None,
        api_key_id: Optional[UUID] = None,
        error: Optional[str] = None
    ):
        self.authenticated = authenticated
        self.user_id = user_id
        self.api_key_id = api_key_id
        self.error = error
    
    @classmethod
    def success(cls, user_id: UUID, api_key_id: UUID) -> "AuthResult":
        """Create successful authentication result"""
        return cls(
            authenticated=True,
            user_id=user_id,
            api_key_id=api_key_id
        )
    
    @classmethod
    def failure(cls, error: str) -> "AuthResult":
        """Create failed authentication result"""
        return cls(
            authenticated=False,
            error=error
        )


class AuthManager:
    """
    Manages API key authentication
    Validates keys against Supabase database (stub for now)
    """
    
    def __init__(self):
        """Initialize auth manager"""
        self.security = get_security_manager()
        # Supabase client will be initialized on first use
        self._supabase_client = None
    
    async def authenticate(self, api_key: str) -> AuthResult:
        """
        Authenticate an API key
        
        Args:
            api_key: Raw API key from Authorization header
        
        Returns:
            AuthResult with authentication status and user info
        """
        # Extract key if it's a Bearer token
        if api_key.startswith("Bearer "):
            api_key = api_key[7:].strip()
        
        if not api_key:
            return AuthResult.failure("Missing API key")
        
        # Hash the key for database lookup
        key_hash = self.security.hash_api_key(api_key)
        
        try:
            # Get Supabase client
            supabase = get_supabase_client()
            
            # Query api_keys table: WHERE key_hash = ? AND status = 'active'
            response = supabase.table("api_keys").select(
                "id, user_id, status"
            ).eq(
                "key_hash", key_hash
            ).eq(
                "status", "active"
            ).limit(1).execute()
            
            # Check if key found
            if not response.data or len(response.data) == 0:
                return AuthResult.failure("Invalid API key")
            
            # Extract user_id and api_key_id
            key_record = response.data[0]
            user_id = UUID(key_record["user_id"])
            api_key_id = UUID(key_record["id"])
            
            return AuthResult.success(user_id, api_key_id)
        
        except ValueError as e:
            # Supabase not configured
            logger.error(f"Supabase not configured: {e}")
            return AuthResult.failure("Authentication service unavailable")
        
        except Exception as e:
            # Database error or other exception
            logger.error(f"Authentication error: {e}", exc_info=True)
            return AuthResult.failure("Authentication service error")
    
    async def validate_key_from_header(
        self,
        authorization_header: Optional[str]
    ) -> AuthResult:
        """
        Validate API key from Authorization header
        
        Args:
            authorization_header: Authorization header value
        
        Returns:
            AuthResult with authentication status
        """
        # Extract token from header
        api_key = self.security.extract_bearer_token(authorization_header)
        
        if not api_key:
            return AuthResult.failure("Missing or invalid Authorization header")
        
        # Authenticate
        return await self.authenticate(api_key)
    
    def is_supabase_configured(self) -> bool:
        """
        Check if Supabase is configured
        
        Returns:
            True if Supabase credentials are available
        """
        try:
            get_supabase_client()
            return True
        except ValueError:
            return False


# Global auth manager instance (singleton)
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get global auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager

