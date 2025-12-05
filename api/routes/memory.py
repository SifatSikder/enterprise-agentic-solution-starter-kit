"""Memory Bank API endpoints.

Provides REST API for Vertex AI Memory Bank operations.

Endpoints:
    POST /api/memory/save - Save session to memory
    POST /api/memory/search - Search memories
    GET /api/memory/status - Check Memory Bank status
"""

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.dependencies import (
    get_current_tenant,
    get_current_user,
    require_agent_execute,
    get_agent_manager,
)
from agents.manager import AgentManager
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


# Request/Response Models
class SaveSessionRequest(BaseModel):
    """Request to save a session to memory."""
    session_id: str = Field(..., description="Session ID to save to memory")
    user_id: Optional[str] = Field(None, description="User ID (defaults to authenticated user)")


class SaveSessionResponse(BaseModel):
    """Response after saving session to memory."""
    success: bool
    message: str
    session_id: str
    tenant_id: str
    user_id: str


class SearchMemoryRequest(BaseModel):
    """Request to search memories."""
    query: str = Field(..., description="Search query", min_length=1)
    user_id: Optional[str] = Field(None, description="User ID (defaults to authenticated user)")
    limit: int = Field(10, description="Maximum number of memories to return", ge=1, le=100)


class SearchMemoryResponse(BaseModel):
    """Response from memory search."""
    query: str
    memories: List[Dict[str, Any]]
    count: int
    tenant_id: str
    user_id: str


class MemoryStatusResponse(BaseModel):
    """Memory Bank status."""
    enabled: bool
    initialized: bool
    auto_save: bool
    project_id: Optional[str] = None
    location: Optional[str] = None
    agent_engine_id: Optional[str] = None


@router.post("/save", response_model=SaveSessionResponse)
async def save_session_to_memory(
    request_data: SaveSessionRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
    authenticated_user_id: Optional[str] = Depends(get_current_user),
    _: bool = Depends(require_agent_execute),
    agent_manager: AgentManager = Depends(get_agent_manager),
):
    """Save a session to Vertex AI Memory Bank for long-term memory.
    
    **Required Permission:** `agent:execute`
    
    **Authentication:** Required (JWT token or API key)
    
    **Multi-Tenancy:** Memories are isolated by tenant.
    
    This endpoint triggers Memory Bank to extract key information from the session
    and store it as searchable memories for future conversations.
    
    **Example:**
    ```json
    {
        "session_id": "session123",
        "user_id": "user456"  // Optional, defaults to authenticated user
    }
    ```
    """
    # Check if Memory Bank is enabled
    if not settings.vertex_memory_enabled:
        raise HTTPException(
            status_code=503,
            detail="Memory Bank is not enabled. Set VERTEX_MEMORY_ENABLED=true"
        )
    
    # Use authenticated user if not specified
    user_id = request_data.user_id or authenticated_user_id or "anonymous"
    
    try:
        # Save session to memory
        await agent_manager.save_session_to_memory(
            session_id=request_data.session_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        return SaveSessionResponse(
            success=True,
            message="Session saved to memory successfully",
            session_id=request_data.session_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"Failed to save session to memory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save session to memory: {str(e)}"
        )


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memories(
    request_data: SearchMemoryRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
    authenticated_user_id: Optional[str] = Depends(get_current_user),
    _: bool = Depends(require_agent_execute),
    agent_manager: AgentManager = Depends(get_agent_manager),
):
    """Search Vertex AI Memory Bank for relevant memories.
    
    **Required Permission:** `agent:execute`
    
    **Authentication:** Required (JWT token or API key)
    
    **Multi-Tenancy:** Searches only memories for the authenticated tenant.
    
    Uses semantic search to find memories relevant to the query.
    
    **Example:**
    ```json
    {
        "query": "What is the user's preferred temperature?",
        "user_id": "user456",  // Optional, defaults to authenticated user
        "limit": 10
    }
    ```
    """
    # Check if Memory Bank is enabled
    if not settings.vertex_memory_enabled:
        raise HTTPException(
            status_code=503,
            detail="Memory Bank is not enabled. Set VERTEX_MEMORY_ENABLED=true"
        )
    
    # Use authenticated user if not specified
    user_id = request_data.user_id or authenticated_user_id or "anonymous"
    
    try:
        # Search memories
        memories = await agent_manager.search_memory(
            query=request_data.query,
            tenant_id=tenant_id,
            user_id=user_id,
            limit=request_data.limit
        )
        
        return SearchMemoryResponse(
            query=request_data.query,
            memories=memories,
            count=len(memories),
            tenant_id=tenant_id,
            user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search memories: {str(e)}"
        )


@router.get("/status", response_model=MemoryStatusResponse)
async def get_memory_status(
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
    _: bool = Depends(require_agent_execute),
    agent_manager: AgentManager = Depends(get_agent_manager),
):
    """Get Vertex AI Memory Bank status.
    
    **Required Permission:** `agent:execute`
    
    **Authentication:** Required (JWT token or API key)
    
    Returns information about Memory Bank configuration and status.
    """
    memory_service = agent_manager.memory_service
    
    return MemoryStatusResponse(
        enabled=settings.vertex_memory_enabled,
        initialized=memory_service.is_initialized if memory_service else False,
        auto_save=settings.vertex_memory_auto_save,
        project_id=settings.google_cloud_project if settings.vertex_memory_enabled else None,
        location=settings.google_cloud_region if settings.vertex_memory_enabled else None,
        agent_engine_id=settings.vertex_agent_engine_id if settings.vertex_memory_enabled else None,
    )

