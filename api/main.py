"""
Main FastAPI application with Google ADK integration
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import json

from api.routes import agents, health, auth, memory
from api.middleware import (SecurityMiddleware,RateLimitMiddleware,SecurityHeadersMiddleware,AuditLogMiddleware)
from agents.manager import AgentManager
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting ADK FastAPI application...")
    agent_manager = AgentManager()
    await agent_manager.initialize()
    logger.info("Agent manager initialized")

    # Store in app state for dependency injection
    app.state.agent_manager = agent_manager

    yield

    # Shutdown
    logger.info("Shutting down application...")
    if hasattr(app.state, 'agent_manager') and app.state.agent_manager:
        await app.state.agent_manager.cleanup()

# Create FastAPI app with security schemes for Swagger UI
app = FastAPI(
    title="D-Ready's Multi Agentic Framework using ADK",
    description="Enterprise-grade multi-agent AI framework with Google ADK, FastAPI, and Vertex AI",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,  # Remember auth between page refreshes
    },
)

# Add security schemes to OpenAPI schema for Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token from /api/auth/login"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Enter your API key"
        }
    }

    # Apply security globally (can be overridden per endpoint)
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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
app.include_router(memory.router, prefix="/api", tags=["memory"])

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
    """WebSocket endpoint for real-time chat with agents."""
    await websocket.accept()
    logger.info(f"WebSocket connection established: {session_id}")

    # Get agent manager from app state
    agent_manager = getattr(websocket.app.state, "agent_manager", None)

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
