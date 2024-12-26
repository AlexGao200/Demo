from environs import Env
from langchain.prompts import PromptTemplate

env = Env()


class BaseConfig:
    """Base configuration with security-first defaults"""

    ENVIRONMENT = env.str("FLASK_ENV", "development")
    DEBUG = False
    TESTING = False

    # Core settings
    SECRET_KEY = env.str("SECRET_KEY")
    FRONTEND_BASE_URL = env.str("FRONTEND_BASE_URL", "http://localhost:3000")
    ALLOWED_ORIGINS = env.str(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000,http://af0971456cb2746be84e345974054aac-2004908522.us-west-1.elb.amazonaws.com/",
    )

    # Security headers (secure by default)
    STRICT_TRANSPORT_SECURITY = True
    STRICT_TRANSPORT_SECURITY_PRELOAD = True
    STRICT_TRANSPORT_SECURITY_MAX_AGE = 31536000  # 1 year
    STRICT_TRANSPORT_SECURITY_INCLUDE_SUBDOMAINS = True

    CONTENT_SECURITY_POLICY = {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self'",
        "img-src": "'self' data: https:",
        "font-src": "'self'",
        "connect-src": "'self'",
    }

    # Service endpoints with sane defaults
    ELASTICSEARCH_HOST = env.str("ELASTICSEARCH_HOST", "localhost")
    ELASTICSEARCH_PORT = env.int("ELASTICSEARCH_PORT", 9200)
    ELASTICSEARCH_USER = env.str("ELASTICSEARCH_USER")
    ELASTICSEARCH_PASSWORD = env.str("ELASTICSEARCH_PASSWORD")
    MONGODB_URI = env.str("MONGODB_URI", "mongodb://localhost:27017/documents")

    # AWS configuration
    AWS_REGION = env.str("AWS_REGION", "us-west-1")
    AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET_NAME = env.str("AWS_S3_BUCKET_NAME")  # Alias for consistency
    AWS_S3_HIGHLIGHTED_BUCKET_NAME = env.str("AWS_S3_HIGHLIGHTED_BUCKET_NAME")
    AWS_S3_THUMBNAIL_BUCKET_NAME = env.str("AWS_S3_THUMBNAIL_BUCKET_NAME")
    AWS_S3_PETITION_BUCKET_NAME = env.str("AWS_S3_PETITION_BUCKET_NAME")

    # Mail configuration
    MAIL_USE_TLS = env.bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = env.bool("MAIL_USE_SSL", False)
    MAIL_SERVER = env.str("MAIL_SERVER")
    MAIL_PORT = env.int("MAIL_PORT", 587)
    MAIL_USERNAME = env.str("MAIL_USERNAME")
    MAIL_PASSWORD = env.str("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = env.str("MAIL_DEFAULT_SENDER", "info@acaceta.com")

    # Model and API configuration
    DEFAULT_EMBEDDING_DIMS = env.int("DEFAULT_EMBEDDING_DIMS", 1024)
    ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY")
    TOGETHER_API_KEY = env.str("TOGETHER_API_KEY")
    COHERE_API_KEY = env.str("COHERE_API_KEY")
    GROQ_API_KEY = env.str("GROQ_API_KEY")
    STRIPE_SECRET_KEY = env.str("STRIPE_SECRET_KEY")
    REACT_APP_STRIPE_PUBLIC_KEY = env.str("REACT_APP_STRIPE_PUBLIC_KEY")
    STRIPE_WEBHOOK_SECRET = env.str("STRIPE_WEBHOOK_SECRET")
    HYPERBOLIC_API_KEY = env.str("HYPERBOLIC_API_KEY")
    VOYAGE_API_KEY = env.str("VOYAGE_API_KEY")

    # Rate limiting defaults (can be overridden)
    RATELIMIT_DEFAULT = "200 per minute"
    RATELIMIT_STORAGE_URL = MONGODB_URI

    # Session configuration (secure by default)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    RAG_GENERATION_PROMPT = PromptTemplate.from_template(
        """
            <s> [INST] You are an assistant for question-answering tasks. Use the following pieces of retrieved context
            to answer the question. If you don't know the answer, just say that you don't know. Keep the answer concise
            but do not leave out any necessary details. Cite documents where applicable. Format responses into organized
            sections and lists using Markdown, including headers, bullet points, and tables where relevant. Do not include a
            section whos sole purpose is for listing citations. [/INST] </s>
            [INST] Question: {question}
            Context: {context}
            Answer: [/INST]
            """
    )

    @classmethod
    def configure_app(cls, app):
        """Configure Flask app with security headers"""

        @app.after_request
        def add_security_headers(response):
            if cls.STRICT_TRANSPORT_SECURITY:
                sts_header = f"max-age={cls.STRICT_TRANSPORT_SECURITY_MAX_AGE}"
                if cls.STRICT_TRANSPORT_SECURITY_INCLUDE_SUBDOMAINS:
                    sts_header += "; includeSubDomains"
                if cls.STRICT_TRANSPORT_SECURITY_PRELOAD:
                    sts_header += "; preload"
                response.headers["Strict-Transport-Security"] = sts_header

            csp_value = "; ".join(
                f"{key} {value}" for key, value in cls.CONTENT_SECURITY_POLICY.items()
            )
            response.headers["Content-Security-Policy"] = csp_value

            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["X-XSS-Protection"] = "1; mode=block"

            return response

    def __getitem__(self, key):
        return getattr(self, key)
