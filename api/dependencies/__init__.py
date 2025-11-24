"""API dependencies."""

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
]

