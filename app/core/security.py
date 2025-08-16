from typing import Any

from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SupabaseJWTValidator:
    """JWT token validator for Supabase authentication following official recommendations."""

    def __init__(self) -> None:
        if not settings.SUPABASE_JWT_SECRET:
            raise ValueError("SUPABASE_JWT_SECRET must be configured")

    async def validate_token(self, token: str) -> dict[str, Any]:
        """
        Validate a Supabase JWT token following official recommendations.

        Args:
            token: The JWT token string

        Returns:
            The validated token payload

        Raises:
            ValueError: If token validation fails
        """
        try:
            # Validate using HS256 algorithm and "authenticated" audience as per Supabase docs
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET or "",
                algorithms=["HS256"],  # Supabase uses HS256, not RS256
                audience="authenticated",  # Supabase standard audience
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,  # Enable audience verification
                },
            )

            # Validate required Supabase claims
            required_claims = ["sub", "exp", "iat", "aud"]
            for claim in required_claims:
                if claim not in payload:
                    raise ValueError(f"Token missing required claim: {claim}")

            # Validate audience is "authenticated"
            if payload.get("aud") != "authenticated":
                raise ValueError(f"Invalid audience: {payload.get('aud')}")

            logger.debug(f"Successfully validated Supabase token for user: {payload.get('sub')}")
            return payload

        except JWTError as e:
            logger.warning(f"Supabase JWT validation failed: {e}")
            raise ValueError(f"Invalid token: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error validating Supabase token: {e}")
            raise ValueError(f"Token validation error: {e}") from e


# Global validator instance
jwt_validator = SupabaseJWTValidator()


async def validate_access_token(token: str) -> dict[str, Any]:
    """
    Validate a Supabase access token and return user information.

    Args:
        token: The JWT access token

    Returns:
        Dictionary containing user information

    Raises:
        ValueError: If token is invalid
    """
    payload = await jwt_validator.validate_token(token)

    return {
        "user_id": payload["sub"],
        "email": payload.get("email"),
        "role": payload.get("role", "authenticated"),
        "session_id": payload.get("session_id"),  # Supabase-specific claim
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
    }
