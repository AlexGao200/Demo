import os
import mongoengine

# Set the FLASK_ENV to 'testing' for all test files
os.environ["FLASK_ENV"] = "testing"

# Set the TESTING flag
os.environ["TESTING"] = "true"

# Set the MongoDB URI for the test database
TEST_MONGO_URI = "mongodb://localhost:27018/test"

# Connect to the test MongoDB instance
mongoengine.connect(host=TEST_MONGO_URI)


# Optionally, disconnect after testing
def disconnect_mongo():
    mongoengine.disconnect()


# You can ensure the connection is properly cleaned up after tests by calling this in your test teardown or exit
