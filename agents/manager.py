"""
Agent Manager - Integrates ADK agents with FastAPI
Loads agents from adk_agents/ and makes them available via WebSocket

REFACTORED: Now uses official ADK Runner pattern with multi-tenancy support
"""
import logging
import sys
import importlib
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from config.settings import settings

from agents.core.adapter import ADKAgentAdapter, create_adk_agent_adapter
from agents.core.interfaces import AgentRequest

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages ADK agents for FastAPI integration.

    REFACTORED: Now uses ADK Runner pattern with:
    - Official google.adk.runners.Runner
    - Multi-tenant session isolation
    - ADK-compatible SessionService
    - Agent adapters for AgentInterface compliance
    """

    def __init__(self):
        # Store ADK agent adapters (not raw agents)
        self.adapters: Dict[str, ADKAgentAdapter] = {}

        # Legacy: Keep raw agents for backward compatibility
        self.agents: Dict[str, any] = {}

    async def initialize(self):
        """Initialize the agent manager and load ADK agents.

        REFACTORED: Now creates ADK agent adapters with Runner support
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

        REFACTORED: Now creates ADKAgentAdapter with Runner support
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

            # Store raw agent for backward compatibility
            self.agents[agent_name] = root_agent

            # Create ADK agent adapter with Runner
            adapter = create_adk_agent_adapter(
                adk_agent=root_agent,
                app_name=agent_name,
            )

            # Initialize adapter
            await adapter.initialize()

            # Store adapter
            self.adapters[agent_name] = adapter

            logger.info(f"Loaded ADK agent adapter: {agent_name}")

        except Exception as e:
            logger.error(f"Failed to load agent {agent_name}: {str(e)}")
            raise


    async def stream_chat(
        self,
        session_id: str,
        message: str,
        agent_name: str = "greeting_agent",
        tenant_id: str = "default",
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """Stream chat responses from an ADK agent using Runner.

        REFACTORED: Now uses ADKAgentAdapter with official ADK Runner pattern

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

            # Create agent request
            request = AgentRequest(
                message=message,
                session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id or "anonymous",
                stream=True,
            )

            # Stream using adapter (which uses Runner internally)
            try:
                async for chunk in adapter.stream(request):
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

    async def cleanup(self):
        """Cleanup resources.

        REFACTORED: Now shuts down all agent adapters
        """
        # Shutdown all adapters
        for agent_name, adapter in self.adapters.items():
            try:
                await adapter.shutdown()
                logger.info(f"Shutdown adapter: {agent_name}")
            except Exception as e:
                logger.error(f"Error shutting down adapter {agent_name}: {e}")

        self.adapters.clear()
        self.agents.clear()
        logger.info("Agent manager cleaned up")
