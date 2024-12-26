#!/bin/bash

# Run the script from the backend directory
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Add the backend directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Starting evaluation script..."
poetry run python rag_eval/run_evals.py
