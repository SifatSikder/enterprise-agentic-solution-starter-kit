"""Base exceptions and error hierarchy for enterprise agent framework."""

from typing import Dict, Any, Optional


class BaseAPIException(Exception):
    """Base exception for all API errors.
    
    Attributes:
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Machine-readable error code
        details: Additional error details
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize base exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# Agent-related exceptions

class AgentNotFoundException(BaseAPIException):
    """Agent not found in registry."""
    
    def __init__(self, agent_name: str):
        super().__init__(
            message=f"Agent '{agent_name}' not found",
            status_code=404,
            error_code="AGENT_NOT_FOUND",
            details={"agent_name": agent_name},
        )


class AgentExecutionException(BaseAPIException):
    """Error during agent execution."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="AGENT_EXECUTION_FAILED",
            details=details or {},
        )


class AgentInitializationException(BaseAPIException):
    """Error during agent initialization."""
    
    def __init__(self, agent_name: str, error: str):
        super().__init__(
            message=f"Agent '{agent_name}' initialization failed: {error}",
            status_code=500,
            error_code="AGENT_INITIALIZATION_FAILED",
            details={"agent_name": agent_name, "error": error},
        )


# Session-related exceptions

class SessionNotFoundException(BaseAPIException):
    """Session not found."""
    
    def __init__(self, session_id: str, tenant_id: str):
        super().__init__(
            message=f"Session '{session_id}' not found for tenant '{tenant_id}'",
            status_code=404,
            error_code="SESSION_NOT_FOUND",
            details={"session_id": session_id, "tenant_id": tenant_id},
        )


# Quota and rate limiting exceptions

class QuotaExceededException(BaseAPIException):
    """User or tenant quota exceeded."""
    
    def __init__(
        self,
        quota_type: str,
        limit: int,
        current: int,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"Quota exceeded for {quota_type}: {current}/{limit}",
            status_code=429,
            error_code="QUOTA_EXCEEDED",
            details={
                "quota_type": quota_type,
                "limit": limit,
                "current": current,
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        )


class RateLimitExceededException(BaseAPIException):
    """Rate limit exceeded."""
    
    def __init__(self, retry_after: int):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


# Authentication and authorization exceptions

class AuthenticationException(BaseAPIException):
    """Authentication failed."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_FAILED",
        )


class AuthorizationException(BaseAPIException):
    """Authorization failed - user doesn't have permission."""
    
    def __init__(self, resource: str, action: str):
        super().__init__(
            message=f"Not authorized to {action} {resource}",
            status_code=403,
            error_code="AUTHORIZATION_FAILED",
            details={"resource": resource, "action": action},
        )


# Validation exceptions

class ValidationException(BaseAPIException):
    """Request validation failed."""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation failed for '{field}': {message}",
            status_code=422,
            error_code="VALIDATION_FAILED",
            details={"field": field, "validation_error": message},
        )


# Tenant-related exceptions

class TenantNotFoundException(BaseAPIException):
    """Tenant not found."""
    
    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"Tenant '{tenant_id}' not found",
            status_code=404,
            error_code="TENANT_NOT_FOUND",
            details={"tenant_id": tenant_id},
        )


class TenantDisabledException(BaseAPIException):
    """Tenant is disabled."""
    
    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"Tenant '{tenant_id}' is disabled",
            status_code=403,
            error_code="TENANT_DISABLED",
            details={"tenant_id": tenant_id},
        )


# Configuration exceptions

class ConfigurationException(BaseAPIException):
    """Configuration error."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Configuration error: {message}",
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details=details,
        )


# External service exceptions

class ExternalServiceException(BaseAPIException):
    """External service error (Vertex AI, etc.)."""
    
    def __init__(self, service: str, error: str):
        super().__init__(
            message=f"External service '{service}' error: {error}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, "error": error},
        )

