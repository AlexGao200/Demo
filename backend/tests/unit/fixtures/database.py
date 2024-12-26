import os
import time
import pytest
from loguru import logger
from mongoengine import connect, disconnect_all
from flask_mongoengine import MongoEngine
from models.user import User
from models.registration_session import RegistrationSession
from models.organization import Organization
from models.user_organization import UserOrganization
from models.invitation import Invitation, RegistrationCode
from models.pending import PendingRequest, PendingDocument
from models.action_log import ActionLog
from models.chat import Chat


def get_test_db_name() -> str:
    """
    Generate a unique database name for parallel test execution.
    Uses pytest worker ID (xdist) if available, otherwise defaults to 'test_db'

    Returns:
        str: Unique test database name
    """
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "")
    db_name = f"test_db_{worker_id}" if worker_id else "test_db"
    logger.info(f"Using test database name: {db_name}")
    return db_name


def connect_test_db(app=None, max_retries: int = 3, retry_delay: int = 1):
    """
    Establish MongoDB connection with retry logic.

    Args:
        app: Optional Flask app to configure
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Connection object on success

    Raises:
        Exception: If connection fails after max retries
    """
    db_name = get_test_db_name()
    mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://mongodb:27019/test_db")
    logger.info(f"Attempting to connect to MongoDB at {mongodb_uri}")

    # Ensure we start with a clean state
    disconnect_all()
    logger.debug("Disconnected from any existing connections")

    # Configure shorter timeouts for testing
    connection_settings = {
        "host": mongodb_uri,
        "serverSelectionTimeoutMS": 2000,  # 2 second timeout
        "db": db_name,  # Explicitly set database name
        "alias": "default",  # Explicitly set default alias
        "connect": True,  # Force connection
        "uuidRepresentation": "standard",
    }
    logger.debug(f"Connection settings: {connection_settings}")

    # If app is provided, configure it
    if app:
        logger.info("Configuring Flask app with MongoDB settings")
        app.config["MONGODB_SETTINGS"] = connection_settings
        db = MongoEngine()
        db.init_app(app)
        logger.info("Successfully initialized MongoDB with Flask app")
        return db

    # Attempt connection with retries
    retries = 0
    last_error = None

    while retries < max_retries:
        try:
            logger.info(f"Connection attempt {retries + 1}/{max_retries}")
            conn = connect(**connection_settings)

            # Verify connection by getting server info
            server_info = conn.server_info()
            logger.info(
                f"Successfully connected to MongoDB. Server info: {server_info}"
            )

            # Log database statistics
            db = conn.get_database()
            stats = db.command("dbStats")
            logger.info(f"Database statistics: {stats}")

            # Log available collections
            collections = db.list_collection_names()
            logger.info(f"Available collections: {collections}")

            return conn

        except Exception as e:
            retries += 1
            last_error = e
            if retries == max_retries:
                logger.error(
                    f"Failed to connect to MongoDB after {max_retries} attempts: {str(e)}"
                )
                raise
            logger.warning(f"Connection attempt {retries} failed: {str(e)}")
            logger.debug(f"Detailed error: {e}", exc_info=True)
            time.sleep(retry_delay)

    raise last_error


def clean_db_collections(collections_to_clean=None):
    """
    Helper function to clean specified collections.
    If no collections specified, cleans all collections except test users.

    Args:
        collections_to_clean: Optional list of collection names to clean
    """
    try:
        all_collections = {
            "registration_sessions": RegistrationSession._get_collection(),
            "organizations": Organization._get_collection(),
            "user_organizations": UserOrganization._get_collection(),
            "invitations": Invitation._get_collection(),
            "pending_requests": PendingRequest._get_collection(),
            "registration_codes": RegistrationCode._get_collection(),
            "action_logs": ActionLog._get_collection(),
            "chats": Chat._get_collection(),
            "pending_documents": PendingDocument._get_collection(),
        }

        # Determine which collections to clean
        if collections_to_clean:
            collections = {
                name: coll
                for name, coll in all_collections.items()
                if name in collections_to_clean
            }
        else:
            collections = all_collections

        logger.info(f"Starting cleanup for collections: {list(collections.keys())}")

        # Clean specified collections
        for name, collection in collections.items():
            result = collection.delete_many({})
            logger.info(f"Deleted {result.deleted_count} documents from {name}")

        # Always preserve test users
        user_collection = User._get_collection()
        result = user_collection.delete_many({"email": {"$not": {"$regex": "^test_"}}})
        logger.info(f"Deleted {result.deleted_count} non-test users")

        logger.info("Database cleanup completed successfully")

    except Exception as e:
        logger.error(f"Error cleaning collections: {str(e)}")
        logger.exception("Detailed cleanup error:")
        raise


@pytest.fixture(scope="session", autouse=True)
def setup_default_connection():
    """
    Ensure default connection is available throughout the test session.
    This fixture runs automatically and manages the database connection lifecycle.

    Yields:
        MongoDB connection object
    """
    logger.info("Setting up session-level database connection")
    disconnect_all()
    conn = connect_test_db()

    # Log session start state
    db = conn.get_database()
    collections = db.list_collection_names()
    logger.info(f"Session started with collections: {collections}")

    yield conn

    logger.info("Cleaning up session-level database connection")
    disconnect_all()
    logger.info("Database session cleanup completed")


@pytest.fixture(autouse=True)
def clean_collections(request):
    """
    Clean only the collections needed for the current test module.
    Uses test module name to determine which collections to clean.
    """
    yield

    # Get the test module name
    module_name = request.module.__name__.lower()

    # Determine which collections to clean based on the test module
    collections_to_clean = []
    if "user" in module_name:
        collections_to_clean = ["user_organizations"]
    elif "organization" in module_name:
        collections_to_clean = ["organizations", "user_organizations", "invitations"]
    elif "auth" in module_name:
        collections_to_clean = ["registration_sessions"]
    elif "chat" in module_name:
        collections_to_clean = ["chats"]

    logger.info("Running post-test collection cleanup")
    clean_db_collections(collections_to_clean)


# Export all needed items
__all__ = [
    "get_test_db_name",
    "connect_test_db",
    "clean_db_collections",
    "setup_default_connection",
    "clean_collections",
]
