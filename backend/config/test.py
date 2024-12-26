from environs import Env
from typing import Literal
from loguru import logger
from langchain.prompts import PromptTemplate

TestSize = Literal["small", "medium", "large"]


def load_env(test_size: TestSize) -> Env:
    """
    Load environment based on test size:
    - small: Use test defaults (no .env needed)
    - medium/large: Load .env for real API keys
    """
    env = Env()

    # Always load base test config
    env.read_env(".env.test")

    # For medium/large tests, load real API keys
    if test_size in ["medium", "large"]:
        try:
            env.read_env(".env", override=True)
        except Exception as e:
            logger.info(f"Warning: Could not load .env file for {test_size} tests: {e}")
            print(f"Warning: Could not load .env file for {test_size} tests: {e}")
            print("Tests requiring real API keys may fail")

    return env


class TestConfig:
    """Test configuration with test size awareness for proper API key handling"""

    _test_size: TestSize = "small"
    _env = load_env(_test_size)

    TESTING = True
    DEBUG = False

    # Core settings
    FLASK_ENV = _env.str("FLASK_ENV", default="testing")
    TMP_DIR = _env.str("TMP_DIR", default="/app/tmp")
    SECRET_KEY = _env.str("SECRET_KEY", default="test_secret_key")
    FRONTEND_BASE_URL = _env.str("FRONTEND_BASE_URL", default="http://localhost:3000")
    REACT_APP_BACKEND_URL = _env.str(
        "REACT_APP_BACKEND_URL", default="http://localhost:5000"
    )
    ACACETA_SUPERADMIN_PASSWORD = _env.str(
        "ACACETA_SUPERADMIN_PASSWORD", default="test_admin_password"
    )

    # Test user settings
    TEST_USER_PASSWORD = _env.str("TEST_USER_PASSWORD", default="Test123!@#")

    # Database settings
    MONGODB_URI = _env.str("MONGODB_URI", default="mongodb://mongo:27019/test_db")
    MONGODB_SETTINGS = {
        "host": MONGODB_URI,
        "serverSelectionTimeoutMS": 2000,
    }

    ELASTICSEARCH_HOST = _env.str("ELASTICSEARCH_HOST", default="elasticsearch")
    ELASTICSEARCH_PORT = _env.int("ELASTICSEARCH_PORT", default=9200)
    ELASTICSEARCH_USER = _env.str("ELASTICSEARCH_USER", default="elastic")
    ELASTICSEARCH_PASSWORD = _env.str("ELASTICSEARCH_PASSWORD", default="test_password")

    # Feature flags
    ENABLE_EXTERNAL_SERVICES = _env.bool("ENABLE_EXTERNAL_SERVICES", default=False)

    # AWS Configuration
    AWS_ACCESS_KEY_ID = _env.str("AWS_ACCESS_KEY_ID", default="test_key")
    AWS_SECRET_ACCESS_KEY = _env.str("AWS_SECRET_ACCESS_KEY", default="test_secret")
    AWS_REGION = _env.str("AWS_REGION", default="us-east-1")
    AWS_S3_BUCKET_NAME = _env.str("AWS_S3_BUCKET_NAME", default="test-bucket")
    AWS_S3_HIGHLIGHTED_BUCKET_NAME = _env.str(
        "AWS_S3_HIGHLIGHTED_BUCKET_NAME", default="test-highlighted-bucket"
    )
    AWS_S3_THUMBNAIL_BUCKET_NAME = _env.str(
        "AWS_S3_THUMBNAIL_BUCKET_NAME", default="test-thumbnail-bucket"
    )
    AWS_S3_PETITION_BUCKET_NAME = _env.str(
        "AWS_S3_PETITION_BUCKET_NAME", default="test-petition-bucket"
    )

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

    @property
    def TEST_SIZE(self) -> TestSize:
        """Get current test size"""
        return self._test_size

    @TEST_SIZE.setter
    def TEST_SIZE(self, size: TestSize):
        """Set test size and reload environment if needed"""
        if size not in ["small", "medium", "large"]:
            raise ValueError("Test size must be 'small', 'medium', or 'large'")

        # Only reload env if size category changes
        if (self._test_size == "small" and size in ["medium", "large"]) or (
            self._test_size in ["medium", "large"] and size == "small"
        ):
            self._env = load_env(size)

        self._test_size = size

    # API keys with test size awareness
    @property
    def ANTHROPIC_API_KEY(self) -> str:
        """Get Anthropic API key based on test size"""
        return (
            self._env.str("ANTHROPIC_API_KEY")
            if self._test_size in ["medium", "large"]
            else "test_key"
        )

    @property
    def GROQ_API_KEY(self) -> str:
        """Get Groq API key based on test size"""
        return (
            self._env.str("GROQ_API_KEY")
            if self._test_size in ["medium", "large"]
            else "test_key"
        )

    @property
    def COHERE_API_KEY(self) -> str:
        """Get Cohere API key based on test size"""
        return (
            self._env.str("COHERE_API_KEY")
            if self._test_size in ["medium", "large"]
            else "test_key"
        )

    @property
    def VOYAGE_API_KEY(self) -> str:
        """Get Cohere API key based on test size"""
        return (
            self._env.str("VOYAGE_API_KEY")
            if self._test_size in ["medium", "large"]
            else "test_key"
        )

    @property
    def OPENAI_API_KEY(self) -> str:
        """Get OpenAI API key based on test size"""
        return (
            self._env.str("OPENAI_API_KEY")
            if self._test_size in ["medium", "large"]
            else "test_key"
        )

    @property
    def TOGETHER_API_KEY(self) -> str:
        """Get Together API key based on test size"""
        return (
            self._env.str("TOGETHER_API_KEY")
            if self._test_size in ["medium", "large"]
            else "test_key"
        )

    @property
    def HYPERBOLIC_API_KEY(self) -> str:
        """Get Hyperbolic API key based on test size"""
        return (
            self._env.str("HYPERBOLIC_API_KEY")
            if self._test_size in ["medium", "large"]
            else "test_key"
        )

    # Stripe keys with test size awareness
    @property
    def STRIPE_SECRET_KEY(self) -> str:
        """Get Stripe secret key based on test size"""
        return (
            self._env.str("STRIPE_SECRET_KEY")
            if self._test_size in ["medium", "large"]
            else "sk_test"
        )

    @property
    def STRIPE_WEBHOOK_SECRET(self) -> str:
        """Get Stripe webhook secret based on test size"""
        return (
            self._env.str("STRIPE_WEBHOOK_SECRET")
            if self._test_size in ["medium", "large"]
            else "test_webhook_secret"
        )

    @property
    def REACT_APP_STRIPE_PUBLIC_KEY(self) -> str:
        """Get Stripe public key based on test size"""
        return (
            self._env.str("REACT_APP_STRIPE_PUBLIC_KEY")
            if self._test_size in ["medium", "large"]
            else "pk_test"
        )

    # Mail settings
    MAIL_SUPPRESS_SEND = _env.bool("MAIL_SUPPRESS_SEND", default=True)
    MAIL_SERVER = _env.str("MAIL_SERVER", default="smtp.test.com")
    MAIL_PORT = _env.int("MAIL_PORT", default=587)
    MAIL_USE_TLS = _env.bool("MAIL_USE_TLS", default=True)
    MAIL_USE_SSL = _env.bool("MAIL_USE_SSL", default=False)
    MAIL_USERNAME = _env.str("MAIL_USERNAME", default="test@test.com")
    MAIL_PASSWORD = _env.str("MAIL_PASSWORD", default="test_password")
    MAIL_DEFAULT_SENDER = _env.str("MAIL_DEFAULT_SENDER", default="test@test.com")

    # Model config
    DEFAULT_EMBEDDING_DIMS = _env.int("DEFAULT_EMBEDDING_DIMS", default=1024)

    # CORS
    ALLOWED_ORIGINS = _env.list(
        "ALLOWED_ORIGINS",
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://frontend:3000",
        ],
    )

    # Testing related
    DOC_PETITION_INDEX = "test_petition_index"

    def __init__(self):
        """Initialize test-specific settings"""
        self.PRESERVE_CONTEXT_ON_EXCEPTION = self._env.bool(
            "PRESERVE_CONTEXT_ON_EXCEPTION", default=False
        )
        self.WTF_CSRF_ENABLED = self._env.bool("WTF_CSRF_ENABLED", default=False)

    @classmethod
    def is_using_real_apis(cls) -> bool:
        """Check if the current configuration uses real API keys"""
        return cls._test_size in ["medium", "large"]
