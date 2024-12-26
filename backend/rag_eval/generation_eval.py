"""
This module provides functionality for evaluating RAG performance using test documents.
"""

from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
)
from deepeval.test_case import MLLMTestCase, MLLMImage
from deepeval import evaluate
from deepeval.dataset import EvaluationDataset
from services.document_ingestion_service import DocumentProcessor
from services.elasticsearch_service import VectorStore
from services.rag import GenerationStrategy
from loguru import logger
import os
from typing import Any, Tuple, NamedTuple, Union, Dict
from utils.error_handlers import log_error
from treeseg.configs import treeseg_configs
from services.llm_service import LLM
from factories.llm_provider_factory import LLMProviderFactory
import anthropic
import openai
from groq import Groq, AsyncGroq
from services.embedding_strategies import (
    CohereEmbeddingStrategy,
    VoyageEmbeddingStrategy,
)
from services.document_processing_strategies import (
    SegmentationStrategy,
    VoyageDocumentStrategy,
)
from mongoengine import connect, disconnect_all
from models.index_registry import IndexRegistry
from models.user import User
from tests.utils.data_factory import DataFactory
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
import base64


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""

    pass


class RetrievalError(Exception):
    """Custom exception for retrieval errors."""

    pass


class StrategyConfig(NamedTuple):
    """Configuration for document processing and embedding strategies."""

    name: str
    processing_strategy: Any
    embedding_strategy: Any
    generation_strategy: GenerationStrategy


def save_base64_image(base64_str: str, output_dir: str) -> str:
    """Save base64 image to a file and return the local path."""
    try:
        # Create directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        filename = f"image_{hash(base64_str)}.png"
        filepath = os.path.join(output_dir, filename)

        # Decode and save image
        image_data = base64.b64decode(base64_str)
        with open(filepath, "wb") as f:
            f.write(image_data)

        return filepath
    except Exception as e:
        logger.error(f"Error saving base64 image: {str(e)}")
        return None


def create_system_prompts(strategy: GenerationStrategy) -> list[Dict[str, Any]]:
    """Create appropriate system prompts based on generation strategy."""
    base_prompt = {
        "type": "text",
        "text": "You are a helpful assistant tasked with answering questions about medical documents.",
    }

    strategy_specific = {
        "type": "text",
        "text": {
            GenerationStrategy.TEXT_ONLY: "Focus on analyzing and explaining the textual content provided.",
            GenerationStrategy.IMAGES_ONLY: "Focus on analyzing and describing the images provided.",
            GenerationStrategy.INTERLEAVED: "Analyze both text and images provided, integrating information from both sources.",
        }[strategy],
    }

    return [base_prompt, strategy_specific]


def create_prompt_from_context(
    question: str,
    retrieval_context: list[Union[str, MLLMImage]],
    strategy: GenerationStrategy,
) -> Union[str, list[Dict[str, Any]]]:
    """Create appropriate prompt format based on generation strategy."""
    if strategy == GenerationStrategy.TEXT_ONLY:
        # For text-only, use simple string format
        text_context = " ".join(
            item for item in retrieval_context if isinstance(item, str)
        )
        return f"""Based on the context, answer the question.

Context:
{text_context}

Question: {question}

Answer:"""
    else:
        # For image-based strategies, use structured format
        content = []
        for item in retrieval_context:
            if isinstance(item, str):
                content.append({"type": "text", "text": item})
            elif isinstance(item, MLLMImage):
                content.append({"type": "image", "image_url": item.url})

        # Add the question at the end
        content.append(
            {
                "type": "text",
                "text": f"Based on the provided content, answer this question: {question}",
            }
        )
        content.append({"type": "text", "text": "Answer:"})

        return [{"role": "user", "content": content}]


async def run_generation_eval(
    es_client, embeddings_providers, clients, filtered_strategies=None
):
    """Run generation evaluation using actual documents and test cases."""
    logger.info("\nRunning Generation Evaluation...")

    # Define strategy combinations to evaluate
    base_strategy_configs = [
        StrategyConfig(
            name="text_only_segmentation_cohere",
            processing_strategy=SegmentationStrategy(
                treeseg_configs=treeseg_configs["augmend"],
                embeddings_providers=embeddings_providers,
            ),
            embedding_strategy=CohereEmbeddingStrategy(
                embeddings_providers=embeddings_providers
            ),
            generation_strategy=GenerationStrategy.TEXT_ONLY,
        ),
        StrategyConfig(
            name="images_only_segmentation_cohere",
            processing_strategy=SegmentationStrategy(
                treeseg_configs=treeseg_configs["augmend"],
                embeddings_providers=embeddings_providers,
            ),
            embedding_strategy=CohereEmbeddingStrategy(
                embeddings_providers=embeddings_providers
            ),
            generation_strategy=GenerationStrategy.IMAGES_ONLY,
        ),
        StrategyConfig(
            name="interleaved_segmentation_cohere",
            processing_strategy=SegmentationStrategy(
                treeseg_configs=treeseg_configs["augmend"],
                embeddings_providers=embeddings_providers,
            ),
            embedding_strategy=CohereEmbeddingStrategy(
                embeddings_providers=embeddings_providers
            ),
            generation_strategy=GenerationStrategy.INTERLEAVED,
        ),
    ]

    # Add Voyage-based strategies if client is provided
    if embeddings_providers.get("voyage"):
        base_strategy_configs.extend(
            [
                StrategyConfig(
                    name="text_only_voyage",
                    processing_strategy=VoyageDocumentStrategy(),
                    embedding_strategy=VoyageEmbeddingStrategy(
                        embeddings_providers=embeddings_providers
                    ),
                    generation_strategy=GenerationStrategy.TEXT_ONLY,
                ),
                StrategyConfig(
                    name="images_only_voyage",
                    processing_strategy=VoyageDocumentStrategy(),
                    embedding_strategy=VoyageEmbeddingStrategy(
                        embeddings_providers=embeddings_providers
                    ),
                    generation_strategy=GenerationStrategy.IMAGES_ONLY,
                ),
                StrategyConfig(
                    name="interleaved_voyage",
                    processing_strategy=VoyageDocumentStrategy(),
                    embedding_strategy=VoyageEmbeddingStrategy(
                        embeddings_providers=embeddings_providers
                    ),
                    generation_strategy=GenerationStrategy.INTERLEAVED,
                ),
            ]
        )

    # Filter strategies if specified
    if filtered_strategies:
        strategy_configs = [
            config
            for config in base_strategy_configs
            if config.generation_strategy in filtered_strategies
        ]
        if not strategy_configs:
            raise ValueError("No matching strategies found for the specified filter")
    else:
        strategy_configs = base_strategy_configs

    all_results = {}

    for strategy_config in strategy_configs:
        logger.info(f"\nEvaluating strategy combination: {strategy_config.name}")

        evaluation_results = {
            "document_processing": None,
            "test_cases": [],
            "aggregate_metrics": {},
            "errors": [],
            "strategy": strategy_config.name,
        }

        try:
            # Initialize MongoDB connection
            mongodb_uri = os.environ.get("MONGODB_URI")
            if not mongodb_uri:
                raise ValueError("MONGODB_URI environment variable not set")

            disconnect_all()
            connect(host=mongodb_uri)
            logger.info("Connected to MongoDB")

            # Ensure test environment is set up
            test_index_name = f"rag_eval_test_{strategy_config.name}"
            await ensure_test_environment(test_index_name)
            logger.info("Test environment setup completed")

            # Initialize LLM providers with strategy-specific system prompts
            llm_providers = {
                "groq": LLM(
                    LLMProviderFactory.create_provider(
                        "groq",
                        sync_client=Groq(api_key=os.getenv("GROQ_API_KEY")),
                        async_client=AsyncGroq(api_key=os.getenv("GROQ_API_KEY")),
                    ),
                    system_prompts=create_system_prompts(
                        strategy_config.generation_strategy
                    ),
                ),
                "hyperbolic": LLM(
                    LLMProviderFactory.create_provider(
                        "openai",
                        sync_client=openai.OpenAI(
                            base_url="https://api.hyperbolic.xyz/v1",
                            api_key=os.getenv("HYPERBOLIC_API_KEY"),
                        ),
                        async_client=openai.AsyncOpenAI(
                            base_url="https://api.hyperbolic.xyz/v1",
                            api_key=os.getenv("HYPERBOLIC_API_KEY"),
                        ),
                    ),
                    system_prompts=create_system_prompts(
                        strategy_config.generation_strategy
                    ),
                ),
                "anthropic": LLM(
                    LLMProviderFactory.create_provider(
                        "anthropic",
                        sync_client=anthropic.Anthropic(
                            api_key=os.getenv("ANTHROPIC_API_KEY")
                        ),
                        async_client=anthropic.AsyncAnthropic(
                            api_key=os.getenv("ANTHROPIC_API_KEY")
                        ),
                    ),
                    system_prompts=create_system_prompts(
                        strategy_config.generation_strategy
                    ),
                ),
            }

            # Initialize services with current strategy combination
            vector_store = VectorStore(es_client, embeddings_providers, 1024)

            document_processor = DocumentProcessor(
                llm_providers=llm_providers,
                vector_store=vector_store,
                dims=1024,
                processing_strategy=strategy_config.processing_strategy,
                embedding_strategy=strategy_config.embedding_strategy,
            )

            # Set up test documents
            evaluation_results["document_processing"] = await setup_test_documents(
                document_processor, vector_store, test_index_name
            )
            logger.info("✓ Test documents ingested")

            # Create evaluation dataset and metadata
            dataset, metadata_list = await create_test_cases(
                vector_store, test_index_name, strategy_config.generation_strategy
            )
            logger.info("✓ Evaluation dataset created")

            # Track metrics for each model
            for client in clients:
                model_name = client.get_model_name()
                logger.info(f"\nEvaluating with model: {model_name}")

                # Initialize metrics
                metrics = [
                    AnswerRelevancyMetric(model=client),
                    FaithfulnessMetric(model=client),
                    ContextualRelevancyMetric(model=client),
                ]

                try:
                    # Generate answers using retrieved context
                    for test_case in dataset.test_cases:
                        prompt = create_prompt_from_context(
                            test_case.input,
                            test_case.retrieval_context,
                            strategy_config.generation_strategy,
                        )
                        response = await client.a_generate(prompt)
                        test_case.actual_output = (
                            response.content
                            if hasattr(response, "content")
                            else str(response)
                        )

                    # Run evaluation
                    results = evaluate(
                        dataset, metrics, write_cache=False, run_async=False
                    )

                    # Store test case results with metadata
                    for idx, test_case in enumerate(dataset.test_cases):
                        test_result = {
                            "model": model_name,
                            "question": test_case.input,
                            "generated_answer": test_case.actual_output,
                            "expected_answer": test_case.expected_output,
                            "target_document": metadata_list[idx]["target_document"],
                            "retrieved_documents": metadata_list[idx][
                                "retrieved_documents"
                            ],
                            "generation_strategy": strategy_config.generation_strategy.value,
                            "metrics": {
                                "answer_relevancy": results.test_results[idx]
                                .metrics_data[0]
                                .score,
                                "faithfulness": results.test_results[idx]
                                .metrics_data[1]
                                .score,
                                "contextual_relevancy": results.test_results[idx]
                                .metrics_data[2]
                                .score,
                            },
                        }
                        evaluation_results["test_cases"].append(test_result)

                    # Calculate and store aggregate metrics for this model
                    evaluation_results["aggregate_metrics"][model_name] = {
                        "average_answer_relevancy": sum(
                            r.metrics_data[0].score for r in results.test_results
                        )
                        / len(results.test_results),
                        "average_faithfulness": sum(
                            r.metrics_data[1].score for r in results.test_results
                        )
                        / len(results.test_results),
                        "average_contextual_relevancy": sum(
                            r.metrics_data[2].score for r in results.test_results
                        )
                        / len(results.test_results),
                    }

                except Exception as e:
                    error_msg = f"Error evaluating model {model_name}: {str(e)}"
                    evaluation_results["errors"].append(error_msg)
                    logger.error(error_msg)
                    continue

            # Store results for this strategy combination
            all_results[strategy_config.name] = evaluation_results

            # Process and export results for this strategy
            process_and_export_results(
                evaluation_results,
                output_dir=f"rag_eval/results/{strategy_config.name}",
            )

        except Exception as e:
            error_msg = f"Critical error in evaluation pipeline for {strategy_config.name}: {str(e)}"
            evaluation_results["errors"].append(error_msg)
            log_error(e, error_msg)
            all_results[strategy_config.name] = evaluation_results

    # Generate comparative analysis
    generate_strategy_comparison(all_results)

    return all_results


async def ensure_test_environment(test_index_name: str):
    """
    Ensure the test environment is properly set up with required MongoDB collections and documents.
    """
    try:
        # Create test user if it doesn't exist
        user = User.objects(email="test@example.com").first()
        if not user:
            user = DataFactory.create_user(email="test@example.com")

        # Create test index registry if it doesn't exist
        if not IndexRegistry.objects(index_name=test_index_name).first():
            index_registry = IndexRegistry(
                index_name=test_index_name,
                index_display_name="RAG Evaluation Test Index",
                entity_type="user",
                entity_id=str(user.id),
            )
            index_registry.save()
            logger.info(f"Created test index registry: {test_index_name}")

        return True
    except Exception as e:
        logger.error(f"Error setting up test environment: {str(e)}")
        raise


async def setup_test_documents(
    document_processor: DocumentProcessor,
    vector_store: VectorStore,
    test_index_name="rag_eval_test",
):
    """Set up test documents in the vector store."""
    try:
        # Ensure test index exists in Elasticsearch
        # Get test user
        test_user = User.objects(email="test@example.com").first()
        if not test_user:
            raise DocumentProcessingError("Test user not found")

        if not vector_store.client.indices.exists(index=test_index_name):
            VectorStore.create_index(vector_store.client, test_index_name)
            logger.info(f"Created test index in Elasticsearch: {test_index_name}")

        # Define test documents
        test_docs = [
            {
                "file_path": "rag_eval/test_docs/ATLASPLAN.pdf",
                "file_url": "example.com",
                "title": "ATLASPLAN Surgical Technique",
            },
        ]

        # Track ingestion results
        ingestion_results = []

        # Ingest documents
        for doc in test_docs:
            if not os.path.exists(doc["file_path"]):
                raise DocumentProcessingError(f"Document not found: {doc['file_path']}")

            try:
                await document_processor.ingest(
                    file_path=doc["file_path"],
                    file_url=doc["file_url"],
                    title=doc["title"],
                    thumbnail_urls=[],
                    index_names=[test_index_name],
                    file_visibility="private",
                    originating_user_id=str(test_user.id),
                    filter_dimensions={},
                )
                ingestion_results.append({"title": doc["title"], "status": "success"})
                logger.info(f"Ingested document: {doc['title']}")
            except Exception as e:
                ingestion_results.append(
                    {"title": doc["title"], "status": "failed", "error": str(e)}
                )
                logger.error(f"Failed to ingest document {doc['title']}: {str(e)}")
                raise DocumentProcessingError(
                    f"Failed to ingest {doc['title']}: {str(e)}"
                )

        return ingestion_results

    except Exception as e:
        raise DocumentProcessingError(f"Error in document setup: {str(e)}")


async def create_test_cases(
    vector_store: VectorStore,
    test_index_name: str,
    generation_strategy: GenerationStrategy,
) -> Tuple[EvaluationDataset, list[dict[str, Any]]]:
    """Create test cases with actual retrieved contexts."""
    try:
        # Define test questions and expected outputs
        test_questions = [
            {
                "question": "Is it ok to remove osteophytes before putting in the Atlasplan guide?",
                "expected_output": "No, don't remove osteophytes before putting in the Atlasplan guide.",
                "document": "Atlasplan Guide",
            },
            {
                "question": "What should I do if I'm having trouble removing the guide without messing up the central glenoid pin",
                "expected_output": "Remove the central glenoid pin, then remove the guide and finally reinsert the central glenoid pin very carefully in the pre-drilled hole in the bone.",
                "document": "Atlasplan Guide",
            },
            {
                "question": "What glenoid pin diameter should I use for the AETOS system?",
                "expected_output": "2.5mm.",
                "document": "Atlasplan Guide",
            },
            {
                "question": "Show me the guide page that labels the implant's key parts.",
                "expected_output": "Please consult Document #X (allow for any X in the model's output, as we don't know pre-chunking which chunk this will be on). Assume that a base64 image string is proof of retrieval.",
                "document": "Atlasplan Guide",
            },
            {
                "question": "Show me a picture of the Atlasplan guide on the glenoid face just after insertion but before any pins have been inserted. Assume that a base64 image string is proof of retrieval.",
                "expected_output": "Please consult Document #X (allow for any X in the model's output, as we don't know pre-chunking which chunk this will be on)",
                "document": "Atlasplan Guide",
            },
        ]

        test_cases = []
        metadata_list = []

        # Create directory for saving images
        image_dir = "rag_eval/temp_images"
        Path(image_dir).mkdir(parents=True, exist_ok=True)

        for question in test_questions:
            try:
                # Get relevant chunks using the vector_store
                chunks = vector_store.get_relevant_documents(
                    question["question"],
                    index_names=[test_index_name],
                    filter_dimensions=None,
                    visibility=None,
                )

                if not chunks:
                    logger.warning(
                        f"No chunks retrieved for question: {question['question']}"
                    )
                    continue

                # Format context based on generation strategy
                retrieval_context: list[Union[str, MLLMImage]] = []

                for chunk in chunks[:5]:
                    metadata = chunk["metadata"]

                    # Add text content
                    retrieval_context.append(metadata["section_text"])

                    # Add associated images for image-based strategies
                    if generation_strategy in [
                        GenerationStrategy.IMAGES_ONLY,
                        GenerationStrategy.INTERLEAVED,
                    ]:
                        if "page_images" in metadata and metadata["page_images"]:
                            for image in metadata["page_images"]:
                                # Save base64 image to file and create MLLMImage
                                image_path = save_base64_image(image, image_dir)
                                if image_path:
                                    retrieval_context.append(
                                        MLLMImage(url=image_path, local=True)
                                    )

                # Create test case
                test_case = MLLMTestCase(
                    input=question["question"],
                    actual_output="",  # Will be filled during evaluation
                    expected_output=question["expected_output"],
                    retrieval_context=retrieval_context,
                )
                test_cases.append(test_case)

                # Store metadata separately
                metadata = {
                    "target_document": question["document"],
                    "retrieved_documents": [
                        chunk["metadata"].get("title", "Unknown")
                        for chunk in chunks[:3]
                    ],
                }
                metadata_list.append(metadata)

            except Exception as e:
                log_error(
                    e, f"Error creating test case for question '{question['question']}'"
                )
                continue

        if not test_cases:
            raise RetrievalError("No test cases could be created")

        # Create evaluation dataset
        dataset = EvaluationDataset(test_cases=test_cases)

        return dataset, metadata_list

    except Exception as e:
        raise RetrievalError(f"Error creating test cases: {str(e)}")


def process_and_export_results(
    results: dict, output_dir: str = "rag_eval/results"
) -> None:
    """Process and export RAG evaluation results in multiple formats."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Convert test cases to DataFrame for analysis
    test_cases_df = pd.DataFrame(results.get("test_cases", []))

    if test_cases_df.empty:
        logger.warning("No test cases found in results")
        return

    # Expand metrics column
    metrics_df = pd.json_normalize(test_cases_df["metrics"])
    test_cases_df = pd.concat(
        [test_cases_df.drop("metrics", axis=1), metrics_df], axis=1
    )

    # Calculate aggregate metrics per model and strategy
    model_metrics = {}
    for model_name, model_results in results.get("aggregate_metrics", {}).items():
        model_metrics[model_name] = {
            "answer_relevancy": model_results.get("average_answer_relevancy", 0),
            "faithfulness": model_results.get("average_faithfulness", 0),
            "contextual_relevancy": model_results.get(
                "average_contextual_relevancy", 0
            ),
        }

    # Print summary
    logger.info("\n=== RAG Evaluation Summary ===")

    for model_name, metrics in model_metrics.items():
        logger.info(f"\nModel: {model_name}")
        for metric, value in metrics.items():
            logger.info(f"{metric.replace('_', ' ').title()}: {value:.3f}")

    logger.info("\nDetailed Results:")
    for _, row in test_cases_df.iterrows():
        logger.info("\n---")
        logger.info(f"Question: {row['question']}")
        logger.info(f"Generated Answer: {row['generated_answer']}")
        logger.info(f"Expected Answer: {row['expected_answer']}")
        logger.info(f"Target Document: {row['target_document']}")
        logger.info(f"Retrieved Documents: {row['retrieved_documents']}")
        logger.info(f"Generation Strategy: {row['generation_strategy']}")
        logger.info("\nMetrics:")
        logger.info(f"- Answer Relevancy: {row['answer_relevancy']:.3f}")
        logger.info(f"- Faithfulness: {row['faithfulness']:.3f}")
        logger.info(f"- Contextual Relevancy: {row['contextual_relevancy']:.3f}")

    # Export results
    test_cases_df.to_csv(f"{output_dir}/detailed_results.csv", index=False)

    with open(f"{output_dir}/aggregate_metrics.json", "w") as f:
        json.dump(model_metrics, f, indent=2)

    # Create visualizations
    plt.figure(figsize=(12, 6))
    metrics_data = []
    for model, metrics in model_metrics.items():
        for metric, value in metrics.items():
            metrics_data.append({"Model": model, "Metric": metric, "Score": value})

    metrics_df = pd.DataFrame(metrics_data)
    sns.barplot(x="Metric", y="Score", hue="Model", data=metrics_df)
    plt.title("RAG Evaluation Metrics by Model")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/metrics_visualization.png")
    plt.close()


def generate_strategy_comparison(all_results: dict[str, Any]):
    """Generate comparative analysis of different strategy combinations."""
    comparison_dir = "rag_eval/results/comparison"
    Path(comparison_dir).mkdir(parents=True, exist_ok=True)

    # Prepare data for comparison
    comparison_data = []
    for strategy_name, results in all_results.items():
        for model_name, metrics in results.get("aggregate_metrics", {}).items():
            comparison_data.append(
                {
                    "Strategy": strategy_name,
                    "Model": model_name,
                    "Answer Relevancy": metrics["average_answer_relevancy"],
                    "Faithfulness": metrics["average_faithfulness"],
                    "Contextual Relevancy": metrics["average_contextual_relevancy"],
                }
            )

    # Create comparison DataFrame
    comparison_df = pd.DataFrame(comparison_data)

    # Generate comparison visualizations
    plt.figure(figsize=(15, 8))
    metrics = ["Answer Relevancy", "Faithfulness", "Contextual Relevancy"]

    for i, metric in enumerate(metrics, 1):
        plt.subplot(1, 3, i)
        sns.barplot(
            data=comparison_df,
            x="Strategy",
            y=metric,
            hue="Model",
        )
        plt.title(f"Comparison of {metric}")
        plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(f"{comparison_dir}/strategy_comparison.png")
    plt.close()

    # Export comparison data
    comparison_df.to_csv(f"{comparison_dir}/strategy_comparison.csv", index=False)

    # Generate summary report
    summary = comparison_df.groupby("Strategy")[metrics].mean()
    summary.to_csv(f"{comparison_dir}/strategy_summary.csv")

    # Log comparison summary
    logger.info("\n=== Strategy Comparison Summary ===")
    for strategy in summary.index:
        logger.info(f"\nStrategy: {strategy}")
        for metric in metrics:
            logger.info(f"{metric}: {summary.loc[strategy, metric]:.3f}")
