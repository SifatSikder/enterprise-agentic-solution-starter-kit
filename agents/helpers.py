"""Helper utilities for the agents module.

Provides common utility functions used across the agent framework,
including session ID scoping for multi-tenancy.
"""
from typing import Tuple

# Separator used to scope session IDs by tenant
SESSION_ID_SEPARATOR = ":"


def scope_session_id(tenant_id: str, session_id: str) -> str:
    """Create a tenant-scoped session ID.
    
    Combines tenant_id and session_id into a single scoped identifier
    for multi-tenant session isolation.
    
    Args:
        tenant_id: Tenant identifier
        session_id: Session identifier
        
    Returns:
        Scoped session ID in format: "{tenant_id}:{session_id}"
        
    Example:
        >>> scope_session_id("acme-corp", "session123")
        'acme-corp:session123'
    """
    return f"{tenant_id}{SESSION_ID_SEPARATOR}{session_id}"


def parse_scoped_session_id(scoped_session_id: str) -> Tuple[str, str]:
    """Parse a scoped session ID into tenant_id and session_id.
    
    Args:
        scoped_session_id: Scoped session ID in format "{tenant_id}:{session_id}"
        
    Returns:
        Tuple of (tenant_id, session_id)
        
    Raises:
        ValueError: If the scoped_session_id format is invalid
        
    Example:
        >>> parse_scoped_session_id("acme-corp:session123")
        ('acme-corp', 'session123')
    """
    parts = scoped_session_id.split(SESSION_ID_SEPARATOR, 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid scoped session ID format. Expected 'tenant_id{SESSION_ID_SEPARATOR}session_id', "
            f"got: '{scoped_session_id}'"
        )
    return parts[0], parts[1]