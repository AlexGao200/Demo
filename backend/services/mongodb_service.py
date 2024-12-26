import os
import time
from loguru import logger
from pymongo.errors import ServerSelectionTimeoutError
from flask_mongoengine import MongoEngine
from mongoengine import disconnect_all


def connect_db(app, db: MongoEngine, max_retries=5, retry_delay=10):
    """
    Initialize MongoDB connection with retry logic.

    Args:
        app: Flask application instance
        db: MongoEngine instance
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds

    Raises:
        ServerSelectionTimeoutError: If connection fails after max retries
    """
    # Always disconnect existing connections first
    disconnect_all()

    mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://mongo:27017/documents")
    logger.info(
        f"Attempting to connect to MongoDB at: {mongodb_uri.split('@')[-1]}"
    )  # Log only the host part, not credentials

    # Configure MongoDB settings with increased timeouts for cloud connections
    app.config["MONGODB_SETTINGS"] = {
        "host": mongodb_uri,
        "connect": False,  # Defer connection until init_app
        "serverSelectionTimeoutMS": 30000,  # 30 second timeout
        "connectTimeoutMS": 30000,
        "socketTimeoutMS": 30000,
        "maxPoolSize": 100,
        "minPoolSize": 10,
        "retryWrites": True,
        "retryReads": True,
        "w": "majority",  # Write concern for better reliability
    }

    retries = 0
    while retries < max_retries:
        try:
            db.init_app(app)
            # Test the connection
            with app.app_context():
                db.get_db()
            logger.info("MongoDB connected successfully")
            return
        except ServerSelectionTimeoutError as e:
            retries += 1
            logger.warning(
                f"Attempt {retries}/{max_retries}: MongoDB connection failed with error: {e}. "
                f"Retrying in {retry_delay} seconds...\n"
                f"Connection details: Host={mongodb_uri.split('@')[-1]}, "
                f"Timeout={app.config['MONGODB_SETTINGS']['serverSelectionTimeoutMS']}ms"
            )
            time.sleep(retry_delay)
            # Ensure clean state before retry
            disconnect_all()
        except ValueError as e:
            if "Extension already initialized" in str(e):
                logger.warning("MongoEngine extension already initialized")
                return
            logger.error(f"ValueError during MongoDB connection: {e}")
            raise
        except Exception as e:
            retries += 1
            logger.error(
                f"Attempt {retries}/{max_retries}: Unexpected error during MongoDB connection: {str(e)}. "
                f"Error type: {type(e).__name__}. Retrying in {retry_delay} seconds..."
            )
            time.sleep(retry_delay)
            # Ensure clean state before retry
            disconnect_all()

    error_msg = (
        f"MongoDB connection failed after {max_retries} attempts. "
        f"Last known connection details: Host={mongodb_uri.split('@')[-1]}, "
        f"Timeout={app.config['MONGODB_SETTINGS']['serverSelectionTimeoutMS']}ms"
    )
    logger.error(error_msg)
    raise ServerSelectionTimeoutError(error_msg)
