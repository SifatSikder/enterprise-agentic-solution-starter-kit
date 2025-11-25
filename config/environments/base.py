"""Base configuration shared across all environments."""

from typing import List, Optional
from pydantic_settings import BaseSettings as PydanticBaseSettings
from pydantic import Field


class BaseSettings(PydanticBaseSettings):
    """Base configuration for all environments.
    
    Attributes shared across development, staging, and production.
    """
    
    # Application
    app_name: str = "ADK Multi-Agent Framework"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Google Cloud / Vertex AI
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    google_cloud_project: str = Field(..., env="GOOGLE_CLOUD_PROJECT")
    google_cloud_region: str = Field(default="us-central1", env="GOOGLE_CLOUD_REGION")
    
    # Default AI Model
    default_model: str = Field(
        default="gemini-2.0-flash-exp",
        env="DEFAULT_MODEL"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = "json"  # json or text
    
    # Redis (optional - if not set, uses in-memory sessions)
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_session_ttl: int = Field(default=3600, env="REDIS_SESSION_TTL")  # 1 hour
    
    # API Configuration
    api_prefix: str = "/api"
    api_version: str = "v1"
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Multi-tenancy
    multi_tenancy_enabled: bool = True
    default_tenant_id: str = Field(default="default", env="DEFAULT_TENANT_ID")
    
    # Session Management
    session_max_messages: int = 100
    session_cleanup_interval: int = 3600  # 1 hour
    
    # Agent Configuration
    agent_timeout: int = 300  # 5 minutes
    agent_max_retries: int = 3
    
    # Vertex AI Memory Bank (Phase 5)
    vertex_memory_enabled: bool = Field(default=False, env="VERTEX_MEMORY_ENABLED")
    vertex_agent_engine_id: Optional[str] = Field(
        default=None,
        env="VERTEX_AGENT_ENGINE_ID",
        description="Agent Engine ID for Memory Bank. If None, creates new instance."
    )
    vertex_memory_auto_save: bool = Field(
        default=True,
        env="VERTEX_MEMORY_AUTO_SAVE",
        description="Automatically save sessions to memory after each conversation"
    )
    
    # Feature Flags
    enable_metrics: bool = False
    enable_tracing: bool = False
    enable_audit_log: bool = False
    
    # Security
    api_key_header: str = "X-API-Key"
    require_api_key: bool = Field(default=False, env="REQUIRE_API_KEY")  # Enable in production

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production-min-32-chars",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")

    # API Keys (for service-to-service authentication)
    # Format: key1,key2,key3
    api_keys: str = Field(default="", env="API_KEYS")

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

