"""Agent factory for creating and managing agent instances."""

import logging
from typing import Dict, Type, Any, Optional
from pathlib import Path
import importlib.util

from agents.core.interfaces import AgentInterface
from api.exceptions import AgentNotFoundException, AgentInitializationException

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating and managing agent instances.
    
    Features:
    - Agent registration and discovery
    - Lazy loading of agents
    - Agent lifecycle management
    - Multi-tenancy support (tenant-specific agent configs)
    """
    
    def __init__(self):
        """Initialize agent factory."""
        self._registry: Dict[str, Type[AgentInterface]] = {}
        self._instances: Dict[str, AgentInterface] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}
        logger.info("AgentFactory initialized")
    
    def register(
        self,
        agent_name: str,
        agent_class: Type[AgentInterface],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register an agent type.
        
        Args:
            agent_name: Unique agent identifier
            agent_class: Agent class implementing AgentInterface
            config: Optional default configuration
        """
        self._registry[agent_name] = agent_class
        if config:
            self._configs[agent_name] = config
        logger.info(f"Registered agent: {agent_name}")
    
    def unregister(self, agent_name: str) -> None:
        """Unregister an agent type.
        
        Args:
            agent_name: Agent identifier to unregister
        """
        self._registry.pop(agent_name, None)
        self._configs.pop(agent_name, None)
        self._instances.pop(agent_name, None)
        logger.info(f"Unregistered agent: {agent_name}")
    
    async def create(
        self,
        agent_name: str,
        config: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> AgentInterface:
        """Create agent instance.
        
        Args:
            agent_name: Agent identifier
            config: Optional configuration override
            tenant_id: Optional tenant ID for tenant-specific config
            
        Returns:
            Agent instance
            
        Raises:
            AgentNotFoundException: If agent not registered
            AgentInitializationException: If initialization fails
        """
        if agent_name not in self._registry:
            raise AgentNotFoundException(agent_name)
        
        # Build configuration
        agent_config = self._configs.get(agent_name, {}).copy()
        if config:
            agent_config.update(config)
        
        # Add tenant context if provided
        if tenant_id:
            agent_config["tenant_id"] = tenant_id
        
        try:
            agent_class = self._registry[agent_name]
            agent = agent_class(**agent_config)
            
            # Initialize agent
            await agent.initialize()
            
            logger.info(
                f"Created agent instance: {agent_name}"
                + (f" for tenant {tenant_id}" if tenant_id else "")
            )
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent {agent_name}: {e}")
            raise AgentInitializationException(agent_name, str(e))
    
    async def get_or_create(
        self,
        agent_name: str,
        config: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> AgentInterface:
        """Get existing agent instance or create new one.
        
        For singleton agents (shared across requests).
        
        Args:
            agent_name: Agent identifier
            config: Optional configuration
            tenant_id: Optional tenant ID
            
        Returns:
            Agent instance
        """
        # Create instance key (include tenant for multi-tenancy)
        instance_key = f"{agent_name}:{tenant_id}" if tenant_id else agent_name
        
        if instance_key not in self._instances:
            self._instances[instance_key] = await self.create(
                agent_name, config, tenant_id
            )
        
        return self._instances[instance_key]
    
    def list_agents(self) -> list[str]:
        """List all registered agent names.
        
        Returns:
            List of agent names
        """
        return list(self._registry.keys())
    
    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Get agent information.
        
        Args:
            agent_name: Agent identifier
            
        Returns:
            Agent metadata
            
        Raises:
            AgentNotFoundException: If agent not registered
        """
        if agent_name not in self._registry:
            raise AgentNotFoundException(agent_name)
        
        agent_class = self._registry[agent_name]
        return {
            "name": agent_name,
            "class": agent_class.__name__,
            "module": agent_class.__module__,
            "config": self._configs.get(agent_name, {}),
        }
    
    async def shutdown_all(self) -> None:
        """Shutdown all agent instances."""
        for instance_key, agent in self._instances.items():
            try:
                await agent.shutdown()
                logger.info(f"Shutdown agent instance: {instance_key}")
            except Exception as e:
                logger.error(f"Error shutting down agent {instance_key}: {e}")
        
        self._instances.clear()
        logger.info("All agents shutdown")


class ADKAgentDiscovery:
    """Auto-discovery for ADK agents from directory.
    
    Scans adk_agents/ directory and registers all agents.
    """
    
    def __init__(self, factory: AgentFactory, agents_path: Path):
        """Initialize ADK agent discovery.
        
        Args:
            factory: Agent factory to register agents with
            agents_path: Path to adk_agents directory
        """
        self.factory = factory
        self.agents_path = agents_path
    
    def discover_and_register(self) -> int:
        """Discover and register all ADK agents.
        
        Returns:
            Number of agents registered
        """
        if not self.agents_path.exists():
            logger.warning(f"Agents path does not exist: {self.agents_path}")
            return 0
        
        count = 0
        for agent_dir in self.agents_path.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith("_"):
                continue
            
            agent_file = agent_dir / "agent.py"
            if not agent_file.exists():
                logger.debug(f"Skipping {agent_dir.name}: no agent.py found")
                continue
            
            try:
                # Load agent module
                spec = importlib.util.spec_from_file_location(
                    f"adk_agents.{agent_dir.name}.agent",
                    agent_file,
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Get root_agent
                    if hasattr(module, "root_agent"):
                        agent = module.root_agent
                        agent_name = agent_dir.name
                        
                        # Wrap ADK agent in adapter (to be implemented)
                        # For now, just log discovery
                        logger.info(f"Discovered ADK agent: {agent_name}")
                        count += 1
                    else:
                        logger.warning(
                            f"Agent {agent_dir.name} has no 'root_agent' variable"
                        )
            except Exception as e:
                logger.error(f"Error loading agent {agent_dir.name}: {e}")
        
        logger.info(f"Discovered {count} ADK agents")
        return count

