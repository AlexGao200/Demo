import sys
import os
import asyncio
from enum import Enum
from typing import List, Optional, Dict
from rag_eval.llm_setup import setup_environment
from rag_eval.generation_eval import run_generation_eval, GenerationStrategy
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")


class ModelType(str, Enum):
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    HYPERBOLIC = "hyperbolic"


class StrategyType(str, Enum):
    TEXT_ONLY_COHERE = "text_only_segmentation_cohere"
    IMAGES_ONLY_COHERE = "images_only_segmentation_cohere"
    INTERLEAVED_COHERE = "interleaved_segmentation_cohere"
    TEXT_ONLY_VOYAGE = "text_only_voyage"
    IMAGES_ONLY_VOYAGE = "images_only_voyage"
    INTERLEAVED_VOYAGE = "interleaved_voyage"


# Mapping from strategy names to GenerationStrategy enums
STRATEGY_TO_GENERATION_MAP: Dict[str, GenerationStrategy] = {
    StrategyType.TEXT_ONLY_COHERE: GenerationStrategy.TEXT_ONLY,
    StrategyType.IMAGES_ONLY_COHERE: GenerationStrategy.IMAGES_ONLY,
    StrategyType.INTERLEAVED_COHERE: GenerationStrategy.INTERLEAVED,
    StrategyType.TEXT_ONLY_VOYAGE: GenerationStrategy.TEXT_ONLY,
    StrategyType.IMAGES_ONLY_VOYAGE: GenerationStrategy.IMAGES_ONLY,
    StrategyType.INTERLEAVED_VOYAGE: GenerationStrategy.INTERLEAVED,
}


def parse_env_config() -> tuple[Optional[List[str]], Optional[List[str]]]:
    """Parse configuration from environment variables."""
    strategies_str = os.getenv("RAG_EVAL_STRATEGIES", "")
    models_str = os.getenv("RAG_EVAL_MODELS", "")

    # Parse strategies
    strategies = [s.strip() for s in strategies_str.split()] if strategies_str else None
    if strategies:
        valid_strategies = set(s.value for s in StrategyType)
        invalid_strategies = [s for s in strategies if s not in valid_strategies]
        if invalid_strategies:
            logger.error(f"Invalid strategies found: {invalid_strategies}")
            logger.error(f"Valid strategies are: {valid_strategies}")
            sys.exit(1)

    # Parse models
    models = [m.strip() for m in models_str.split()] if models_str else None
    if models:
        valid_models = set(m.value for m in ModelType)
        invalid_models = [m for m in models if m not in valid_models]
        if invalid_models:
            logger.error(f"Invalid models found: {invalid_models}")
            logger.error(f"Valid models are: {valid_models}")
            sys.exit(1)

    return strategies, models


def filter_clients(
    clients: List[any], selected_models: Optional[List[str]]
) -> List[any]:
    """Filter LLM clients based on selected models."""
    if not selected_models:
        return clients

    filtered_clients = []
    for client in clients:
        model_name = client.get_model_name().lower()
        if any(model.lower() in model_name for model in selected_models):
            filtered_clients.append(client)

    return filtered_clients


def filter_strategies(
    selected_strategies: Optional[List[str]],
) -> List[GenerationStrategy]:
    """Convert strategy strings to GenerationStrategy enums."""
    if not selected_strategies:
        # Return all unique generation strategies
        return list(set(STRATEGY_TO_GENERATION_MAP.values()))

    # Convert selected strategy names to their corresponding GenerationStrategy enums
    return [STRATEGY_TO_GENERATION_MAP[s] for s in selected_strategies]


async def run_evaluations():
    """Run RAG evaluations with specified configurations."""
    try:
        # Parse configuration from environment
        selected_strategies, selected_models = parse_env_config()

        logger.info("Starting RAG Evaluation Suite...")
        logger.info(f"Selected Strategies: {selected_strategies or 'all'}")
        logger.info(f"Selected Models: {selected_models or 'all'}")

        # Setup environment and get clients and embedding providers
        clients, es_client, embeddings_providers = setup_environment()

        # Filter clients based on selected models
        filtered_clients = filter_clients(clients, selected_models)
        if not filtered_clients:
            logger.error("No matching clients found for selected models")
            sys.exit(1)

        # Get filtered strategies
        filtered_strategies = filter_strategies(selected_strategies)
        logger.info(
            f"Mapped to generation strategies: {[s.value for s in filtered_strategies]}"
        )

        logger.info("\nRunning Generation Evaluation...")
        generation_results = await run_generation_eval(
            es_client=es_client,
            embeddings_providers=embeddings_providers,
            clients=filtered_clients,
            filtered_strategies=filtered_strategies,
        )

        # Print results summary
        logger.info("\n=== Final Results Summary ===")
        logger.info("\nGeneration Evaluation Results:")

        for strategy_name, strategy_results in generation_results.items():
            logger.info(f"\nStrategy: {strategy_name}")
            if "aggregate_metrics" in strategy_results:
                for model_name, metrics in strategy_results[
                    "aggregate_metrics"
                ].items():
                    logger.info(f"\nModel: {model_name}")
                    logger.info(
                        f"Average Answer Relevancy: {metrics['average_answer_relevancy']:.3f}"
                    )
                    logger.info(
                        f"Average Faithfulness: {metrics['average_faithfulness']:.3f}"
                    )
                    logger.info(
                        f"Average Contextual Relevancy: {metrics['average_contextual_relevancy']:.3f}"
                    )

        # Report any errors
        all_errors = []
        for strategy_results in generation_results.values():
            if "errors" in strategy_results:
                all_errors.extend(strategy_results["errors"])

        if all_errors:
            logger.error("\nErrors encountered during evaluation:")
            for error in all_errors:
                logger.error(f"- {error}")

        logger.info("\nEvaluation completed successfully!")

    except ImportError as e:
        logger.error(f"\n❌ Error importing required modules: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error during evaluation: {str(e)}")
        sys.exit(1)


def main():
    """Entry point that handles running the evaluation."""
    try:
        asyncio.run(run_evaluations())
    except KeyboardInterrupt:
        logger.warning("\nEvaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
