"""Authentication dependencies for FastAPI routes."""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_tenant(request: Request) -> str:
    """Get current tenant ID from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Tenant ID
    """
    tenant_id = getattr(request.state, "tenant_id", settings.default_tenant_id)
    return tenant_id


async def get_current_user(request: Request) -> Optional[str]:
    """Get current user ID from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID or None if not authenticated
    """
    return getattr(request.state, "user_id", None)


async def require_authentication(request: Request) -> bool:
    """Require that the request is authenticated.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if authenticated
        
    Raises:
        HTTPException: If not authenticated
    """
    authenticated = getattr(request.state, "authenticated", False)
    
    if not authenticated and settings.require_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return authenticated


async def require_permissions(
    request: Request,
    required_permissions: List[str]
) -> bool:
    """Require specific permissions.
    
    Args:
        request: FastAPI request object
        required_permissions: List of required permission strings
        
    Returns:
        True if user has all required permissions
        
    Raises:
        HTTPException: If user lacks required permissions
    """
    # Get user permissions from request state
    user_permissions = getattr(request.state, "permissions", [])
    
    # Check if user has all required permissions
    missing_permissions = [
        perm for perm in required_permissions
        if perm not in user_permissions
    ]
    
    if missing_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permissions: {', '.join(missing_permissions)}"
        )
    
    return True


class PermissionChecker:
    """Dependency class for checking permissions."""
    
    def __init__(self, required_permissions: List[str]):
        """Initialize permission checker.
        
        Args:
            required_permissions: List of required permission strings
        """
        self.required_permissions = required_permissions
    
    async def __call__(self, request: Request) -> bool:
        """Check if user has required permissions.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if user has all required permissions
            
        Raises:
            HTTPException: If user lacks required permissions
        """
        return await require_permissions(request, self.required_permissions)


# Common permission checkers
require_agent_read = PermissionChecker(["agent:read"])
require_agent_write = PermissionChecker(["agent:write"])
require_agent_execute = PermissionChecker(["agent:execute"])
require_admin = PermissionChecker(["admin"])


async def get_tenant_from_header(
    request: Request,
    x_tenant_id: Optional[str] = None
) -> str:
    """Get tenant ID from header or request state.
    
    Args:
        request: FastAPI request object
        x_tenant_id: Optional tenant ID from X-Tenant-ID header
        
    Returns:
        Tenant ID
    """
    # Priority: request state > header > default
    if hasattr(request.state, "tenant_id"):
        return request.state.tenant_id
    
    if x_tenant_id:
        return x_tenant_id
    
    return settings.default_tenant_id


async def validate_tenant_access(
    request: Request,
    tenant_id: str
) -> bool:
    """Validate that the authenticated user can access the specified tenant.
    
    Args:
        request: FastAPI request object
        tenant_id: Tenant ID to validate access for
        
    Returns:
        True if access is allowed
        
    Raises:
        HTTPException: If access is denied
    """
    # Get authenticated tenant from request state
    auth_tenant_id = getattr(request.state, "tenant_id", settings.default_tenant_id)
    
    # Check if tenant IDs match
    if auth_tenant_id != tenant_id:
        logger.warning(
            f"Tenant access denied: authenticated={auth_tenant_id}, requested={tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: tenant mismatch"
        )
    
    return True

