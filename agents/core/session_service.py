"""Session storage implementations for multi-tenant agent framework."""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import timedelta

import redis.asyncio as redis

from agents.core.interfaces import SessionService

logger = logging.getLogger(__name__)


class RedisSessionService:
    """Redis-backed session storage with multi-tenancy support.
    
    Features:
    - Tenant isolation (sessions scoped by tenant_id)
    - TTL/expiration (configurable per session)
    - Atomic operations
    - Connection pooling
    """
    
    def __init__(
        self,
        redis_url: str,
        default_ttl: int = 3600,  # 1 hour default
        max_connections: int = 10,
    ):
        """Initialize Redis session service.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default session TTL in seconds
            max_connections: Max connections in pool
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.max_connections = max_connections
        self._redis: Optional[redis.Redis] = None
        
    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.max_connections,
            )
            logger.info("Redis session service initialized")
    
    async def shutdown(self) -> None:
        """Close Redis connections."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis session service shutdown")
    
    def _get_key(self, session_id: str, tenant_id: str) -> str:
        """Generate Redis key with tenant isolation.
        
        Format: session:{tenant_id}:{session_id}
        """
        return f"session:{tenant_id}:{session_id}"
    
    def _get_tenant_pattern(self, tenant_id: str) -> str:
        """Get pattern for all sessions in a tenant."""
        return f"session:{tenant_id}:*"
    
    async def get_session(
        self,
        session_id: str,
        tenant_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get session history from Redis.

        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier

        Returns:
            List of messages in session, or None if session doesn't exist.
            Empty list [] means session exists but has no messages yet.
        """
        if not self._redis:
            await self.initialize()

        key = self._get_key(session_id, tenant_id)

        try:
            data = await self._redis.get(key)
            if data is not None:
                messages = json.loads(data)
                logger.debug(
                    f"Retrieved session {session_id} for tenant {tenant_id}: "
                    f"{len(messages)} messages"
                )
                return messages
            else:
                logger.debug(f"Session {session_id} not found for tenant {tenant_id}")
                return None  # Session doesn't exist
        except Exception as e:
            logger.error(
                f"Error retrieving session {session_id} for tenant {tenant_id}: {e}"
            )
            return None  # Treat errors as session not found
    
    async def save_session(
        self,
        session_id: str,
        tenant_id: str,
        messages: List[Dict[str, Any]],
        ttl: Optional[int] = None,
    ) -> None:
        """Save session history to Redis with TTL.
        
        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier
            messages: List of messages to save
            ttl: Time-to-live in seconds (uses default if None)
        """
        if not self._redis:
            await self.initialize()
        
        key = self._get_key(session_id, tenant_id)
        ttl = ttl or self.default_ttl
        
        try:
            data = json.dumps(messages)
            await self._redis.setex(key, ttl, data)
            logger.debug(
                f"Saved session {session_id} for tenant {tenant_id}: "
                f"{len(messages)} messages, TTL={ttl}s"
            )
        except Exception as e:
            logger.error(
                f"Error saving session {session_id} for tenant {tenant_id}: {e}"
            )
            raise
    
    async def delete_session(self, session_id: str, tenant_id: str) -> None:
        """Delete session from Redis.
        
        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier
        """
        if not self._redis:
            await self.initialize()
        
        key = self._get_key(session_id, tenant_id)
        
        try:
            await self._redis.delete(key)
            logger.info(f"Deleted session {session_id} for tenant {tenant_id}")
        except Exception as e:
            logger.error(
                f"Error deleting session {session_id} for tenant {tenant_id}: {e}"
            )
            raise
    
    async def list_sessions(
        self, 
        tenant_id: str, 
        user_id: Optional[str] = None
    ) -> List[str]:
        """List all sessions for a tenant.
        
        Note: This scans Redis keys - use sparingly in production.
        For production, consider maintaining a separate index.
        
        Args:
            tenant_id: Tenant identifier
            user_id: Optional user filter (not implemented yet)
            
        Returns:
            List of session IDs
        """
        if not self._redis:
            await self.initialize()
        
        pattern = self._get_tenant_pattern(tenant_id)
        
        try:
            # Scan for keys matching pattern
            session_ids = []
            async for key in self._redis.scan_iter(match=pattern):
                # Extract session_id from key: session:{tenant_id}:{session_id}
                session_id = key.split(":")[-1]
                session_ids.append(session_id)
            
            logger.debug(
                f"Found {len(session_ids)} sessions for tenant {tenant_id}"
            )
            return session_ids
        except Exception as e:
            logger.error(f"Error listing sessions for tenant {tenant_id}: {e}")
            return []
    
    async def extend_ttl(
        self, 
        session_id: str, 
        tenant_id: str, 
        ttl: int
    ) -> bool:
        """Extend session TTL.
        
        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier
            ttl: New TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self._redis:
            await self.initialize()
        
        key = self._get_key(session_id, tenant_id)
        
        try:
            result = await self._redis.expire(key, ttl)
            if result:
                logger.debug(
                    f"Extended TTL for session {session_id} "
                    f"(tenant {tenant_id}) to {ttl}s"
                )
            return bool(result)
        except Exception as e:
            logger.error(
                f"Error extending TTL for session {session_id} "
                f"(tenant {tenant_id}): {e}"
            )
            return False


class InMemorySessionService:
    """In-memory session storage for development/testing.
    
    WARNING: Not suitable for production - data lost on restart.
    Use RedisSessionService for production.
    """
    
    def __init__(self):
        """Initialize in-memory storage."""
        self._sessions: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        logger.warning(
            "Using InMemorySessionService - data will be lost on restart. "
            "Use RedisSessionService for production."
        )
    
    async def initialize(self) -> None:
        """No initialization needed for in-memory."""
        pass
    
    async def shutdown(self) -> None:
        """Clear all sessions."""
        self._sessions.clear()
    
    async def get_session(
        self,
        session_id: str,
        tenant_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get session from memory.

        Returns:
            List of messages in session, or None if session doesn't exist.
            Empty list [] means session exists but has no messages yet.
        """
        tenant_sessions = self._sessions.get(tenant_id)
        if tenant_sessions is None:
            return None  # Tenant has no sessions

        if session_id not in tenant_sessions:
            return None  # Session doesn't exist

        return tenant_sessions[session_id]  # Could be [] if empty
    
    async def save_session(
        self,
        session_id: str,
        tenant_id: str,
        messages: List[Dict[str, Any]],
        ttl: Optional[int] = None,
    ) -> None:
        """Save session to memory (TTL ignored)."""
        if tenant_id not in self._sessions:
            self._sessions[tenant_id] = {}
        self._sessions[tenant_id][session_id] = messages
    
    async def delete_session(self, session_id: str, tenant_id: str) -> None:
        """Delete session from memory."""
        if tenant_id in self._sessions:
            self._sessions[tenant_id].pop(session_id, None)
    
    async def list_sessions(
        self, 
        tenant_id: str, 
        user_id: Optional[str] = None
    ) -> List[str]:
        """List sessions for tenant."""
        return list(self._sessions.get(tenant_id, {}).keys())

