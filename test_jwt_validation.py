#!/usr/bin/env python3
"""Test JWT validation to debug signature verification issues."""

import asyncio
import sys
from jose import jwt as jose_jwt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_jwt_validation():
    """Test JWT validation with different scenarios."""
    
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    print(f"JWT Secret loaded: {jwt_secret[:20]}...{jwt_secret[-20:]}")
    print(f"JWT Secret length: {len(jwt_secret)}")
    
    # Test token - replace with your actual token
    test_token = input("Please paste your JWT token here: ").strip()
    
    if not test_token:
        print("No token provided")
        return
    
    print(f"\nToken length: {len(test_token)}")
    print(f"Token preview: {test_token[:50]}...")
    
    # Try to decode without verification
    try:
        unverified_payload = jose_jwt.decode(test_token, key="", options={"verify_signature": False, "verify_aud": False, "verify_exp": False})
        print("\nUnverified payload:")
        for key, value in unverified_payload.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"Failed to decode without verification: {e}")
        return
    
    # Try to verify with the secret
    print("\nAttempting signature verification...")
    try:
        verified_payload = jose_jwt.decode(
            test_token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
            }
        )
        print("✓ Signature verification successful!")
        print(f"User ID: {verified_payload.get('sub')}")
    except Exception as e:
        print(f"✗ Signature verification failed: {e}")
        
        # Try without audience check
        try:
            payload_no_aud = jose_jwt.decode(
                test_token,
                jwt_secret,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": False,
                }
            )
            print(f"\nToken validates without audience check. Audience in token: {unverified_payload.get('aud')}")
        except Exception as e2:
            print(f"Still fails without audience check: {e2}")

if __name__ == "__main__":
    asyncio.run(test_jwt_validation())