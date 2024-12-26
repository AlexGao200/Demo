import os

# Fetch Together API Key from environment variables
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Define the headers for the embedding requests
EMBEDDINGS_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOGETHER_API_KEY}",
}

# Define the embedding endpoint
EMBEDDINGS_ENDPOINT = "https://api.together.xyz/v1/embeddings"

# Configuration dictionaries for different use cases
bertseg_configs = {
    "ami": {
        "SENTENCE_COMPARISON_WINDOW": 15,
        "SMOOTHING_PASSES": 2,
        "SMOOTHING_WINDOW": 5,
        "EMBEDDINGS_HEADERS": EMBEDDINGS_HEADERS,
        "EMBEDDINGS_ENDPOINT": EMBEDDINGS_ENDPOINT,
    },
    "icsi": {
        "SENTENCE_COMPARISON_WINDOW": 15,
        "SMOOTHING_PASSES": 2,
        "SMOOTHING_WINDOW": 5,
        "EMBEDDINGS_HEADERS": EMBEDDINGS_HEADERS,
        "EMBEDDINGS_ENDPOINT": EMBEDDINGS_ENDPOINT,
    },
    "augmend": {
        "SENTENCE_COMPARISON_WINDOW": 15,
        "SMOOTHING_PASSES": 2,
        "SMOOTHING_WINDOW": 5,
        "EMBEDDINGS_HEADERS": EMBEDDINGS_HEADERS,
        "EMBEDDINGS_ENDPOINT": EMBEDDINGS_ENDPOINT,
    },
}

treeseg_configs = {
    "ami": {
        "MIN_SEGMENT_SIZE": 5,
        "MAX_SEGMENT_SIZE": 25,  # Ensure MAX_SEGMENT_SIZE is defined
        "LAMBDA_BALANCE": 0,
        "UTTERANCE_EXPANSION_WIDTH": 4,
        "EMBEDDINGS_HEADERS": EMBEDDINGS_HEADERS,
        "EMBEDDINGS_ENDPOINT": EMBEDDINGS_ENDPOINT,
    },
    "icsi": {
        "MIN_SEGMENT_SIZE": 5,
        "MAX_SEGMENT_SIZE": 25,  # Ensure MAX_SEGMENT_SIZE is defined
        "LAMBDA_BALANCE": 0,
        "UTTERANCE_EXPANSION_WIDTH": 4,
        "EMBEDDINGS_HEADERS": EMBEDDINGS_HEADERS,
        "EMBEDDINGS_ENDPOINT": EMBEDDINGS_ENDPOINT,
    },
    "augmend": {
        "MIN_SEGMENT_SIZE": 5,
        "MAX_SEGMENT_SIZE": 25,  # Adjusted as per your specific needs
        "LAMBDA_BALANCE": 0,
        "UTTERANCE_EXPANSION_WIDTH": 2,
        "EMBEDDINGS_HEADERS": EMBEDDINGS_HEADERS,
        "EMBEDDINGS_ENDPOINT": EMBEDDINGS_ENDPOINT,
    },
}
