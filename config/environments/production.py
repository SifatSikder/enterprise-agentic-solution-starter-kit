"""Production environment configuration."""

from typing import List
from pydantic import Field

from config.environments.base import BaseSettings


class ProductionSettings(BaseSettings):
    """Production-specific configuration.
    
    Optimized for security, performance, and reliability.
    """
    
    environment: str = "production"
    
    # Logging - Structured JSON logs for parsing
    log_level: str = "WARNING"
    log_format: str = "json"
    
    # CORS - Strict origins only
    cors_origins: List[str] = Field(
        ...,  # Required in production
        env="CORS_ORIGINS"
    )
    
    # Rate Limiting - Strict limits
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    
    # Security - Required
    require_api_key: bool = True
    
    # Features - Enable production monitoring
    enable_metrics: bool = True
    enable_tracing: bool = True
    enable_audit_log: bool = True
    
    # Vertex AI Memory - Enable in production
    vertex_memory_enabled: bool = True
    
    # Session - Longer TTL for production
    redis_session_ttl: int = 7200  # 2 hours
    
    # Agent - Production timeout
    agent_timeout: int = 300  # 5 minutes
    
    # Additional production settings
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # GCP Secret Manager (for production secrets)
    use_secret_manager: bool = Field(default=True, env="USE_SECRET_MANAGER")
    secret_manager_project: str = Field(
        default="",
        env="SECRET_MANAGER_PROJECT"
    )

