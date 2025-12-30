"""
CF-X Security Module
Key hashing, salt/pepper management
"""
import os
import hashlib
import hmac
from typing import Optional


class SecurityManager:
    """
    Manages API key hashing and verification
    Uses HMAC-SHA256 with salt + pepper for key hashing
    """
    
    def __init__(self):
        """
        Initialize security manager with salt and pepper from environment
        
        Raises:
            ValueError: If HASH_SALT or KEY_HASH_PEPPER are not set
        """
        # Salt: REQUIRED from environment (no default)
        self.salt = os.getenv("HASH_SALT")
        if not self.salt:
            raise ValueError(
                "HASH_SALT environment variable is required. "
                "Generate a strong random string: openssl rand -hex 32"
            )
        
        # Pepper: REQUIRED from environment (no default)
        self.pepper = os.getenv("KEY_HASH_PEPPER")
        if not self.pepper:
            raise ValueError(
                "KEY_HASH_PEPPER environment variable is required. "
                "Generate a strong random string: openssl rand -hex 32"
            )
        
        # Security check: salt and pepper must be different
        if self.salt == self.pepper:
            raise ValueError(
                "HASH_SALT and KEY_HASH_PEPPER must be different values"
            )
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key using HMAC-SHA256 with salt + pepper
        
        Args:
            api_key: Raw API key (should be UUID-like string)
        
        Returns:
            Hexadecimal hash string
        """
        # Combine salt + api_key + pepper
        message = f"{self.salt}:{api_key}:{self.pepper}"
        
        # Generate HMAC-SHA256 hash
        hash_obj = hmac.new(
            self.pepper.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        )
        
        return hash_obj.hexdigest()
    
    def verify_api_key(self, api_key: str, stored_hash: str) -> bool:
        """
        Verify an API key against stored hash
        
        Args:
            api_key: Raw API key to verify
            stored_hash: Stored hash from database
        
        Returns:
            True if key matches, False otherwise
        """
        computed_hash = self.hash_api_key(api_key)
        return hmac.compare_digest(computed_hash, stored_hash)
    
    def extract_bearer_token(self, authorization_header: Optional[str]) -> Optional[str]:
        """
        Extract API key from Authorization header (Bearer token)
        
        Args:
            authorization_header: Authorization header value (e.g., "Bearer sk-...")
        
        Returns:
            API key string if valid, None otherwise
        """
        if not authorization_header:
            return None
        
        # Check if it starts with "Bearer "
        if not authorization_header.startswith("Bearer "):
            return None
        
        # Extract token (remove "Bearer " prefix)
        token = authorization_header[7:].strip()
        
        # Basic validation: should not be empty
        if not token:
            return None
        
        return token


# Global security manager instance (singleton)
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager

