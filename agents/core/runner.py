"""ADK Runner wrapper with multi-tenancy support.

This module wraps google.adk.runners.Runner to add enterprise features:
- Multi-tenancy (tenant_id isolation)
- Redis-backed session storage
- Metrics and logging
- Error handling
"""

import logging
from typing import Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass

from google.adk.runners import Runner as ADKRunner
from google.adk.agents import Agent
from google.genai import types

from agents.core.interfaces import AgentRequest, AgentResponse, AgentHealthStatus
from agents.core.adk_session_adapter import MultiTenantSessionAdapter
from api.exceptions.base import (
    AgentExecutionException,
    SessionNotFoundException,
    TenantNotFoundException,
)
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class RunnerConfig:
    """Configuration for ADK Runner wrapper."""
    
    app_name: str
    agent: Agent
    session_service: Optional[Any] = None  # ADK SessionService
    enable_metrics: bool = True
    enable_logging: bool = True
    timeout_seconds: int = 300


class MultiTenantRunner:
    """Enterprise wrapper for google.adk.runners.Runner with multi-tenancy.
    
    This class wraps the official ADK Runner and adds:
    - Multi-tenant session isolation
    - Redis-backed session storage
    - Metrics collection
    - Enhanced error handling
    - Logging and observability
    
    Example:
        ```python
        from google.adk.agents import Agent
        from agents.core.runner import MultiTenantRunner, RunnerConfig
        
        agent = Agent(name="my_agent", model="gemini-2.0-flash", ...)
        
        config = RunnerConfig(
            app_name="my_app",
            agent=agent
        )
        
        runner = MultiTenantRunner(config)
        await runner.initialize()
        
        # Execute agent
        response = await runner.execute(
            user_id="user123",
            session_id="session456",
            tenant_id="acme-corp",
            message="Hello"
        )
        ```
    """
    
    def __init__(self, config: RunnerConfig):
        """Initialize multi-tenant runner.
        
        Args:
            config: Runner configuration
        """
        self.config = config
        self.agent = config.agent
        self.app_name = config.app_name
        
        # ADK Runner (will be initialized in initialize())
        self._adk_runner: Optional[ADKRunner] = None
        
        # Session service (ADK-compatible)
        self._session_service = config.session_service
        
        # Metrics
        self._execution_count = 0
        self._error_count = 0
        
        logger.info(
            f"MultiTenantRunner created for app '{self.app_name}', "
            f"agent '{self.agent.name}'"
        )
    
    async def initialize(self) -> None:
        """Initialize the runner and session service.

        Raises:
            Exception: If initialization fails
        """
        try:
            # Initialize session service if not provided
            if self._session_service is None:
                logger.info("Using MultiTenantSessionAdapter (ADK-compatible)")
                self._session_service = MultiTenantSessionAdapter()
                await self._session_service.initialize()

            # Create ADK Runner
            self._adk_runner = ADKRunner(
                agent=self.agent,
                app_name=self.app_name,
                session_service=self._session_service
            )

            logger.info(f"MultiTenantRunner initialized for '{self.app_name}'")

        except Exception as e:
            logger.error(f"Failed to initialize runner: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the runner and cleanup resources."""
        try:
            # Cleanup session service if needed
            if hasattr(self._session_service, 'shutdown'):
                await self._session_service.shutdown()
            
            logger.info(f"MultiTenantRunner shutdown for '{self.app_name}'")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def execute(
        self,
        user_id: str,
        session_id: str,
        tenant_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Execute agent and return complete response.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            tenant_id: Tenant identifier (for multi-tenancy)
            message: User message
            context: Optional context data
            
        Returns:
            Complete agent response
            
        Raises:
            AgentExecutionException: If execution fails
            SessionNotFoundException: If session not found
            TenantNotFoundException: If tenant not found
        """
        if not self._adk_runner:
            raise AgentExecutionException(
                "Runner not initialized. Call initialize() first."
            )
        
        try:
            self._execution_count += 1
            
            # Create tenant-scoped session ID
            # Format: {tenant_id}:{session_id}
            scoped_session_id = f"{tenant_id}:{session_id}"
            
            logger.info(
                f"Executing agent for user={user_id}, "
                f"session={scoped_session_id}, tenant={tenant_id}"
            )
            
            # Ensure session exists (create if needed)
            try:
                await self._session_service.get_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=scoped_session_id
                )
            except Exception:
                # Session doesn't exist, create it
                logger.info(f"Creating new session: {scoped_session_id}")
                await self._session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=scoped_session_id
                )

            # Create user message content
            content = types.Content(
                role="user",
                parts=[types.Part(text=message)]
            )

            # Run agent using ADK Runner
            # Note: ADK Runner.run() returns an iterator of events
            final_response_text = ""

            for event in self._adk_runner.run(
                user_id=user_id,
                session_id=scoped_session_id,
                new_message=content
            ):
                # Collect final response
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = event.content.parts[0].text
            
            # Build response
            response = AgentResponse(
                message=final_response_text,
                session_id=session_id,  # Return original session_id (without tenant prefix)
                tenant_id=tenant_id,
                metadata={
                    "agent_name": self.agent.name,
                    "app_name": self.app_name,
                    "execution_count": self._execution_count,
                }
            )
            
            logger.info(f"Agent execution completed for session={scoped_session_id}")
            return response
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Agent execution failed: {e}")
            raise AgentExecutionException(
                f"Failed to execute agent: {str(e)}",
                details={"tenant_id": tenant_id, "session_id": session_id}
            )
    
    async def stream(
        self,
        user_id: str,
        session_id: str,
        tenant_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """Stream agent responses.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            tenant_id: Tenant identifier
            message: User message
            context: Optional context data
            
        Yields:
            Response chunks as they're generated
            
        Raises:
            AgentExecutionException: If execution fails
        """
        if not self._adk_runner:
            raise AgentExecutionException(
                "Runner not initialized. Call initialize() first."
            )
        
        try:
            # Create tenant-scoped session ID
            scoped_session_id = f"{tenant_id}:{session_id}"
            
            logger.info(
                f"Streaming agent for user={user_id}, "
                f"session={scoped_session_id}, tenant={tenant_id}"
            )

            # Ensure session exists (create if needed)
            try:
                await self._session_service.get_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=scoped_session_id
                )
            except Exception:
                # Session doesn't exist, create it
                logger.info(f"Creating new session: {scoped_session_id}")
                await self._session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=scoped_session_id
                )

            # Create user message content
            content = types.Content(
                role="user",
                parts=[types.Part(text=message)]
            )
            
            # Stream using ADK Runner
            for event in self._adk_runner.run(
                user_id=user_id,
                session_id=scoped_session_id,
                new_message=content
            ):
                # Stream partial responses
                if event.partial and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            yield part.text
                
                # Also yield final response
                elif event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            yield part.text
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Agent streaming failed: {e}")
            raise AgentExecutionException(
                f"Failed to stream agent: {str(e)}",
                details={"tenant_id": tenant_id, "session_id": session_id}
            )
    
    async def health_check(self) -> AgentHealthStatus:
        """Check runner health.

        Returns:
            Health status
        """
        is_healthy = self._adk_runner is not None

        return AgentHealthStatus(
            healthy=is_healthy,
            status="healthy" if is_healthy else "unhealthy",
            details={
                "agent_name": self.agent.name,
                "app_name": self.app_name,
                "execution_count": self._execution_count,
                "error_count": self._error_count,
                "session_service": type(self._session_service).__name__,
            }
        )

