"""Agent adapter to bridge ADK agents with AgentInterface protocol.

This module provides an adapter that wraps google.adk.agents.Agent (or LlmAgent)
to implement our AgentInterface protocol, enabling seamless integration with
the FastAPI backend.
"""

import logging
from typing import AsyncIterator, Optional, Dict, Any

from google.adk.agents import Agent, LlmAgent
from google.genai import types

from agents.core.interfaces import (
    AgentInterface,
    AgentRequest,
    AgentResponse,
    AgentHealthStatus,
)
from agents.core.runner import MultiTenantRunner, RunnerConfig
from api.exceptions.base import AgentExecutionException

logger = logging.getLogger(__name__)


class ADKAgentAdapter:
    """Adapter to wrap ADK Agent/LlmAgent with AgentInterface protocol.
    
    This adapter bridges the gap between:
    - Google ADK agents (Agent, LlmAgent)
    - Our AgentInterface protocol (for FastAPI integration)
    
    Features:
    - Implements AgentInterface protocol
    - Uses MultiTenantRunner for execution
    - Handles streaming and non-streaming responses
    - Provides health checks
    - Manages lifecycle (initialize/shutdown)
    
    Example:
        ```python
        from google.adk.agents import Agent
        from agents.core.adapter import ADKAgentAdapter
        
        # Create ADK agent
        adk_agent = Agent(
            name="my_agent",
            model="gemini-2.0-flash",
            description="My agent",
            instruction="You are a helpful assistant",
            tools=[...]
        )
        
        # Wrap with adapter
        adapter = ADKAgentAdapter(adk_agent, app_name="my_app")
        await adapter.initialize()
        
        # Use via AgentInterface
        request = AgentRequest(
            message="Hello",
            session_id="session123",
            tenant_id="acme-corp",
            user_id="user456"
        )
        
        response = await adapter.execute(request)
        ```
    """
    
    def __init__(
        self,
        adk_agent: Agent | LlmAgent,
        app_name: str,
        runner_config: Optional[RunnerConfig] = None,
    ):
        """Initialize ADK agent adapter.
        
        Args:
            adk_agent: Google ADK Agent or LlmAgent instance
            app_name: Application name for the runner
            runner_config: Optional runner configuration
        """
        self.adk_agent = adk_agent
        self.app_name = app_name
        
        # Create runner config
        if runner_config is None:
            runner_config = RunnerConfig(
                app_name=app_name,
                agent=adk_agent,
            )
        
        # Create multi-tenant runner
        self._runner = MultiTenantRunner(runner_config)
        
        logger.info(
            f"ADKAgentAdapter created for agent '{adk_agent.name}', "
            f"app '{app_name}'"
        )
    
    @property
    def name(self) -> str:
        """Get agent name."""
        return self.adk_agent.name
    
    @property
    def description(self) -> str:
        """Get agent description."""
        return self.adk_agent.description or f"ADK agent: {self.adk_agent.name}"
    
    async def initialize(self) -> None:
        """Initialize the adapter and runner.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            await self._runner.initialize()
            logger.info(f"ADKAgentAdapter initialized for '{self.name}'")
        except Exception as e:
            logger.error(f"Failed to initialize adapter: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the adapter and cleanup resources."""
        try:
            await self._runner.shutdown()
            logger.info(f"ADKAgentAdapter shutdown for '{self.name}'")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute agent and return complete response.
        
        Args:
            request: Agent request with message, session, tenant info
        
        Returns:
            Complete agent response
        
        Raises:
            AgentExecutionException: If execution fails
        """
        try:
            logger.info(
                f"Executing agent '{self.name}' for tenant={request.tenant_id}, "
                f"session={request.session_id}"
            )
            
            # Execute via runner
            response = await self._runner.execute(
                user_id=request.user_id or "anonymous",
                session_id=request.session_id,
                tenant_id=request.tenant_id,
                message=request.message,
                context=request.context,
            )
            
            logger.info(f"Agent '{self.name}' execution completed")
            return response
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise AgentExecutionException(
                f"Failed to execute agent '{self.name}': {str(e)}",
                details={
                    "agent_name": self.name,
                    "tenant_id": request.tenant_id,
                    "session_id": request.session_id,
                }
            )
    
    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        """Stream agent responses.
        
        Args:
            request: Agent request with message, session, tenant info
        
        Yields:
            Response chunks as they're generated
        
        Raises:
            AgentExecutionException: If streaming fails
        """
        try:
            logger.info(
                f"Streaming agent '{self.name}' for tenant={request.tenant_id}, "
                f"session={request.session_id}"
            )
            
            # Stream via runner
            async for chunk in self._runner.stream(
                user_id=request.user_id or "anonymous",
                session_id=request.session_id,
                tenant_id=request.tenant_id,
                message=request.message,
                context=request.context,
            ):
                yield chunk
            
            logger.info(f"Agent '{self.name}' streaming completed")
            
        except Exception as e:
            logger.error(f"Agent streaming failed: {e}")
            raise AgentExecutionException(
                f"Failed to stream agent '{self.name}': {str(e)}",
                details={
                    "agent_name": self.name,
                    "tenant_id": request.tenant_id,
                    "session_id": request.session_id,
                }
            )
    
    async def health_check(self) -> AgentHealthStatus:
        """Check agent health.
        
        Returns:
            Health status
        """
        try:
            # Get runner health
            runner_health = await self._runner.health_check()

            return AgentHealthStatus(
                healthy=runner_health.healthy,
                status=runner_health.status,
                details={
                    "agent_name": self.name,
                    "app_name": self.app_name,
                    "agent_type": type(self.adk_agent).__name__,
                    "runner_details": runner_health.details,
                }
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return AgentHealthStatus(
                healthy=False,
                status="error",
                details={
                    "agent_name": self.name,
                    "error": str(e)
                }
            )


def create_adk_agent_adapter(
    adk_agent: Agent | LlmAgent,
    app_name: Optional[str] = None,
) -> ADKAgentAdapter:
    """Factory function to create an ADK agent adapter.
    
    Args:
        adk_agent: Google ADK Agent or LlmAgent instance
        app_name: Optional application name (defaults to agent name)
    
    Returns:
        Configured ADKAgentAdapter instance
    
    Example:
        ```python
        from google.adk.agents import Agent
        from agents.core.adapter import create_adk_agent_adapter
        
        adk_agent = Agent(name="my_agent", ...)
        adapter = create_adk_agent_adapter(adk_agent)
        await adapter.initialize()
        ```
    """
    if app_name is None:
        app_name = adk_agent.name
    
    adapter = ADKAgentAdapter(
        adk_agent=adk_agent,
        app_name=app_name,
    )
    
    logger.info(f"Created ADK agent adapter for '{adk_agent.name}'")
    return adapter

