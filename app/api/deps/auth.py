import secrets
from typing import Any, cast

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from neo4j import AsyncSession

from app.api.deps.graph import get_graph_db
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import validate_access_token

logger = get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

# Cypher query for ensuring user exists with profile data
_MERGE_USER_QUERY = """
MERGE (u:CoffeeDrinker {id: $user_id})
ON CREATE SET u.email = $email,
              u.first_name = $first_name,
              u.last_name = $last_name,
              u.display_name = $display_name
"""


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, Any]:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials from the Authorization header

    Returns:
        Dictionary containing user information

    Raises:
        HTTPException: If authentication fails (401 Unauthorized)
    """
    if not credentials:
        logger.warning("Request missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_info = await validate_access_token(credentials.credentials)
        logger.debug(f"Authenticated user: {user_info['user_id']}")
        return user_info

    except ValueError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from e


async def get_current_user_id(current_user: dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Dependency to get just the current user ID.

    Args:
        current_user: Current user info from get_current_user dependency

    Returns:
        The user ID string
    """
    user_id = current_user.get("user_id")
    if not user_id or not isinstance(user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")
    return cast(str, user_id)


async def ensure_user_exists(
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_graph_db),
) -> str:
    """
    Ensures CoffeeDrinker node exists for authenticated user.

    Uses MERGE for idempotent creation - safe to call on every request.
    ON CREATE SET populates profile fields only when the node is first created.
    This dependency validates the JWT AND ensures the user node exists in Neo4j.

    Args:
        current_user: The authenticated user info from JWT
        session: Neo4j async session

    Returns:
        The user ID string
    """
    user_id = current_user.get("user_id")
    if not user_id or not isinstance(user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")

    try:
        await session.run(
            _MERGE_USER_QUERY,
            user_id=user_id,
            email=current_user.get("email"),
            first_name=current_user.get("first_name"),
            last_name=current_user.get("last_name"),
            display_name=current_user.get("display_name"),
        )
        logger.debug(f"Ensured CoffeeDrinker exists for user: {user_id}")
    except Exception as e:
        logger.error(f"Failed to ensure user exists in Neo4j: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize user session",
        ) from e
    return user_id


def require_user_access(resource_user_id: str, current_user_id: str) -> None:
    """
    Helper function to check if current user can access a resource.

    Args:
        resource_user_id: The user ID who owns the resource
        current_user_id: The current authenticated user ID

    Raises:
        HTTPException: If user doesn't have access (403 Forbidden)
    """
    if resource_user_id != current_user_id:
        logger.warning(
            f"Access denied: user {current_user_id} tried to access resource owned by {resource_user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own resources",
        )


# Optional dependency for endpoints that can work with or without auth
async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any] | None:
    """
    Optional authentication dependency.
    Returns user info if valid token provided, None otherwise.

    Args:
        credentials: HTTP Bearer credentials (optional)

    Returns:
        User info dict if authenticated, None if not
    """
    if not credentials:
        return None

    try:
        return await validate_access_token(credentials.credentials)
    except Exception:
        # Log the error but don't raise - this is optional auth
        logger.debug("Optional authentication failed, proceeding without auth")
        return None


async def get_current_user_role(current_user: dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Dependency to get the current user's application role.

    Args:
        current_user: Current user info from get_current_user dependency

    Returns:
        The user role string ('admin' or 'user')
    """
    return current_user.get("user_role", "user")


def require_role(allowed_roles: list[str]):
    """
    Factory function to create a dependency that requires specific roles.

    Args:
        allowed_roles: List of role names that are allowed access

    Returns:
        A dependency function that validates user role

    Example:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user_id: str = Depends(get_current_user_id),
            _: str = Depends(require_role(["admin"])),
        ):
            ...
    """

    async def role_checker(current_user: dict[str, Any] = Depends(get_current_user)) -> str:
        user_role = current_user.get("user_role", "user")
        if user_role not in allowed_roles:
            logger.warning(
                f"Access denied: user {current_user.get('user_id')} with role '{user_role}' "
                f"tried to access endpoint requiring {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This endpoint requires one of these roles: {allowed_roles}",
            )
        return user_role

    return role_checker


# Convenience dependency for admin-only endpoints
require_admin = require_role(["admin"])


async def require_api_key(x_api_key: str | None = Header(None)) -> str:
    """
    Dependency to validate x-api-key header for admin operations.

    This provides a simple static API key authentication mechanism for
    manual admin operations (e.g., embedding trueup via Postman).

    Args:
        x_api_key: The API key from x-api-key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing, invalid, or not configured
    """
    if not settings.ADMIN_API_KEY:
        logger.error("ADMIN_API_KEY is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured on this server",
        )

    if not x_api_key:
        logger.warning("Request missing x-api-key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="x-api-key header required",
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(x_api_key, settings.ADMIN_API_KEY):
        logger.warning("Invalid API key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    logger.debug("API key validated successfully")
    return x_api_key
