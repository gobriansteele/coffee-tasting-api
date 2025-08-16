#!/usr/bin/env python3
"""
JWT Generator for Local Development

This script generates JWT tokens for testing purposes using the Supabase JWT secret.
"""

import datetime
import sys
from pathlib import Path

# Add the app directory to the Python path so we can import settings
sys.path.append(str(Path(__file__).parent.parent))

try:
    import jwt
except ImportError:
    print("Error: PyJWT not installed. Install with: pip install pyjwt")
    sys.exit(1)

from app.core.config import settings


def generate_jwt_token(user_id: str, email: str, role: str = "authenticated", hours: int = 1) -> str:
    """
    Generate a JWT token for testing.

    Args:
        user_id: User UUID from auth.users table
        email: User email
        role: User role (authenticated, service_role, etc.)
        hours: Token expiration in hours

    Returns:
        JWT token string
    """
    if not settings.SUPABASE_JWT_SECRET:
        raise ValueError("SUPABASE_JWT_SECRET not configured in environment")

    # Set token expiration
    exp = datetime.datetime.utcnow() + datetime.timedelta(hours=hours)

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": exp,
        "aud": "authenticated",
        "iat": datetime.datetime.utcnow(),
        "iss": "supabase",
    }

    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    return token


def main():
    """Main function to generate and print JWT token."""
    if len(sys.argv) < 3:
        print("Usage: python generate_jwt.py <user_id> <email> [role] [hours]")
        print("Example: python generate_jwt.py abc123 user@example.com authenticated 1")
        sys.exit(1)

    user_id = sys.argv[1]
    email = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else "authenticated"
    hours_arg = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else "1"
    hours = int(hours_arg)

    try:
        token = generate_jwt_token(user_id, email, role, hours)
        print("Generated JWT Token:")
        print(token)
        print("\nUse this token in your Authorization header:")
        print(f"Authorization: Bearer {token}")

        # Decode and display token info for verification
        decoded = jwt.decode(
            token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )
        print("\nToken payload:")
        for key, value in decoded.items():
            if key == "exp":
                exp_time = datetime.datetime.fromtimestamp(value)
                print(f"  {key}: {value} ({exp_time})")
            else:
                print(f"  {key}: {value}")

    except Exception as e:
        print(f"Error generating token: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
