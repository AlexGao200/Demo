from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_mongoengine import MongoEngine
from mongoengine import disconnect_all
from loguru import logger
from unittest.mock import MagicMock
import os
import time
from datetime import datetime

from config.test import TestConfig
from services.auth_service import AuthService
from services.chat_service import ChatService
from services.email_service import EmailService
from services.file_service import FileService
from services.s3_service import S3Service
from services.rag import ChatPDF
from services.embedding_service import EmbeddingModel
from services.elasticsearch_service import (
    VectorStore,
    create_elasticsearch_client_with_retries,
)
from services.document_ingestion_service import DocumentProcessor
from services.document_processing_strategies import (
    SegmentationStrategy,
)
from services.embedding_strategies import (
    CohereEmbeddingStrategy,
)
from services.llm_service import LLM
from services.index_service import IndexService, VectorStoreAdapter
from models.index_registry import IndexRegistry
from services.user_service import UserService
from services.organization_service import OrganizationService

from blueprints.auth_routes import create_auth_blueprint
from blueprints.chat_routes import create_chat_blueprint
from blueprints.organization_routes import create_organization_blueprint
from blueprints.misc_routes import create_misc_blueprint
from blueprints.user_routes import create_user_blueprint
from blueprints.file_routes import create_file_blueprint
from blueprints.filter_routes import create_filter_blueprint
from blueprints.subscription_routes import create_subscriptions_blueprint
from blueprints.doc_petition_routes import create_petition_blueprint
from treeseg.configs import treeseg_configs
from tests.utils.provider_factory import TestProviderFactory


class IntegrationAppFactory:
    """Factory for creating Flask applications configured for integration testing."""

    @staticmethod
    def _get_test_db_name(test_name: str = None) -> str:
        """Generate unique database name for parallel testing with enhanced isolation."""
        # Get worker ID for parallel testing
        worker = os.environ.get("PYTEST_XDIST_WORKER", "")
        worker_id = f"_{worker}" if worker else ""

        # Sanitize test name (remove special characters, limit length)
        if test_name:
            # Replace special characters and spaces with underscore
            sanitized_name = "".join(c if c.isalnum() else "_" for c in test_name)
        else:
            sanitized_name = "unknown"

        timestamp = datetime.now().strftime("%y%m%d-%s")

        max_db_name_length = 63
        name_chars_allowed = max_db_name_length - len(timestamp) - len(worker_id) - 6
        sanitized_name = sanitized_name[:name_chars_allowed]

        # Add timestamp for temporal uniqueness

        # Combine all components
        return f"test{worker_id}_{sanitized_name}_{timestamp}"

    @staticmethod
    def _configure_test_db(app: Flask, test_name: str) -> MongoEngine:
        """Configure and initialize test database for Flask app."""
        # Generate unique database name
        db_name = IntegrationAppFactory._get_test_db_name(test_name)

        # Configure MongoDB settings
        app.config["MONGODB_SETTINGS"] = {
            "host": f"mongodb://mongo:27017/{db_name}",
            "db": db_name,
            "connect": False,  # Defer connection until needed
            "serverSelectionTimeoutMS": 5000,
        }

        # Initialize database with retry logic
        db = MongoEngine()
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                db.init_app(app)
                with app.app_context():
                    # Verify connection
                    db.get_db()
                logger.info(f"Connected to test database: {db_name}")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to connect to database after {max_retries} attempts"
                    )
                    raise
                logger.warning(f"DB connection attempt {attempt + 1} failed: {e}")
                time.sleep(retry_delay)
                disconnect_all()

        return db

    @staticmethod
    def create_app(
        config_object=None,
        blueprints={},
        mock_services={},
        enable_rate_limits=False,
        test_name="default",
    ):
        """
        Create a Flask application configured for integration testing.

        Args:
            config_object: Configuration class to use (defaults to TestConfig)
            blueprints: List of blueprint names to register (defaults to all)
            mock_services: Dictionary of service names to mock objects
            enable_rate_limits: Whether to enable rate limiting (defaults to False for testing)
            test_name: Name of the test for VCR cassette naming (defaults to "default")

        Returns:
            Flask application configured for testing
        """
        # Ensure clean database state
        disconnect_all()

        app = Flask(__name__)

        # Load configuration
        if config_object is None:
            config_object = TestConfig
        app.config.from_object(config_object)

        # Configure database
        IntegrationAppFactory._configure_test_db(app, test_name)

        # Initialize core services
        mail = Mail(app)
        email_service = EmailService(mail)

        # Initialize rate limiter (disabled by default for testing)
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri="memory://",
            enabled=enable_rate_limits,
        )

        # Initialize or mock services based on configuration
        services = IntegrationAppFactory._initialize_services(
            app,
            mock_services,
            email_service,
            test_name,
        )

        # Initialize IndexService and UserService
        if "index" in mock_services:
            services["index_service"] = mock_services["index"]
        else:
            vector_store_adapter = VectorStoreAdapter(services["vector_store"])
            services["index_service"] = IndexService(
                index_operations=vector_store_adapter, registry_operations=IndexRegistry
            )

        if "user" in mock_services:
            services["user_service"] = mock_services["user"]
        else:
            services["user_service"] = UserService(
                index_service=services["index_service"]
            )

        # Initialize AuthService with UserService dependency
        auth_service = AuthService(
            email_service=email_service,
            secret_key=app.config["SECRET_KEY"],
            user_service=services["user_service"],
        )

        if "organization" in mock_services:
            services["organization_service"] = mock_services["organization"]
        else:
            services["organization_service"] = OrganizationService(
                services["index_service"]
            )

        # Register requested blueprints
        IntegrationAppFactory._register_blueprints(
            app, blueprints or "all", services, auth_service, email_service, limiter
        )

        return app

    @staticmethod
    def _initialize_services(app, mock_services, email_service, test_name):
        """Initialize or mock required services based on configuration."""
        services = {}
        test_size = app.config.get("TEST_SIZE", "small")

        # S3 Service - mock for all tests due to external dependency
        if "s3" in mock_services:
            services["s3_service"] = mock_services["s3"]
        else:
            services["s3_service"] = MagicMock(spec=S3Service)

        # Elasticsearch - use real instance for medium/large tests
        if "elasticsearch" in mock_services:
            services["elasticsearch_client"] = mock_services["elasticsearch"]
        elif test_size in ["medium", "large"]:
            services["elasticsearch_client"] = create_elasticsearch_client_with_retries(
                host=app.config["ELASTICSEARCH_HOST"],
                port=app.config["ELASTICSEARCH_PORT"],
            )
        else:
            services["elasticsearch_client"] = MagicMock()

        # Initialize LLM providers with proper VCR handling
        if test_size in ["medium", "large"]:
            llm_providers = {
                "groq": TestProviderFactory.create_llm_service("groq", test_name),
                "hyperbolic": TestProviderFactory.create_llm_service(
                    "hyperbolic", test_name
                ),
                "anthropic": TestProviderFactory.create_llm_service(
                    "anthropic", test_name
                ),
            }
        else:
            # Mock LLM providers for small tests
            mock_llm = MagicMock(spec=LLM)
            mock_llm.invoke.return_value = "Mocked LLM response"
            mock_llm.ainvoke.return_value = ["Mocked", "stream", "response"]
            llm_providers = {
                "groq": mock_llm,
                "hyperbolic": mock_llm,
                "anthropic": mock_llm,
            }

        # Initialize embedding providers
        if "embedding" in mock_services:
            embeddings_providers = {
                "cohere": mock_services["embedding"],
                "voyage": mock_services["embedding"],
            }
        elif test_size in ["medium", "large"]:
            embeddings_providers = {
                "cohere": TestProviderFactory.create_embedding_provider(
                    "cohere", test_name
                ),
                "voyage": TestProviderFactory.create_embedding_provider(
                    "voyage", test_name
                ),
            }
        else:
            mock_embedding = MagicMock(spec=EmbeddingModel)
            mock_embedding.embed.return_value = [0] * app.config[
                "DEFAULT_EMBEDDING_DIMS"
            ]
            mock_embedding.async_embed = mock_embedding.embed  # Ensure async mock
            embeddings_providers = {"cohere": mock_embedding, "voyage": mock_embedding}

        # Vector Store
        if "vector_store" in mock_services:
            services["vector_store"] = mock_services["vector_store"]
        else:
            services["vector_store"] = VectorStore(
                services["elasticsearch_client"],
                embeddings_providers=embeddings_providers,
                dims=app.config["DEFAULT_EMBEDDING_DIMS"],
            )

        # Initialize embedding strategies
        cohere_strategy = CohereEmbeddingStrategy(
            embeddings_providers=embeddings_providers
        )
        # voyage_strategy = VoyageEmbeddingStrategy(
        #     embeddings_providers=embeddings_providers
        # )

        # Initialize document processing strategies
        segmentation_strategy = SegmentationStrategy(
            treeseg_configs=treeseg_configs["augmend"],
            embeddings_providers=embeddings_providers,
        )
        # voyage_doc_strategy = VoyageDocumentStrategy()

        # Chat PDF Service
        if "chat_pdf" in mock_services:
            services["chat_pdf"] = mock_services["chat_pdf"]
        else:
            services["chat_pdf"] = ChatPDF(
                llm_providers=llm_providers,
                prompt=app.config["RAG_GENERATION_PROMPT"],
                vector_store=services["vector_store"],
                s3_service=services["s3_service"],
                reranker=TestProviderFactory.create_embedding_provider(
                    test_name=test_name
                ).model  # FIXME
                if test_size in ["medium", "large"]
                else None,
                dims=app.config["DEFAULT_EMBEDDING_DIMS"],
            )

        # Document Processor
        if "document_processor" in mock_services:
            services["document_processor"] = mock_services["document_processor"]
        else:
            services["document_processor"] = DocumentProcessor(
                llm_providers=llm_providers,
                vector_store=services["vector_store"],
                dims=app.config["DEFAULT_EMBEDDING_DIMS"],
                embedding_strategy=cohere_strategy,  # Default to Cohere for text
                processing_strategy=segmentation_strategy,  # Default to segmentation
            )

        # File Service
        if "file" in mock_services:
            services["file_service"] = mock_services["file"]
        else:
            services["file_service"] = FileService(
                services["s3_service"],
                services["document_processor"],
                elasticsearch_client=services["elasticsearch_client"],
            )

        # Chat Service
        if "chat" in mock_services:
            services["chat_service"] = mock_services["chat"]
        else:
            services["chat_service"] = ChatService(services["chat_pdf"])

        return services

    @staticmethod
    def _register_blueprints(
        app, blueprints, services, auth_service, email_service, limiter
    ):
        """Register requested blueprints with the application."""
        blueprint_creators = {
            "auth": lambda: create_auth_blueprint(
                auth_service,
                email_service,
                services["organization_service"],
                services["user_service"],
            ),
            "chat": lambda: create_chat_blueprint(services["chat_service"], limiter),
            "organization": lambda: create_organization_blueprint(
                email_service, services["organization_service"]
            ),
            "misc": lambda: create_misc_blueprint(email_service),
            "user": lambda: create_user_blueprint(
                limiter, services["organization_service"], services["user_service"]
            ),
            "file": lambda: create_file_blueprint(
                services["chat_pdf"], services["file_service"], limiter
            ),
            "filter": lambda: create_filter_blueprint(),
            "subscription": lambda: create_subscriptions_blueprint(
                MagicMock()
            ),  # Mock stripe service
            "petition": lambda: create_petition_blueprint(
                services["chat_pdf"], email_service, services["file_service"]
            ),
        }

        if blueprints == "all":
            blueprints = blueprint_creators.keys()

        for blueprint_name in blueprints:
            if blueprint_name in blueprint_creators:
                try:
                    blueprint = blueprint_creators[blueprint_name]()
                    app.register_blueprint(blueprint)
                    logger.info(f"Registered blueprint: {blueprint_name}")
                except Exception as e:
                    logger.error(f"Failed to register blueprint {blueprint_name}: {e}")
            else:
                logger.warning(f"Unknown blueprint: {blueprint_name}")
