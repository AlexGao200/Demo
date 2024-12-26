#!/bin/bash

# Function to check if a container is running
container_running() {
    docker inspect -f '{{.State.Running}}' $1 2>/dev/null
}

# Reset MongoDB
if [ "$(container_running acaceta-mongo-1)" = "true" ]; then
    echo "Resetting MongoDB..."
    docker exec acaceta-mongo-1 mongosh --eval "db.dropDatabase()" documents
    echo "MongoDB databases dropped."
    docker exec acaceta-mongo-1 rm -rf /data/db/*
    echo "MongoDB data directory cleared."
else
    echo "MongoDB container is not running."
fi

# Reset Elasticsearch
if [ "$(container_running elasticsearch)" = "true" ]; then
    echo "Resetting Elasticsearch..."
    # Delete all indices
    docker exec elasticsearch curl -X GET "http://localhost:9200/_cat/indices?h=index" | while read index; do
        docker exec elasticsearch curl -X DELETE "http://localhost:9200/$index"
    done
    echo "Elasticsearch indices deleted."
    # Clear data directory
    docker exec elasticsearch sh -c 'rm -rf /usr/share/elasticsearch/data/* && mkdir -p /usr/share/elasticsearch/data'
    echo "Elasticsearch data directory cleared."
    # Restart Elasticsearch to ensure clean state
else
    echo "Elasticsearch container is not running."
fi
cd ~/code/acaceta && docker-compose down

echo "Reset operation completed. Restarting Docker network."

docker-compose up --build
