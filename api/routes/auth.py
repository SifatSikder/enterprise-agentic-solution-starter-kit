"""Authentication routes for user login and token management."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import timedelta
import logging

from api.middleware.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from api.dependencies.auth import get_current_user, get_current_tenant
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (optional)")


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    tenant_id: str = Field(..., description="Tenant ID")


class UserInfo(BaseModel):
    """User information model."""
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    tenant_id: str = Field(..., description="Tenant ID")
    permissions: List[str] = Field(default_factory=list, description="User permissions")


class APIKeyRequest(BaseModel):
    """API key creation request."""
    name: str = Field(..., description="API key name/description")
    tenant_id: str = Field(..., description="Tenant ID")
    permissions: List[str] = Field(default_factory=list, description="API key permissions")


class APIKeyResponse(BaseModel):
    """API key response model."""
    api_key: str = Field(..., description="Generated API key")
    name: str = Field(..., description="API key name")
    tenant_id: str = Field(..., description="Tenant ID")
    permissions: List[str] = Field(..., description="API key permissions")
    created_at: str = Field(..., description="Creation timestamp")


# In-memory user store (replace with database in production)
# Format: {username: {password_hash, tenant_id, permissions}}
# Pre-computed password hashes using bcrypt
DEMO_USERS = {
    "admin": {
        "password_hash": "$2b$12$p3G24oXWibxgY72W2OvtXuuwyMwduhWEDRb0w89oNB6AC7texMxRW",  # admin123
        "tenant_id": "default",
        "permissions": ["admin", "agent:read", "agent:write", "agent:execute"],
    },
    "user1": {
        "password_hash": "$2b$12$eMiXPp8MW//Oe4omjhehjOgQgiMXieXOLefuEVs3vJrtZhkhyYihS",  # user123
        "tenant_id": "tenant1",
        "permissions": ["agent:read", "agent:execute"],
    },
    "user2": {
        "password_hash": "$2b$12$eMiXPp8MW//Oe4omjhehjOgQgiMXieXOLefuEVs3vJrtZhkhyYihS",  # user123
        "tenant_id": "tenant2",
        "permissions": ["agent:read", "agent:execute"],
    },
}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token.
    
    Args:
        request: Login credentials
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Validate credentials
    user = DEMO_USERS.get(request.username)
    
    if not user or not verify_password(request.password, user["password_hash"]):
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Use provided tenant_id or user's default tenant
    tenant_id = request.tenant_id or user["tenant_id"]
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": request.username,
            "tenant_id": tenant_id,
            "permissions": user["permissions"],
        },
        expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {request.username} (tenant: {tenant_id})")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        tenant_id=tenant_id,
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    request: Request,
    user_id: Optional[str] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get current authenticated user information.
    
    Args:
        request: FastAPI request
        user_id: Current user ID from dependency
        tenant_id: Current tenant ID from dependency
        
    Returns:
        User information
        
    Raises:
        HTTPException: If not authenticated
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Get user permissions from request state
    permissions = getattr(request.state, "permissions", [])
    
    return UserInfo(
        user_id=user_id,
        username=user_id,  # In this demo, user_id is the username
        tenant_id=tenant_id,
        permissions=permissions,
    )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    user_id: Optional[str] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Refresh JWT access token.
    
    Args:
        request: FastAPI request
        user_id: Current user ID
        tenant_id: Current tenant ID
        
    Returns:
        New JWT access token
        
    Raises:
        HTTPException: If not authenticated
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Get user permissions
    permissions = getattr(request.state, "permissions", [])
    
    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user_id,
            "tenant_id": tenant_id,
            "permissions": permissions,
        },
        expires_delta=access_token_expires
    )
    
    logger.info(f"Token refreshed for user: {user_id}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        tenant_id=tenant_id,
    )


@router.post("/logout")
async def logout(user_id: Optional[str] = Depends(get_current_user)):
    """Logout user (client should discard token).
    
    Args:
        user_id: Current user ID
        
    Returns:
        Success message
    """
    logger.info(f"User logged out: {user_id or 'anonymous'}")
    
    return {
        "message": "Successfully logged out",
        "detail": "Please discard your access token"
    }


@router.get("/demo-credentials")
async def get_demo_credentials():
    """Get demo credentials for testing (development only).
    
    Returns:
        Demo user credentials
    """
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not available in production"
        )
    
    return {
        "message": "Demo credentials for testing",
        "users": [
            {
                "username": "admin",
                "password": "admin123",
                "tenant_id": "default",
                "permissions": ["admin", "agent:read", "agent:write", "agent:execute"],
            },
            {
                "username": "user1",
                "password": "user123",
                "tenant_id": "tenant1",
                "permissions": ["agent:read", "agent:execute"],
            },
            {
                "username": "user2",
                "password": "user123",
                "tenant_id": "tenant2",
                "permissions": ["agent:read", "agent:execute"],
            },
        ],
        "note": "Use POST /api/auth/login to get a JWT token"
    }

