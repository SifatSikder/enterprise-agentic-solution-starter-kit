"""ADK SessionService adapter with multi-tenancy support.

This module provides an adapter that wraps our RedisSessionService to be compatible
with google.adk.sessions.BaseSessionService while maintaining multi-tenancy features.
"""

import logging
from typing import Optional, List
from datetime import datetime

from google.adk.sessions import BaseSessionService, Session
from google.adk.events import Event
from google.genai import types

from agents.core.session_service import RedisSessionService, InMemorySessionService
from config.settings import settings

logger = logging.getLogger(__name__)


class MultiTenantSessionAdapter(BaseSessionService):
    """ADK-compatible SessionService with multi-tenancy support.
    
    This adapter wraps our custom RedisSessionService to provide:
    - ADK BaseSessionService interface compliance
    - Multi-tenant session isolation (tenant_id in session_id)
    - Redis-backed persistence
    - Backward compatibility with existing code
    
    Session ID Format:
        - External (ADK): "{tenant_id}:{session_id}"
        - Internal (Redis): session:{tenant_id}:{session_id}
    
    Example:
        ```python
        from agents.core.adk_session_adapter import MultiTenantSessionAdapter
        
        # Initialize adapter
        adapter = MultiTenantSessionAdapter()
        await adapter.initialize()
        
        # Create session with tenant-scoped ID
        session = await adapter.create_session(
            app_name="my_app",
            user_id="user123",
            session_id="acme-corp:session456"  # tenant_id:session_id
        )
        
        # Append events
        event = Event(...)
        await adapter.append_event(session, event)
        ```
    """
    
    def __init__(
        self,
        backend: Optional[RedisSessionService | InMemorySessionService] = None
    ):
        """Initialize multi-tenant session adapter.
        
        Args:
            backend: Optional session storage backend (Redis or InMemory)
                    If None, will auto-select based on settings
        """
        self._backend = backend
        self._initialized = False
        
        logger.info("MultiTenantSessionAdapter created")
    
    async def initialize(self) -> None:
        """Initialize the session backend."""
        if self._initialized:
            return
        
        # Auto-select backend if not provided
        if self._backend is None:
            if settings.redis_url:
                logger.info("Using RedisSessionService backend")
                self._backend = RedisSessionService(
                    redis_url=settings.redis_url,
                    default_ttl=settings.redis_session_ttl,
                )
            else:
                logger.warning("Using InMemorySessionService backend (dev only)")
                self._backend = InMemorySessionService()
        
        # Initialize backend
        await self._backend.initialize()
        self._initialized = True
        
        logger.info("MultiTenantSessionAdapter initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the session backend."""
        if self._backend:
            await self._backend.shutdown()
        self._initialized = False
    
    def _parse_session_id(self, session_id: str) -> tuple[str, str]:
        """Parse tenant_id and session_id from composite session_id.
        
        Args:
            session_id: Composite session ID in format "{tenant_id}:{session_id}"
        
        Returns:
            Tuple of (tenant_id, session_id)
        
        Raises:
            ValueError: If session_id format is invalid
        """
        parts = session_id.split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid session_id format. Expected 'tenant_id:session_id', "
                f"got '{session_id}'"
            )
        return parts[0], parts[1]
    
    async def create_session(
        self,
        app_name: str,
        user_id: str,
        state: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Create a new session.
        
        Args:
            app_name: Application name
            user_id: User identifier
            state: Optional initial state
            session_id: Optional session ID in format "{tenant_id}:{session_id}"
                       If None, a new session_id will be generated
        
        Returns:
            New Session object
        
        Raises:
            ValueError: If session_id format is invalid
        """
        if not self._initialized:
            await self.initialize()
        
        # Parse tenant_id from session_id
        if session_id:
            tenant_id, actual_session_id = self._parse_session_id(session_id)
        else:
            # Generate new session_id
            # Note: Caller should provide tenant_id in session_id
            raise ValueError(
                "session_id is required and must be in format 'tenant_id:session_id'"
            )
        
        # Create ADK Session object
        session = Session(
            id=session_id,  # Keep composite format for ADK
            app_name=app_name,
            user_id=user_id,
            state=state or {},
            events=[],
            last_update_time=datetime.now().timestamp(),
        )
        
        # Initialize empty session in backend
        await self._backend.save_session(
            session_id=actual_session_id,
            tenant_id=tenant_id,
            messages=[],  # Empty initially
        )
        
        logger.info(
            f"Created session: app={app_name}, user={user_id}, "
            f"session={session_id}"
        )
        
        return session
    
    async def get_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> Optional[Session]:
        """Get an existing session.
        
        Args:
            app_name: Application name
            user_id: User identifier
            session_id: Session ID in format "{tenant_id}:{session_id}"
        
        Returns:
            Session object if found, None otherwise
        
        Raises:
            ValueError: If session_id format is invalid
        """
        if not self._initialized:
            await self.initialize()
        
        # Parse tenant_id from session_id
        tenant_id, actual_session_id = self._parse_session_id(session_id)
        
        # Get messages from backend
        messages = await self._backend.get_session(
            session_id=actual_session_id,
            tenant_id=tenant_id,
        )

        if not messages:
            # Auto-create session if it doesn't exist
            # This is required for ADK Runner which expects sessions to exist
            logger.info(f"Session not found, auto-creating: {session_id}")
            return await self.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
        
        # Convert messages to ADK Events
        # Note: This is a simplified conversion
        # In production, you'd need proper message -> Event conversion
        events = []
        state = {}
        
        for msg in messages:
            # Create Event from message
            # This is simplified - adjust based on your message format
            content = types.Content(
                role=msg.get("role", "user"),
                parts=[types.Part(text=msg.get("content", ""))]
            )
            
            event = Event(
                author=msg.get("role", "user"),
                content=content,
            )
            events.append(event)
        
        # Create Session object
        session = Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state,
            events=events,
            last_update_time=datetime.now().timestamp(),
        )
        
        logger.debug(f"Retrieved session: {session_id} with {len(events)} events")
        
        return session
    
    async def append_event(
        self,
        session: Session,
        event: Event,
    ) -> Session:
        """Append an event to a session.
        
        Args:
            session: Session object
            event: Event to append
        
        Returns:
            Updated Session object
        
        Raises:
            ValueError: If session_id format is invalid
        """
        if not self._initialized:
            await self.initialize()
        
        # Parse tenant_id from session_id
        tenant_id, actual_session_id = self._parse_session_id(session.id)
        
        # Append event to session
        session.events.append(event)
        session.last_update_time = datetime.now().timestamp()
        
        # Update state if event has state delta
        if event.actions and event.actions.state_delta:
            session.state.update(event.actions.state_delta.to_dict())
        
        # Convert events to messages for backend storage
        messages = []
        for evt in session.events:
            # Convert Event to message format
            # This is simplified - adjust based on your message format
            if evt.content and evt.content.parts:
                message = {
                    "role": evt.author,
                    "content": evt.content.parts[0].text if evt.content.parts else "",
                    "timestamp": evt.timestamp,
                }
                messages.append(message)
        
        # Save to backend
        await self._backend.save_session(
            session_id=actual_session_id,
            tenant_id=tenant_id,
            messages=messages,
        )
        
        logger.debug(
            f"Appended event to session {session.id}: "
            f"total events={len(session.events)}"
        )
        
        return session
    
    async def delete_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None:
        """Delete a session.
        
        Args:
            app_name: Application name
            user_id: User identifier
            session_id: Session ID in format "{tenant_id}:{session_id}"
        
        Raises:
            ValueError: If session_id format is invalid
        """
        if not self._initialized:
            await self.initialize()
        
        # Parse tenant_id from session_id
        tenant_id, actual_session_id = self._parse_session_id(session_id)
        
        # Delete from backend
        await self._backend.delete_session(
            session_id=actual_session_id,
            tenant_id=tenant_id,
        )
        
        logger.info(f"Deleted session: {session_id}")
    
    async def list_sessions(
        self,
        app_name: str,
        user_id: str,
    ) -> List[Session]:
        """List all sessions for a user.
        
        Note: This implementation is limited because we can't easily
        filter by app_name and user_id with our current backend.
        
        Args:
            app_name: Application name
            user_id: User identifier
        
        Returns:
            List of Session objects (may be empty)
        """
        if not self._initialized:
            await self.initialize()
        
        # Note: Our backend doesn't support filtering by app_name/user_id
        # This is a limitation that should be addressed in production
        logger.warning(
            "list_sessions is not fully implemented - "
            "cannot filter by app_name/user_id with current backend"
        )
        
        return []

