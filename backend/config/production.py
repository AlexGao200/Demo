from environs import Env
from .base import BaseConfig

env = Env()


class ProductionConfig(BaseConfig):
    """Production configuration focused on security and reliability"""

    ENVIRONMENT = "production"
    DEBUG = False
    TESTING = False

    REACT_APP_BACKEND_URL = env.str("REACT_APP_BACKEND_URL", "http://localhost:5000")

    TMP_DIR = env.str("TMP_DIR", default="/app/tmp")

    # Use k8s service discovery
    ELASTICSEARCH_HOST = env.str("ELASTICSEARCH_HOST")

    # Force SSL
    PREFERRED_URL_SCHEME = "https"

    # Production URLs
    FRONTEND_BASE_URL = env.str("FRONTEND_BASE_URL", "https://app.acaceta.com")

    # Rate limiting (more strict in production)
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = BaseConfig.MONGODB_URI

    # Session configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # Additional production-specific settings
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    PROPAGATE_EXCEPTIONS = True
