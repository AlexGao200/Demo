# acaceta


If docker out of volume, run:

docker system prune -a
docker volume prune




Inspect docker disk space usage:

docker system df

Remove all volumes:

#!/bin/bash

# Stop all running containers
docker stop $(docker ps -aq)

# Remove all containers
docker rm $(docker ps -aq)

# Remove all volumes
docker volume rm $(docker volume ls -q)

# Prune the Docker system
docker system prune -a -f --volumes

# Rebuild and restart containers
docker-compose up --build




# Commands to manually test opensearch:

1. Create index:

curl -X PUT "localhost:9200/test_vectors" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "index": {
      "knn": true
    }
  },
  "mappings": {
    "properties": {
      "vector": {
        "type": "knn_vector",
        "dimension": 3
      }
    }
  }
}'

2. Insert test vectors


curl -X POST "localhost:9200/test_vectors/_doc/1" -H 'Content-Type: application/json' -d'
{
  "vector": [1.0, 2.0, 3.0]
}'

curl -X POST "localhost:9200/test_vectors/_doc/2" -H 'Content-Type: application/json' -d'
{
  "vector": [4.0, 5.0, 6.0]
}'

curl -X POST "localhost:9200/test_vectors/_doc/3" -H 'Content-Type: application/json' -d'
{
  "vector": [7.0, 8.0, 9.0]
}'

3.

Query a vector:

curl -X POST "localhost:9200/test_vectors/_search" -H 'Content-Type: application/json' -d'
{
  "size": 3,
  "query": {
    "knn": {
      "field": "vector",
      "query_vector": [2.0, 3.0, 4.0],
      "k": 3
    }
  }
}'


# Notes: Can change the vector to one of the test vectors. I changed the dimension of the index/vectors to 3
# ease of execution.




### Example manual opensearch commands using lucene/cosine similarity:

1. Create index:

Example command:

curl -X PUT "http://localhost:9200/test_vectors" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "index": {
      "knn": true
    }
  },
  "mappings": {
    "properties": {
      "embedding": {
        "type": "knn_vector",
        "dimension": 3
      },
      "metadata": {
        "properties": {
          "id": {
            "type": "long"
          },
          "description": {
            "type": "text"
          }
        }
      }
    }
  }
}'


2.

Insert embeddings generated from pdf retrieved from s3:

Example command:


curl -X POST "http://localhost:9200/test_vectors/_doc/1" -H 'Content-Type: application/json' -d'
{
  "embedding": [0.1, 0.2, 0.3],
  "metadata": {
    "id": 1,
    "description": "Test vector 1"
  }
}'

curl -X POST "http://localhost:9200/test_vectors/_doc/2" -H 'Content-Type: application/json' -d'
{
  "embedding": [0.4, 0.5, 0.6],
  "metadata": {
    "id": 2,
    "description": "Test vector 2"
  }
}'

curl -X POST "http://localhost:9200/test_vectors/_doc/3" -H 'Content-Type: application/json' -d'
{
  "embedding": [0.7, 0.8, 0.9],
  "metadata": {
    "id": 3,
    "description": "Test vector 3"
  }
}'


3. Query the created index with the embedding generated for the query:

Example code:

curl -X POST "http://localhost:9200/test_vectors/_search" -H 'Content-Type: application/json' -d'
{
  "size": 10,
  "query": {
    "script_score": {
      "query": {
        "match_all": {}
      },
      "script": {
        "source": "cosineSimilarity(params.queryVector, doc[\"embedding\"]) + 1.0",
        "params": {
          "queryVector": [0.1, 0.2, 0.3]
        }
      }
    }
  }
}'


# Running test enviornment with override:

docker-compose -f docker-compose.yml -f docker-compose.test.yml up --build
