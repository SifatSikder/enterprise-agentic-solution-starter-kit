"""API dependencies."""

from fastapi import Request, HTTPException

from api.dependencies.auth import (
    get_current_tenant,
    get_current_user,
    require_authentication,
    require_permissions,
    PermissionChecker,
    require_agent_read,
    require_agent_write,
    require_agent_execute,
    require_admin,
    get_tenant_from_header,
    validate_tenant_access,
)

from agents.manager import AgentManager


def get_agent_manager(request: Request) -> AgentManager:
    """Get agent manager from app state via dependency injection.

    Args:
        request: FastAPI request object

    Returns:
        AgentManager instance

    Raises:
        HTTPException: If agent manager is not initialized
    """
    agent_manager = getattr(request.app.state, "agent_manager", None)
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")
    return agent_manager


__all__ = [
    "get_current_tenant",
    "get_current_user",
    "require_authentication",
    "require_permissions",
    "PermissionChecker",
    "require_agent_read",
    "require_agent_write",
    "require_agent_execute",
    "require_admin",
    "get_tenant_from_header",
    "validate_tenant_access",
    "get_agent_manager",
]

