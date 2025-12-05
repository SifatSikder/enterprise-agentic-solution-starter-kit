"""Custom exceptions for enterprise agent framework."""

from api.exceptions.base import (
    BaseAPIException,
    AgentNotFoundException,
    AgentExecutionException,
    AgentInitializationException,
    SessionNotFoundException,
    QuotaExceededException,
    RateLimitExceededException,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    TenantNotFoundException,
    TenantDisabledException,
    ConfigurationException,
    ExternalServiceException,
)

__all__ = [
    "BaseAPIException",
    "AgentNotFoundException",
    "AgentExecutionException",
    "AgentInitializationException",
    "SessionNotFoundException",
    "QuotaExceededException",
    "RateLimitExceededException",
    "AuthenticationException",
    "AuthorizationException",
    "ValidationException",
    "TenantNotFoundException",
    "TenantDisabledException",
    "ConfigurationException",
    "ExternalServiceException",
]

