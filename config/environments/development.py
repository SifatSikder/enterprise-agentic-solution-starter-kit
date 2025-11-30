"""Development environment configuration."""

from typing import List
from config.environments.base import BaseSettings


class DevelopmentSettings(BaseSettings):
    """Development-specific configuration.
    
    Optimized for local development with relaxed security and verbose logging.
    """
    
    environment: str = "development"
    
    # Logging - Verbose for debugging
    log_level: str = "DEBUG"
    log_format: str = "text"
    
    # CORS - Allow all origins in dev
    cors_origins: List[str] = ["*"]
    
    # Rate Limiting - Relaxed for testing
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 1000
    
    # Security - Disabled for easier testing
    require_api_key: bool = False
    
    # Features - Enable all for testing
    enable_metrics: bool = True
    enable_tracing: bool = True
    enable_audit_log: bool = True
    
    # Vertex AI Memory - Disabled in dev (use Redis)
    vertex_memory_enabled: bool = False
    
    # Session - Shorter TTL for testing
    redis_session_ttl: int = 1800  # 30 minutes
    
    # Agent - Shorter timeout for faster feedback
    agent_timeout: int = 60  # 1 minute

