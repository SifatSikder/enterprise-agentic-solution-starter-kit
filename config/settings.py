"""Application settings and configuration.

Environment-based configuration management for enterprise multi-agent framework.
"""

import os
import logging
from functools import lru_cache

from config.environments.base import BaseSettings
from config.environments.development import DevelopmentSettings
from config.environments.production import ProductionSettings

logger = logging.getLogger(__name__)


@lru_cache()
def get_settings() -> BaseSettings:
    """Get environment-specific settings.

    Returns appropriate settings based on ENVIRONMENT variable:
    - development: DevelopmentSettings (relaxed security, verbose logging)
    - production: ProductionSettings (strict security, structured logging)
    - staging: ProductionSettings (same as production)

    Settings are cached for performance.

    Returns:
        Environment-specific settings instance
    """
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        logger.info("Loading production settings")
        return ProductionSettings()
    elif env == "staging":
        logger.info("Loading staging settings (production config)")
        return ProductionSettings()
    else:
        logger.info("Loading development settings")
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()


__all__ = ["settings", "get_settings", "BaseSettings"]
