"""Vertex AI Memory Bank service for long-term agent memory.

This module provides integration with Google's Vertex AI Memory Bank for storing
and retrieving long-term memories across agent conversations. This is separate from
session storage - sessions are short-term conversation history, while memories are
long-term knowledge that persists across sessions.

Architecture:
    - Session Service: Short-term conversation history (RedisSessionService, InMemorySessionService)
    - Memory Service: Long-term knowledge across conversations (VertexMemoryService)
    
Usage:
    memory_service = VertexMemoryService(
        project_id="my-project",
        location="us-central1",
        agent_engine_id="123456"
    )
    
    await memory_service.initialize()
    
    # Add session to long-term memory
    await memory_service.add_session_to_memory(session, tenant_id="acme-corp")
    
    # Search memories for relevant information
    memories = await memory_service.search_memory(
        query="What is the user's preferred temperature?",
        tenant_id="acme-corp",
        user_id="user123"
    )
"""

import logging
from typing import Optional, List, Dict, Any

from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import Session
import vertexai

from config.settings import settings

logger = logging.getLogger(__name__)


class VertexMemoryService:
    """Vertex AI Memory Bank service for long-term agent memory.
    
    This service wraps Google's VertexAiMemoryBankService to provide:
    - Multi-tenant memory isolation
    - Long-term knowledge storage across sessions
    - Semantic search for relevant memories
    - Integration with ADK Runner and agents
    
    Multi-Tenancy:
        Memories are isolated by tenant using the app_name parameter.
        Format: "{tenant_id}:{app_name}"
        
    Memory Lifecycle:
        1. Agent has conversation with user (stored in session)
        2. Session is saved to memory bank (add_session_to_memory)
        3. Memory Bank extracts key information as "memories"
        4. Future conversations can search memories (search_memory)
        5. Relevant memories are included in agent context
    """
    
    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None, agent_engine_id: Optional[str] = None, app_name: Optional[str] = None):
        """Initialize Vertex AI Memory Bank service.
        
        Args:
            project_id: Google Cloud project ID (defaults to settings.google_cloud_project)
            location: Google Cloud region (defaults to settings.google_cloud_region)
            agent_engine_id: Agent Engine instance ID for Memory Bank
                           If None, will create a new Agent Engine instance
            app_name: Application name for memory scoping (defaults to settings.app_name)
        """
        self.project_id = project_id or settings.google_cloud_project
        self.location = location or settings.google_cloud_region
        self.agent_engine_id = agent_engine_id
        self.app_name = app_name or settings.app_name
        
        self._memory_service: Optional[VertexAiMemoryBankService] = None
        self._vertexai_client: Optional[Any] = None
        self._initialized = False
        
        logger.info(
            f"VertexMemoryService configured: "
            f"project={self.project_id}, location={self.location}, "
            f"agent_engine_id={self.agent_engine_id or 'auto-create'}"
        )
    
    async def initialize(self) -> None:
        """Initialize Vertex AI Memory Bank client.
        
        Creates or connects to an Agent Engine instance with Memory Bank.
        This must be called before using the service.
        
        Raises:
            Exception: If initialization fails
        """
        if self._initialized:
            logger.debug("VertexMemoryService already initialized")
            return
        
        try:
            logger.info("Initializing Vertex AI Memory Bank...")
            
            # Initialize Vertex AI client
            self._vertexai_client = vertexai.Client(
                project=self.project_id,
                location=self.location
            )
            
            # Create or get Agent Engine instance
            if self.agent_engine_id:
                logger.info(f"Using existing Agent Engine: {self.agent_engine_id}")
            else:
                logger.info("Creating new Agent Engine instance with Memory Bank...")
                agent_engine = self._vertexai_client.agent_engines.create()
                self.agent_engine_id = agent_engine.api_resource.name.split("/")[-1]
                logger.info(
                    f"Created Agent Engine: {agent_engine.api_resource.name} "
                    f"(ID: {self.agent_engine_id})"
                )
            
            # Initialize Memory Bank service
            self._memory_service = VertexAiMemoryBankService(
                project=self.project_id,
                location=self.location,
                agent_engine_id=self.agent_engine_id
            )
            
            self._initialized = True
            logger.info("✅ Vertex AI Memory Bank initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI Memory Bank: {e}")
            raise
    
    def _get_tenant_app_name(self, tenant_id: str) -> str:
        """Get tenant-specific app name for memory isolation.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant-scoped app name: "{tenant_id}:{app_name}"
        """
        return f"{tenant_id}:{self.app_name}"
    
    async def add_session_to_memory(self, session: Session, tenant_id: str, user_id: Optional[str] = None) -> None:
        """Add session to long-term memory.
        
        Triggers Memory Bank to extract key information from the session
        and store it as searchable memories.
        
        Args:
            session: ADK Session object containing conversation history
            tenant_id: Tenant identifier for multi-tenancy
            user_id: Optional user identifier (extracted from session if not provided)
            
        Raises:
            RuntimeError: If service not initialized
            Exception: If memory generation fails
        """
        if not self._initialized:
            raise RuntimeError("VertexMemoryService not initialized. Call initialize() first.")
        
        try:
            # Get tenant-scoped app name for isolation
            tenant_app_name = self._get_tenant_app_name(tenant_id)
            
            # Extract user_id from session if not provided
            if not user_id and hasattr(session, 'user_id'):
                user_id = session.user_id
            
            logger.info(
                f"Adding session to memory: tenant={tenant_id}, "
                f"session_id={session.id}, user_id={user_id}"
            )
            
            # Trigger memory generation
            # Note: This is an async operation that may take a few seconds
            await self._memory_service.add_session_to_memory(session)
            
            logger.info(
                f"✅ Session added to memory bank: "
                f"app_name={tenant_app_name}, session_id={session.id}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to add session to memory: tenant={tenant_id}, "
                f"session_id={session.id}, error={e}"
            )
            raise
    
    async def search_memory(self, query: str, tenant_id: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search long-term memories for relevant information.
        
        Uses semantic search to find memories relevant to the query.
        
        Args:
            query: Search query (e.g., "What is the user's preferred temperature?")
            tenant_id: Tenant identifier for multi-tenancy
            user_id: User identifier to scope the search
            limit: Maximum number of memories to return
            
        Returns:
            List of memory objects with relevant information
            
        Raises:
            RuntimeError: If service not initialized
            Exception: If search fails
        """
        if not self._initialized:
            raise RuntimeError("VertexMemoryService not initialized. Call initialize() first.")
        
        try:
            # Get tenant-scoped app name for isolation
            tenant_app_name = self._get_tenant_app_name(tenant_id)
            
            logger.debug(
                f"Searching memories: tenant={tenant_id}, user={user_id}, "
                f"query='{query[:50]}...'"
            )
            
            # Search memories (returns SearchMemoryResponse object, not async iterator)
            memories_response = await self._memory_service.search_memory(
                app_name=tenant_app_name,
                user_id=user_id,
                query=query,
            )

            # Debug logging
            logger.debug(f"Memory response type: {type(memories_response)}")
            logger.debug(f"Memory response value: {memories_response}")

            # Convert response to list of dictionaries
            memory_list = []
            if memories_response:
                # Check if it's an iterable (list, tuple, etc.)
                if hasattr(memories_response, '__iter__') and not isinstance(memories_response, (str, bytes)):
                    for memory in memories_response:
                        # Debug logging
                        logger.debug(f"Memory object type: {type(memory)}, value: {memory}")

                        # Convert memory object to dictionary
                        memory_dict = {}

                        if isinstance(memory, dict):
                            memory_dict = memory
                        elif isinstance(memory, tuple):
                            # Handle named tuple or regular tuple
                            if hasattr(memory, '_asdict'):
                                memory_dict = memory._asdict()
                            elif len(memory) == 2:
                                # The tuple is (key, value) - extract the value
                                key, value = memory
                                if isinstance(value, list):
                                    # If value is a list of memory objects, process each
                                    for mem_item in value:
                                        if isinstance(mem_item, dict):
                                            memory_list.append(mem_item)
                                        elif hasattr(mem_item, '__dict__'):
                                            memory_list.append(vars(mem_item))
                                        else:
                                            memory_list.append({"content": str(mem_item)})

                                        if len(memory_list) >= limit:
                                            break
                                    # Skip adding the tuple itself
                                    continue
                                else:
                                    memory_dict = {key: value}
                            else:
                                memory_dict = {"content": str(memory)}
                        elif hasattr(memory, 'to_dict'):
                            memory_dict = memory.to_dict()
                        elif hasattr(memory, '__dict__'):
                            memory_dict = vars(memory)
                        else:
                            # Fallback: convert to string representation
                            memory_dict = {"content": str(memory)}

                        if memory_dict:  # Only append if we have a dict
                            memory_list.append(memory_dict)

                        if len(memory_list) >= limit:
                            break
                else:
                    # If it's a single object, try to convert it
                    if hasattr(memories_response, '__dict__'):
                        memory_list.append(vars(memories_response))
                    else:
                        memory_list.append({"content": str(memories_response)})

            logger.info(
                f"Found {len(memory_list)} memories for tenant={tenant_id}, "
                f"user={user_id}"
            )

            return memory_list
            
        except Exception as e:
            logger.error(
                f"Failed to search memories: tenant={tenant_id}, "
                f"user={user_id}, error={e}"
            )
            raise
    
    async def close(self) -> None:
        """Close the memory service and cleanup resources."""
        if self._initialized:
            logger.info("Closing Vertex AI Memory Bank service")
            self._memory_service = None
            self._vertexai_client = None
            self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if the service is initialized."""
        return self._initialized

