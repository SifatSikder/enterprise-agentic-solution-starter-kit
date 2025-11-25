"""
Main FastAPI application with Google ADK integration
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import logging
from typing import Optional
import json

from api.routes import agents, health, auth, memory
from api.models.requests import ChatRequest, ChatResponse
from api.middleware import (
    SecurityMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    AuditLogMiddleware,
)
from agents.manager import AgentManager
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global agent manager
agent_manager: Optional[AgentManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global agent_manager
    
    # Startup
    logger.info("Starting ADK FastAPI application...")
    agent_manager = AgentManager()
    await agent_manager.initialize()
    logger.info("Agent manager initialized")

    # Inject agent_manager into app state for dependency injection
    app.state.agent_manager = agent_manager

    # Legacy: Also inject into agents routes for backward compatibility
    from api.routes import agents as agents_routes
    agents_routes.set_agent_manager(agent_manager)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if agent_manager:
        await agent_manager.cleanup()

# Create FastAPI app
app = FastAPI(
    title="ADK Multi-Agent Framework",
    description="Enterprise-grade multi-agent AI framework with Google ADK, FastAPI, and Vertex AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add security middleware (order matters!)
# 1. Security headers (first)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Audit logging
app.add_middleware(AuditLogMiddleware)

# 3. Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute
)

# 4. Authentication & authorization
# Parse API keys from environment
api_keys_dict = {}
if settings.api_keys:
    for idx, key in enumerate(settings.api_keys.split(",")):
        key = key.strip()
        if key:
            api_keys_dict[key] = {
                "tenant_id": f"tenant_{idx}",
                "name": f"api_key_{idx}",
                "permissions": ["agent:read", "agent:execute"],
            }

app.add_middleware(SecurityMiddleware, api_keys=api_keys_dict)

# 5. CORS (last middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(memory.router, prefix="/api", tags=["memory"])  # Phase 5: Memory Bank routes

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Google ADK + FastAPI Workshop API!",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat with agents"""
    await websocket.accept()
    logger.info(f"WebSocket connection established: {session_id}")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process with agent manager
            if agent_manager:
                async for chunk in agent_manager.stream_chat(
                    session_id=session_id,
                    message=message_data.get("message", ""),
                    agent_name=message_data.get("agent", "default")
                ):
                    await websocket.send_json(chunk)
            else:
                await websocket.send_json({
                    "error": "Agent manager not initialized"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
