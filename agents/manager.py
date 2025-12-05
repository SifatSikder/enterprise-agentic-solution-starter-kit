"""
Agent Manager - Integrates ADK agents with FastAPI
Loads agents from adk_agents/ and makes them available via WebSocket

Uses official ADK Runner pattern with multi-tenancy support
Vertex AI Memory Bank integration for long-term memory
"""
import logging
import sys
import importlib
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from config.settings import settings

from agents.core.adapter import ADKAgentAdapter, create_adk_agent_adapter
from agents.core.vertex_memory_service import VertexMemoryService
from agents.helpers import scope_session_id

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages ADK agents for FastAPI integration.

    This class uses ADK Runner pattern with:
    - Official google.adk.runners.Runner
    - Multi-tenant session isolation
    - ADK-compatible SessionService
    - Agent adapters for AgentInterface compliance
    """

    def __init__(self):
        # Store ADK agent adapters (not raw agents)
        self.adapters: Dict[str, ADKAgentAdapter] = {}

        # Vertex AI Memory Bank service for long-term memory
        self.memory_service: Optional[VertexMemoryService] = None

    async def initialize(self):
        """Initialize the agent manager and load ADK agents.

        Discovers and loads ADK agents from adk_agents/ directory,
        creates adapters with Runner support, and optionally initializes
        Vertex AI Memory Bank for long-term memory storage.
        """
        try:
            # Add adk_agents to Python path
            adk_agents_path = Path(__file__).parent.parent / "adk_agents"
            sys.path.insert(0, str(adk_agents_path))

            # Auto-discover agents from adk_agents/ directory
            discovered_agents = self._discover_agents(adk_agents_path)
            logger.info(f"Discovered {len(discovered_agents)} agents: {discovered_agents}")

            # Load each discovered agent
            for agent_name in discovered_agents:
                await self._load_adk_agent(agent_name)

            logger.info("Agent manager initialized successfully")
            logger.info(f"Loaded {len(self.adapters)} ADK agent adapters: {list(self.adapters.keys())}")

            # Initialize Vertex AI Memory Bank if enabled
            if settings.vertex_memory_enabled:
                logger.info("Creating Vertex AI Memory Bank...")
                self.memory_service = VertexMemoryService(
                    project_id=settings.google_cloud_project,
                    location=settings.google_cloud_region,
                    agent_engine_id=settings.vertex_agent_engine_id,
                    app_name=settings.app_name,
                )
                await self.memory_service.initialize()
                logger.info("✅ Vertex AI Memory Bank enabled and initialized")
            else:
                logger.info("Vertex AI Memory Bank disabled (VERTEX_MEMORY_ENABLED=false)")

        except Exception as e:
            logger.error(f"Failed to initialize agent manager: {str(e)}")
            raise

    def _discover_agents(self, adk_agents_path: Path) -> List[str]:
        """Discover all valid ADK agents in adk_agents/ directory

        An agent is valid if:
        1. It's a directory in adk_agents/
        2. It contains agent.py file
        3. The agent.py file exports a 'root_agent' variable

        Args:
            adk_agents_path: Path to adk_agents directory

        Returns:
            List of agent names (directory names)
        """
        agents = []

        if not adk_agents_path.exists():
            logger.warning(f"ADK agents path not found: {adk_agents_path}")
            return agents

        for item in adk_agents_path.iterdir():
            # Skip hidden directories and __pycache__
            if not item.is_dir() or item.name.startswith('_') or item.name.startswith('.'):
                continue

            # Check for agent.py file
            agent_file = item / "agent.py"
            if not agent_file.exists():
                logger.debug(f"Skipping {item.name}: no agent.py found")
                continue

            # Verify it exports root_agent (simple text search)
            try:
                content = agent_file.read_text()
                if 'root_agent' in content:
                    agents.append(item.name)
                    logger.debug(f"Discovered agent: {item.name}")
                else:
                    logger.debug(f"Skipping {item.name}: no root_agent variable")
            except Exception as e:
                logger.warning(f"Error checking {item.name}: {e}")

        return sorted(agents)  # Alphabetical order

    async def _load_adk_agent(self, agent_name: str):
        """Load an ADK agent from adk_agents/ directory.

        Creates an ADKAgentAdapter with Runner support for the agent.

        Args:
            agent_name: Name of the agent module to load
        """
        try:
            # Import the actual ADK agent module
            module_path = f"{agent_name}.agent"
            agent_module = importlib.import_module(module_path)

            # Get the root_agent object
            if not hasattr(agent_module, 'root_agent'):
                raise AttributeError(f"Agent module {agent_name} missing 'root_agent'")

            root_agent = agent_module.root_agent

            # Configure API credentials globally for ADK
            # ADK uses environment variables or global client configuration
            if settings.google_api_key:
                import os
                # Set GOOGLE_API_KEY environment variable for ADK to use
                os.environ["GOOGLE_API_KEY"] = settings.google_api_key
                logger.debug(f"Set GOOGLE_API_KEY environment variable for agent {agent_name}")

            # Create ADK agent adapter with Runner
            adapter = create_adk_agent_adapter(adk_agent=root_agent,app_name=agent_name)

            # Initialize adapter
            await adapter.initialize()

            # Store adapter
            self.adapters[agent_name] = adapter

            logger.info(f"Loaded ADK agent adapter: {agent_name}")

        except Exception as e:
            logger.error(f"Failed to load agent {agent_name}: {str(e)}")
            raise

    async def stream_chat(self, session_id: str, message: str, agent_name: str = "template_simple_agent", tenant_id: str = "default", user_id: Optional[str] = None) -> AsyncGenerator[Dict, None]:
        """Stream chat responses from an ADK agent using Runner.

        Uses ADKAgentAdapter with official ADK Runner pattern.
        Auto-saves session to Memory Bank after completion if enabled.

        Args:
            session_id: Session identifier
            message: User message
            agent_name: Name of agent to use
            tenant_id: Tenant identifier (for multi-tenancy)
            user_id: Optional user identifier

        Yields:
            Dict with streaming chunks and completion status
        """
        try:
            # Get the agent adapter
            if agent_name not in self.adapters:
                yield {"error": f"Agent '{agent_name}' not found. Available: {list(self.adapters.keys())}"}
                return

            adapter = self.adapters[agent_name]

            # Stream using adapter's domain-level method (adapter handles request conversion)
            try:
                async for chunk in adapter.stream_chat(
                    message=message,
                    session_id=session_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                ):
                    yield {
                        "type": "chunk",
                        "content": chunk,
                        "agent": agent_name
                    }

                # Send completion signal
                yield {
                    "type": "complete",
                    "agent": agent_name
                }

                # Auto-save session to Memory Bank (if enabled)
                if settings.vertex_memory_enabled and settings.vertex_memory_auto_save:
                    try:
                        await self.save_session_to_memory(
                            session_id=session_id,
                            tenant_id=tenant_id,
                            user_id=user_id or "anonymous"
                        )
                    except Exception as mem_error:
                        # Don't fail the request if memory save fails
                        logger.warning(
                            f"Failed to auto-save session to memory: {mem_error}"
                        )

            except Exception as e:
                logger.error(f"Agent execution error: {str(e)}")
                yield {
                    "type": "error",
                    "content": f"Error: {str(e)}",
                    "agent": agent_name
                }

        except Exception as e:
            logger.error(f"Stream chat error: {str(e)}")
            yield {"error": str(e)}

    async def save_session_to_memory(self, session_id: str, tenant_id: str, user_id: str) -> None:
        """Save session to Vertex AI Memory Bank for long-term memory.

        Extracts key information from the session and stores it
        as searchable memories for future conversations.

        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier
            user_id: User identifier

        Raises:
            RuntimeError: If Memory Bank is not enabled or initialized
        """
        if not self.memory_service:
            raise RuntimeError(
                "Memory Bank not enabled. Set VERTEX_MEMORY_ENABLED=true"
            )

        try:
            # Get the session from the adapter's session service
            # We need to retrieve the full session object to save to memory
            adapter = next(iter(self.adapters.values()))  # Get any adapter
            session_service = adapter.get_session_service()

            # Get the app name from the adapter (e.g., "template_simple_agent")
            # This is critical - we need to use the SAME app_name that was used
            # when creating the session, otherwise we'll get an empty session
            app_name = adapter.get_runner_app_name()

            # The runner adds tenant prefix to session_id internally
            # So the actual session ID in storage is: {tenant_id}:{session_id}
            scoped_session_id = scope_session_id(tenant_id, session_id)

            # Get the session
            session = await session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=scoped_session_id
            )

            # Save to memory bank
            await self.memory_service.add_session_to_memory(
                session=session,
                tenant_id=tenant_id,
                user_id=user_id
            )

            logger.info(
                f"✅ Session saved to memory: tenant={tenant_id}, "
                f"session={session_id}, user={user_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to save session to memory: tenant={tenant_id}, "
                f"session={session_id}, error={e}"
            )
            raise

    async def search_memory(self, query: str, tenant_id: str, user_id: str, limit: int = 10) -> List[Dict]:
        """Search Vertex AI Memory Bank for relevant memories.

        Uses semantic search to find memories relevant to the query.

        Args:
            query: Search query
            tenant_id: Tenant identifier
            user_id: User identifier
            limit: Maximum number of memories to return

        Returns:
            List of memory objects

        Raises:
            RuntimeError: If Memory Bank is not enabled or initialized
        """
        if not self.memory_service:
            raise RuntimeError(
                "Memory Bank not enabled. Set VERTEX_MEMORY_ENABLED=true"
            )

        try:
            memories = await self.memory_service.search_memory(
                query=query,
                tenant_id=tenant_id,
                user_id=user_id,
                limit=limit
            )

            logger.info(
                f"Found {len(memories)} memories for tenant={tenant_id}, "
                f"user={user_id}"
            )

            return memories

        except Exception as e:
            logger.error(
                f"Failed to search memories: tenant={tenant_id}, "
                f"user={user_id}, error={e}"
            )
            raise

    async def cleanup(self):
        """Cleanup resources.

        Shuts down all agent adapters and closes Memory Bank service.
        """
        # Shutdown all adapters
        for agent_name, adapter in self.adapters.items():
            try:
                await adapter.shutdown()
                logger.info(f"Shutdown adapter: {agent_name}")
            except Exception as e:
                logger.error(f"Error shutting down adapter {agent_name}: {e}")

        self.adapters.clear()

        # Close Memory Bank service if enabled
        if self.memory_service:
            try:
                await self.memory_service.close()
                logger.info("Closed Vertex AI Memory Bank service")
            except Exception as e:
                logger.error(f"Error closing Memory Bank service: {e}")

        logger.info("Agent manager cleaned up")
