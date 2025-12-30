#!/usr/bin/env python3
"""
CF-X API Key Generator
Creates a new API key and stores it in Supabase with proper hashing

Usage:
    python scripts/create-api-key.py --user-id <UUID> --supabase-url <URL> --supabase-key <SERVICE_ROLE_KEY>
"""

import argparse
import uuid
import sys
import os
from supabase import create_client, Client

# Add router path to import security module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'cfx-router'))

from cfx.security import SecurityManager


def generate_api_key() -> str:
    """Generate a new API key (UUID format)"""
    return f"cfx_{uuid.uuid4().hex}"


def hash_api_key(api_key: str, salt: str, pepper: str) -> str:
    """Hash API key using SecurityManager"""
    # Temporarily set env vars for SecurityManager
    os.environ["HASH_SALT"] = salt
    os.environ["KEY_HASH_PEPPER"] = pepper
    
    security = SecurityManager()
    return security.hash_api_key(api_key)


def create_api_key_in_supabase(
    supabase: Client,
    user_id: str,
    key_hash: str
) -> str:
    """Insert API key into Supabase and return the key ID"""
    response = supabase.table("api_keys").insert({
        "user_id": user_id,
        "key_hash": key_hash,
        "status": "active"
    }).execute()
    
    if not response.data:
        raise Exception("Failed to create API key in Supabase")
    
    return response.data[0]["id"]


def main():
    parser = argparse.ArgumentParser(description="Create a new CF-X API key")
    parser.add_argument("--user-id", required=True, help="User UUID from Supabase Auth")
    parser.add_argument("--supabase-url", required=True, help="Supabase project URL")
    parser.add_argument("--supabase-key", required=True, help="Supabase service role key")
    parser.add_argument("--hash-salt", required=True, help="HASH_SALT from router environment")
    parser.add_argument("--hash-pepper", required=True, help="KEY_HASH_PEPPER from router environment")
    
    args = parser.parse_args()
    
    # Generate API key
    api_key = generate_api_key()
    print(f"🔑 Generated API Key: {api_key}")
    print("⚠️  SAVE THIS KEY - It won't be shown again!")
    print("")
    
    # Hash the key
    key_hash = hash_api_key(api_key, args.hash_salt, args.hash_pepper)
    print(f"✓ Key hashed")
    
    # Connect to Supabase
    supabase = create_client(args.supabase_url, args.supabase_key)
    
    # Create API key in database
    try:
        key_id = create_api_key_in_supabase(supabase, args.user_id, key_hash)
        print(f"✓ API key created in Supabase (ID: {key_id})")
        print("")
        print("=" * 60)
        print("API KEY CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"API Key: {api_key}")
        print(f"Key ID: {key_id}")
        print(f"User ID: {args.user_id}")
        print("=" * 60)
        print("")
        print("Use this API key in Authorization header:")
        print(f"  Authorization: Bearer {api_key}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

