"""Agent interfaces and protocols for enterprise multi-agent framework."""

from typing import Protocol, AsyncIterator, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentRequest:
    """Request to execute an agent.
    
    Attributes:
        message: User message/query
        session_id: Unique session identifier
        tenant_id: Tenant/organization identifier for multi-tenancy
        user_id: User identifier for tracking and quotas
        context: Additional context (metadata, settings, etc.)
        stream: Whether to stream response chunks
    """
    message: str
    session_id: str
    tenant_id: str
    user_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    stream: bool = True
    
    def __post_init__(self):
        """Validate request."""
        if not self.message:
            raise ValueError("Message cannot be empty")
        if not self.session_id:
            raise ValueError("Session ID is required")
        if not self.tenant_id:
            raise ValueError("Tenant ID is required for multi-tenancy")


@dataclass
class AgentResponse:
    """Response from agent execution.
    
    Attributes:
        message: Agent response message
        status: Execution status
        metadata: Additional metadata (model used, tokens, etc.)
        error: Error message if failed
        execution_time: Time taken to execute (seconds)
        timestamp: Response timestamp
    """
    message: str
    status: AgentStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message": self.message,
            "status": self.status.value,
            "metadata": self.metadata,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AgentHealthStatus:
    """Agent health check status.
    
    Attributes:
        healthy: Whether agent is healthy
        status: Status message
        details: Additional health details
        last_check: Last health check timestamp
    """
    healthy: bool
    status: str
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "healthy": self.healthy,
            "status": self.status,
            "details": self.details,
            "last_check": self.last_check.isoformat(),
        }


class AgentInterface(Protocol):
    """Protocol defining the interface for all agent implementations.
    
    This protocol ensures all agents (ADK, custom, third-party) implement
    a consistent interface for execution, streaming, and health checks.
    """
    
    name: str
    description: str
    
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute agent and return complete response.
        
        Args:
            request: Agent request with message and context
            
        Returns:
            Complete agent response
            
        Raises:
            AgentExecutionException: If execution fails
        """
        ...
    
    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        """Stream agent response chunks.
        
        Args:
            request: Agent request with message and context
            
        Yields:
            Response chunks as they are generated
            
        Raises:
            AgentExecutionException: If execution fails
        """
        ...
    
    async def health_check(self) -> AgentHealthStatus:
        """Check if agent is healthy and ready to process requests.
        
        Returns:
            Health status with details
        """
        ...
    
    async def initialize(self) -> None:
        """Initialize agent resources (connections, models, etc.).
        
        Called once when agent is loaded.
        """
        ...
    
    async def shutdown(self) -> None:
        """Cleanup agent resources.
        
        Called when agent is being unloaded.
        """
        ...