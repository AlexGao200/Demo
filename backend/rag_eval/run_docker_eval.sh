#!/bin/bash

# Exit on error, undefined variables, and pipe failures
set -euo pipefail

# Get the absolute path to the project root (two levels up from script)
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"

cd "${ROOT_DIR}"

# Default values
STRATEGIES=""
MODELS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --strategies)
            shift
            STRATEGIES="$1"
            shift
            ;;
        --models)
            shift
            MODELS="$1"
            shift
            ;;
        --help)
            echo "Usage: $0 [--strategies 'text_only_segmentation_cohere images_only_segmentation_cohere interleaved_segmentation_cohere'] [--models 'anthropic groq hyperbolic']"
            echo ""
            echo "Options:"
            echo "  --strategies   Space-separated list of strategies to evaluate"
            echo "                 Valid values: text_only_segmentation_cohere images_only_segmentation_cohere interleaved_segmentation_cohere text_only_voyage images_only_voyage interleaved_voyage"
            echo "  --models       Space-separated list of models to evaluate"
            echo "                 Valid values: anthropic groq hyperbolic"
            echo ""
            echo "Examples:"
            echo "  $0 --strategies 'text_only_segmentation_cohere images_only_segmentation_cohere' --models 'anthropic groq'"
            echo "  $0 --strategies 'text_only_segmentation_cohere'"
            echo "  $0 --models 'anthropic'"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate strategies if provided
if [ -n "$STRATEGIES" ]; then
    # Convert string to array for validation
    IFS=' ' read -r -a strategy_array <<< "$STRATEGIES"
    for strategy in "${strategy_array[@]}"; do
        case $strategy in
            text_only_segmentation_cohere|images_only_segmentation_cohere|interleaved_segmentation_cohere|text_only_voyage|images_only_voyage|interleaved_voyage)
                ;;
            *)
                echo "❌ Invalid strategy: $strategy"
                echo "Valid strategies are: text_only_segmentation_cohere images_only_segmentation_cohere interleaved_segmentation_cohere text_only_voyage images_only_voyage interleaved_voyage"
                exit 1
                ;;
        esac
    done
fi

# Validate models if provided
if [ -n "$MODELS" ]; then
    # Convert string to array for validation
    IFS=' ' read -r -a model_array <<< "$MODELS"
    for model in "${model_array[@]}"; do
        case $model in
            anthropic|groq|hyperbolic)
                ;;
            *)
                echo "❌ Invalid model: $model"
                echo "Valid models are: anthropic groq hyperbolic"
                exit 1
                ;;
        esac
    done
fi

echo "🚀 Starting RAG evaluation suite..."
if [ -n "$STRATEGIES" ]; then
    echo "Strategies: $STRATEGIES"
else
    echo "Strategies: all"
fi
if [ -n "$MODELS" ]; then
    echo "Models: $MODELS"
else
    echo "Models: all"
fi

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up any previous failed runs
echo "🧹 Cleaning up previous containers..."
docker-compose -f docker-compose.rag-eval.yml down

# Export variables for docker-compose
export RAG_EVAL_STRATEGIES="$STRATEGIES"
export RAG_EVAL_MODELS="$MODELS"

# Run the evaluation suite
echo "📊 Running evaluations..."
if docker-compose -f docker-compose.rag-eval.yml up --build --abort-on-container-exit; then
    echo "✅ Evaluation completed successfully!"
    exit_code=0
else
    echo "❌ Evaluation failed. Check the logs above for details."
    exit_code=1
fi

# Clean up
echo "🧹 Cleaning up containers..."
docker-compose -f docker-compose.rag-eval.yml down

exit ${exit_code}
