"""Agent management endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from api.models.requests import ChatRequest, ChatResponse
from api.models.agent import AgentInfo
from api.dependencies.auth import (
    get_current_tenant,
    get_current_user,
    require_agent_read,
    require_agent_execute,
    require_authentication,
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def get_agent_manager(request: Request):
    """Get agent manager from app state via dependency injection."""
    agent_manager = getattr(request.app.state, "agent_manager", None)
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")
    return agent_manager

@router.get("/list", response_model=List[AgentInfo])
async def list_agents(
    request: Request,
    agent_manager=Depends(get_agent_manager),
    tenant_id: str = Depends(get_current_tenant),
    user_id: Optional[str] = Depends(get_current_user),
    _: bool = Depends(require_agent_read),
):
    """List all available agents discovered from adk_agents/ directory.

    **Required Permission:** `agent:read`

    **Authentication:** Required (JWT token or API key)

    **Multi-Tenancy:** Returns agents available to the authenticated tenant.
    """
    try:
        logger.info(f"Listing agents for tenant={tenant_id}, user={user_id}")

        agent_infos = []
        for agent_name, adapter in agent_manager.adapters.items():
            # Extract metadata from ADK agent adapter
            adk_agent = adapter._adk_agent
            info = AgentInfo(
                name=agent_name,
                description=getattr(adk_agent, 'description', f"ADK agent: {agent_name}"),
                capabilities=["chat", "streaming", "tools"] if hasattr(adk_agent, 'tools') and adk_agent.tools else ["chat", "streaming"],
                status="active"
            )
            agent_infos.append(info)

        logger.info(f"Found {len(agent_infos)} agents for tenant={tenant_id}")
        return agent_infos
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    chat_request: ChatRequest,
    request: Request,
    agent_manager=Depends(get_agent_manager),
    tenant_id: str = Depends(get_current_tenant),
    user_id: Optional[str] = Depends(get_current_user),
    _: bool = Depends(require_agent_execute),
):
    """Send a message to an agent and get non-streaming response.

    **Required Permission:** `agent:execute`

    **Authentication:** Required (JWT token or API key)

    **Multi-Tenancy:** Agent execution is isolated by tenant. Sessions are tenant-specific.

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/agents/chat \\
      -H "Authorization: Bearer <your_jwt_token>" \\
      -H "Content-Type: application/json" \\
      -d '{
        "message": "Hello, how can you help me?",
        "agent": "template_simple_agent",
        "session_id": "my-session-123"
      }'
    ```
    """
    try:
        # Use tenant_id from authentication for session isolation
        # Session ID format: {tenant_id}:{user_session_id}
        user_session_id = chat_request.session_id or f"rest_{id(chat_request)}"
        tenant_session_id = f"{tenant_id}:{user_session_id}"

        agent_name = chat_request.agent or "template_simple_agent"

        logger.info(
            f"Chat request: tenant={tenant_id}, user={user_id}, "
            f"agent={agent_name}, session={tenant_session_id}"
        )

        # Use agent manager to get response
        # For REST endpoint, collect all chunks into one response
        full_message = ""

        async for chunk in agent_manager.stream_chat(
            session_id=tenant_session_id,
            message=chat_request.message,
            agent_name=agent_name,
            tenant_id=tenant_id,  # Pass tenant_id for multi-tenant session isolation
        ):
            if chunk.get("type") == "chunk":
                full_message += chunk.get("content", "")
            elif chunk.get("error"):
                raise HTTPException(status_code=500, detail=chunk["error"])

        logger.info(
            f"Chat completed: tenant={tenant_id}, session={tenant_session_id}, "
            f"response_length={len(full_message)}"
        )

        return ChatResponse(
            message=full_message,
            agent=agent_name,
            session_id=user_session_id  # Return user's session ID (without tenant prefix)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

