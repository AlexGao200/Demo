#!/bin/bash

# Function to copy environment files
setup_env() {
    if [ -f ".env" ]; then
        cp .env backend/.env
    fi
    if [ -f ".env.test" ]; then
        cp .env.test backend/.env.test
    fi
}

# Function to clean up environment files
cleanup_env() {
    rm -f backend/.env backend/.env.test
}

# Function to clean up containers
cleanup_containers() {
    echo "Cleaning up existing containers..."
    docker compose -f docker-compose.test.yml down -v
}

# Set up environment and clean up any existing containers
setup_env
cleanup_containers

# Start test environment and wait for services
echo "Starting test environment..."
docker compose -f docker-compose.test.yml up -d --build

# Wait for MongoDB to be ready
echo "Waiting for MongoDB..."
until docker compose -f docker-compose.test.yml exec -T mongo mongosh --eval "db.runCommand('ping').ok" > /dev/null 2>&1; do
    sleep 2
done

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch..."
until curl -s http://localhost:9201 > /dev/null; do
    sleep 2
done

# Run the tests
echo "Running tests..."
docker compose -f docker-compose.test.yml exec backend pytest tests/unit/services -v

# Store the exit code
exit_code=$?

# Clean up
echo "Cleaning up..."
docker compose -f docker-compose.test.yml down -v
cleanup_env

# Return the test exit code
exit $exit_code
