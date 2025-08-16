from typing import Any, cast

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.logging import get_logger
from app.core.security import validate_access_token

logger = get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


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
