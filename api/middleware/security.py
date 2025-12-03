"""Security middleware for API authentication and authorization."""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict, Any, Callable
import logging
import time
from datetime import datetime, timedelta
import jwt
import bcrypt

from config.settings import settings

logger = logging.getLogger(__name__)

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for API key and JWT authentication."""
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/health",
        "/api/auth/login",
        "/api/auth/register",
    }
    
    def __init__(self, app, api_keys: Optional[Dict[str, Dict[str, Any]]] = None):
        """Initialize security middleware.
        
        Args:
            app: FastAPI application
            api_keys: Dictionary of API keys with metadata
                     Format: {"key": {"tenant_id": "...", "name": "...", "permissions": [...]}}
        """
        super().__init__(app)
        self.api_keys = api_keys or {}
        self.require_auth = settings.require_api_key
        
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request through security checks."""
        
        # Skip authentication for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Always try to extract authentication if provided (even if not required)
        authenticated = False
        if not self.require_auth:
            # Try to extract JWT token if provided
            try:
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    await self._validate_jwt_token(request, token)
                    authenticated = True
            except Exception as e:
                logger.debug(f"Optional JWT validation failed: {e}")

            # If not authenticated, set default tenant
            if not authenticated:
                tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
                request.state.tenant_id = tenant_id
                request.state.authenticated = False
            else:
                request.state.authenticated = True

            return await call_next(request)
        
        # Check for API key or JWT token
        try:
            # Try API Key first
            api_key = request.headers.get(settings.api_key_header)
            if api_key:
                await self._validate_api_key(request, api_key)
            else:
                # Try JWT token
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    await self._validate_jwt_token(request, token)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Missing authentication credentials",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            
            # Authentication successful
            request.state.authenticated = True
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    
    async def _validate_api_key(self, request: Request, api_key: str):
        """Validate API key and set tenant context."""
        if api_key not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        key_data = self.api_keys[api_key]
        request.state.tenant_id = key_data.get("tenant_id", settings.default_tenant_id)
        request.state.api_key_name = key_data.get("name", "unknown")
        request.state.permissions = key_data.get("permissions", [])
        request.state.auth_method = "api_key"
        
        logger.debug(f"API key authenticated: {key_data.get('name')} (tenant: {request.state.tenant_id})")
    
    async def _validate_jwt_token(self, request: Request, token: str):
        """Validate JWT token and set user context."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[ALGORITHM]
            )
            
            # Extract claims
            user_id: str = payload.get("sub")
            tenant_id: str = payload.get("tenant_id", settings.default_tenant_id)
            permissions: list = payload.get("permissions", [])
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Set request state
            request.state.user_id = user_id
            request.state.tenant_id = tenant_id
            request.state.permissions = permissions
            request.state.auth_method = "jwt"
            
            logger.debug(f"JWT authenticated: user={user_id}, tenant={tenant_id}")
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        """Initialize rate limiter.
        
        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per client
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, list] = {}
        self.enabled = settings.rate_limit_enabled
        
    async def dispatch(self, request: Request, call_next: Callable):
        """Check rate limits before processing request."""
        
        if not self.enabled:
            return await call_next(request)
        
        # Get client identifier (tenant_id or IP)
        client_id = getattr(request.state, "tenant_id", None) or request.client.host
        
        # Clean old requests (older than 1 minute)
        current_time = time.time()
        if client_id in self.request_counts:
            self.request_counts[client_id] = [
                req_time for req_time in self.request_counts[client_id]
                if current_time - req_time < 60
            ]
        else:
            self.request_counts[client_id] = []
        
        # Check rate limit
        if len(self.request_counts[client_id]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute."
            )
        
        # Record this request
        self.request_counts[client_id].append(current_time)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.request_counts[client_id])
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy - Allow Swagger UI and FastAPI docs
        # In production, tighten this policy and serve docs from same origin
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware to track all API calls."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Log request and response details."""
        
        if not settings.enable_audit_log:
            return await call_next(request)
        
        # Record request start time
        start_time = time.time()
        
        # Extract request details
        tenant_id = getattr(request.state, "tenant_id", "unknown")
        user_id = getattr(request.state, "user_id", "anonymous")
        auth_method = getattr(request.state, "auth_method", "none")
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            status_code = 500
            error = str(e)
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log audit entry
            logger.info(
                "API_AUDIT",
                extra={
                    "timestamp": datetime.utcnow().isoformat(),
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "auth_method": auth_method,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": request.client.host if request.client else "unknown",
                    "error": error,
                }
            )
        
        return response


# Utility functions for JWT tokens
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Token payload data
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

