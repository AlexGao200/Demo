import anthropic
import atexit
import os
import sys
import time
from datetime import datetime, timezone
import cohere
import voyageai
import voyageai.client_async
from factories.embedding_provider_factory import EmbeddingProviderFactory
import nest_asyncio
import stripe
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, session, make_response
from flask_mail import Mail
from flask_mongoengine import MongoEngine
from groq import AsyncGroq, Groq
from loguru import logger
from models.chat import Chat
from services.chat_service import ChatService
from services.embedding_service import EmbeddingModel
from services.llm_service import LLM
from services.mongodb_service import connect_db
from services.stripe_service import StripeService
from services.document_ingestion_service import DocumentProcessor
from services.elasticsearch_service import (
    VectorStore,
    create_elasticsearch_client_with_retries,
)
from services.rag import ChatPDF
from services.s3_service import S3Service
from treeseg.configs import treeseg_configs
from models.user import User

from services.email_service import EmailService
from services.user_service import UserService
from blueprints.auth_routes import create_auth_blueprint
from blueprints.chat_routes import create_chat_blueprint
from blueprints.organization_routes import create_organization_blueprint
from blueprints.misc_routes import create_misc_blueprint
from blueprints.user_routes import create_user_blueprint
from blueprints.file_routes import create_file_blueprint
from blueprints.filter_routes import create_filter_blueprint
from blueprints.subscription_routes import create_subscriptions_blueprint
from blueprints.doc_petition_routes import create_petition_blueprint
from services.auth_service import AuthService
from services.index_service import IndexService, VectorStoreAdapter
from models.index_registry import IndexRegistry
from services.organization_service import OrganizationService

from services.file_service import FileService

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import openai
from factories.llm_provider_factory import LLMProviderFactory

from services.embedding_strategies import CohereEmbeddingStrategy
from services.document_processing_strategies import SegmentationStrategy


def get_config_class():
    """
    Determine which configuration class to use based on environment.
    """
    env = os.getenv("FLASK_ENV", "development")
    logger.info(f"App config is: {env}")
    if env == "development":
        from config.development import DevelopmentConfig

        return DevelopmentConfig
    elif env == "production":
        from config.production import ProductionConfig

        return ProductionConfig
    elif env == "testing":
        from config.test import TestConfig

        return TestConfig
    else:
        raise ValueError(f"Invalid FLASK_ENV: {env}")


def create_app(config_object=None):
    """
    Application factory pattern.
    Args:
        config_object: Configuration class to use. If None, determines from environment.
    """
    app = Flask(__name__)

    # Load environment-specific config
    if config_object is None:
        config_object = get_config_class()

    # Apply configuration
    app.config.from_object(config_object)

    # Configure AWS credentials if running in EKS
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        # IRSA will automatically provide credentials
        logger.info("Running in Kubernetes, using IRSA for AWS credentials")

    # Clean up ALLOWED_ORIGINS
    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000,https://acaceta.com,https://www.acaceta.com",
        ).split(",")
        if origin.strip()
    ]

    def normalize_origin(origin):
        """Normalize origin by removing 'www.' if present"""
        return origin.replace("www.", "")

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            origin = request.headers.get("Origin")
            normalized_request_origin = normalize_origin(origin) if origin else None

            # Check if the normalized origin matches any of our allowed origins
            is_allowed = any(
                normalize_origin(allowed_origin) == normalized_request_origin
                for allowed_origin in ALLOWED_ORIGINS
            )

            if is_allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, DELETE, OPTIONS"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, X-Requested-With"
                )
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Max-Age"] = "3600"
            return response

    @app.after_request
    def after_request(response):
        origin = request.headers.get("Origin")
        if origin:
            normalized_request_origin = normalize_origin(origin)
            is_allowed = any(
                normalize_origin(allowed_origin) == normalized_request_origin
                for allowed_origin in ALLOWED_ORIGINS
            )

            if is_allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Expose-Headers"] = (
                    "Content-Type, Authorization"
                )

        # Prevent Flask from overwriting the CORS headers
        if not response.headers.get("Access-Control-Allow-Credentials"):
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response

    nest_asyncio.apply()

    # Initialize rate limiter with MongoDB connection parameters in URI
    mongodb_uri = config_object.MONGODB_URI
    if "?" in mongodb_uri:
        mongodb_uri += "&"
    else:
        mongodb_uri += "?"
    mongodb_uri += (
        "serverSelectionTimeoutMS=30000&connectTimeoutMS=30000&socketTimeoutMS=30000"
    )

    limiter = Limiter(
        get_remote_address,
        app=app,
        storage_uri=mongodb_uri,
        strategy="fixed-window",
    )

    # Initialize services with AWS credentials management
    stripe_client = stripe
    stripe_client.api_key = config_object.STRIPE_SECRET_KEY
    stripe_service = StripeService(stripe_client)

    s3_service = S3Service()

    logger.info("Initializing RAG system...")

    # Initialize LLM providers with clear sync/async designation
    llm_providers = {
        "groq": LLM(
            LLMProviderFactory.create_provider(
                "groq",
                sync_client=Groq(api_key=config_object.GROQ_API_KEY),
                async_client=AsyncGroq(api_key=config_object.GROQ_API_KEY),
            ),
            system_prompts="You are a helpful assistant.",
        ),
        "hyperbolic": LLM(
            LLMProviderFactory.create_provider(
                "openai",
                sync_client=openai.OpenAI(
                    base_url="https://api.hyperbolic.xyz/v1",
                    api_key=config_object.HYPERBOLIC_API_KEY,
                ),
                async_client=openai.AsyncOpenAI(
                    base_url="https://api.hyperbolic.xyz/v1",
                    api_key=config_object.HYPERBOLIC_API_KEY,
                ),
            ),
            system_prompts="You are a helpful assistant.",
        ),
        "anthropic": LLM(
            LLMProviderFactory.create_provider(
                "anthropic",
                sync_client=anthropic.Anthropic(
                    api_key=config_object.ANTHROPIC_API_KEY
                ),
                async_client=anthropic.AsyncAnthropic(
                    api_key=config_object.ANTHROPIC_API_KEY
                ),
            ),
            system_prompts="You are a helpful assistant.",
        ),
    }

    embeddings_providers = {
        "cohere": EmbeddingModel(
            EmbeddingProviderFactory.create_provider(
                "cohere",
                sync_client=cohere.ClientV2(api_key=config_object.COHERE_API_KEY),
                async_client=cohere.AsyncClientV2(api_key=config_object.COHERE_API_KEY),
            )
        ),
        "voyage": EmbeddingModel(
            EmbeddingProviderFactory.create_provider(
                "voyage",
                sync_client=voyageai.Client(api_key=config_object.VOYAGE_API_KEY),
                async_client=voyageai.AsyncClient(api_key=config_object.VOYAGE_API_KEY),
            )
        ),
    }

    selected_config = treeseg_configs["augmend"]
    prompt = app.config["RAG_GENERATION_PROMPT"]

    embedding_strategy = CohereEmbeddingStrategy(
        embeddings_providers=embeddings_providers
    )

    # Initialize processing strategy with treeseg config
    processing_strategy = SegmentationStrategy(
        treeseg_configs=selected_config, embeddings_providers=embeddings_providers
    )

    elasticsearch_client = create_elasticsearch_client_with_retries(
        host=config_object.ELASTICSEARCH_HOST,
        port=config_object.ELASTICSEARCH_PORT,
        username=config_object.ELASTICSEARCH_USER,
        password=config_object.ELASTICSEARCH_PASSWORD,
    )
    try:
        health = elasticsearch_client.cluster.health()
        logger.info(f"Elasticsearch cluster health: {health}")
    except Exception as e:
        logger.error(f"Failed to check Elasticsearch health: {e}")

    with app.app_context():
        # Initialize core services
        vector_store = VectorStore(
            elasticsearch_client,
            embeddings_providers=embeddings_providers,
            dims=config_object.DEFAULT_EMBEDDING_DIMS,
        )

        # Initialize IndexService with both required dependencies
        vector_store_adapter = VectorStoreAdapter(vector_store)
        index_service = IndexService(
            index_operations=vector_store_adapter, registry_operations=IndexRegistry
        )

        # Initialize UserService with IndexService and StripeService dependencies
        user_service = UserService(
            index_service=index_service, stripe_service=stripe_service
        )

        cohere_client = cohere.ClientV2(api_key=config_object.COHERE_API_KEY)
        # Initialize other services
        chat_pdf = ChatPDF(
            llm_providers=llm_providers,
            prompt=prompt,
            vector_store=vector_store,
            s3_service=s3_service,
            reranker=cohere_client,
            dims=config_object.DEFAULT_EMBEDDING_DIMS,
        )

        document_processor = DocumentProcessor(
            llm_providers=llm_providers,
            vector_store=vector_store,
            dims=config_object.DEFAULT_EMBEDDING_DIMS,
            processing_strategy=processing_strategy,
            embedding_strategy=embedding_strategy,
        )

        chat_service = ChatService(chat_pdf)
        email_service = EmailService(Mail(app))
        file_service = FileService(
            s3_service, document_processor, elasticsearch_client=elasticsearch_client
        )

        # Initialize AuthService with UserService dependency
        auth_service = AuthService(
            email_service=email_service,
            secret_key=app.config["SECRET_KEY"],
            user_service=user_service,
        )

        organization_service = OrganizationService(index_service=index_service)

        # Create a service registry
        app.extensions["services"] = {
            "index_service": index_service,
            "user_service": user_service,
            "chat_service": chat_service,
            "email_service": email_service,
            "file_service": file_service,
            "auth_service": auth_service,
            "organization_service": organization_service,
        }

    # MongoDB setup
    with app.app_context():
        db = MongoEngine()
        logger.remove(0)
        logger.add(sys.stderr, level="INFO")
        connect_db(app, db)

    # Register blueprints with explicitly injected services
    app.register_blueprint(
        create_organization_blueprint(
            app.extensions["services"]["email_service"],
            app.extensions["services"]["organization_service"],
        )
    )
    app.register_blueprint(
        create_auth_blueprint(
            app.extensions["services"]["auth_service"],
            app.extensions["services"]["email_service"],
            app.extensions["services"]["organization_service"],
            app.extensions["services"]["user_service"],
        )
    )
    app.register_blueprint(
        create_chat_blueprint(
            app.extensions["services"]["chat_service"],
            limiter,
            app.extensions["services"]["email_service"],
        )
    )
    app.register_blueprint(
        create_misc_blueprint(app.extensions["services"]["email_service"])
    )
    app.register_blueprint(create_filter_blueprint())
    app.register_blueprint(
        create_user_blueprint(
            limiter,
            app.extensions["services"]["user_service"],
            app.extensions["services"]["organization_service"],
        )
    )
    app.register_blueprint(
        create_file_blueprint(
            chat_pdf, app.extensions["services"]["file_service"], limiter
        )
    )
    app.register_blueprint(
        create_petition_blueprint(
            chat_pdf,
            app.extensions["services"]["email_service"],
            app.extensions["services"]["file_service"],
        )
    )
    app.register_blueprint(create_subscriptions_blueprint(stripe_service))

    # Scheduled tasks
    def remove_old_tmp_files():
        tmp_dir = app.config["TMP_DIR"]
        if os.path.exists(tmp_dir):
            now = time.time()
            for filename in os.listdir(tmp_dir):
                file_path = os.path.join(tmp_dir, filename)
                if os.stat(file_path).st_mtime < now - 86400:
                    os.remove(file_path)
                    logger.info(f"Removed old temporary file: {file_path}")

    def cleanup_guest_data():
        """Clean up expired guest sessions and their associated data"""
        try:
            current_time = datetime.now(timezone.utc)

            # Clean up expired guest chats
            expired_chats = Chat.objects(
                is_guest_chat=True, expires_at__lt=current_time
            )

            if expired_chats:
                chat_count = expired_chats.count()
                expired_chats.delete()
                logger.info(f"Cleaned up {chat_count} expired guest chats")

            # Clean up expired guest users
            expired_users = User.objects(
                is_guest=True, session_expires_at__lt=current_time
            )

            if expired_users:
                user_count = expired_users.count()
                expired_users.delete()
                logger.info(f"Cleaned up {user_count} expired guest users")

        except Exception as e:
            logger.error(f"Failed to cleanup guest data: {str(e)}")

    # Initialize scheduler
    scheduler = BackgroundScheduler()

    # Add jobs to scheduler
    scheduler.add_job(func=remove_old_tmp_files, trigger="interval", hours=1)
    scheduler.add_job(
        func=cleanup_guest_data, trigger="interval", minutes=30
    )  # Run every 30 minutes

    # Start scheduler
    scheduler.start()

    # Register shutdown
    atexit.register(lambda: scheduler.shutdown())

    @app.after_request
    def log_response_headers(response):
        logger.info("Response headers:")
        for header, value in response.headers:
            logger.info(f"{header}: {value}")
        return response

    @app.before_request
    def check_temp_indices():
        """Remove expired temporary indices from Elasticsearch and the session."""
        current_time = datetime.now(timezone.utc)
        for temp_index, info in list(session.items()):
            if "expires_at" in info and current_time > datetime.fromisoformat(
                info["expires_at"]
            ):
                elasticsearch_client.indices.delete(index=temp_index, ignore=[400, 404])
                session.pop(temp_index, None)

    return app
