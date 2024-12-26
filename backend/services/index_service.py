from typing import Optional, Protocol
from models.index_registry import IndexRegistry
from services.elasticsearch_service import VectorStore
from datetime import datetime, timezone
from utils.error_handlers import log_error

from loguru import logger


class IndexOperations(Protocol):
    """Protocol defining the interface for index operations."""

    def create_index(self, index_name: str) -> None:
        """Create an index with the given name."""
        ...

    def delete_index(self, index_name: str) -> None:
        """Delete an index with the given name."""
        ...


class IndexRegistryOperations(Protocol):
    """Protocol defining the interface for index registry operations."""

    @staticmethod
    def register_index(
        base_name: str,
        entity_name: str,
        entity_type: str,
        entity_id: str,
        document_id: str,
        metadata: Optional[dict] = None,
    ) -> "IndexRegistry":
        """Register a new index in the registry."""
        ...

    @staticmethod
    def delete_index(index_name: str) -> int:
        """Delete an index from the registry."""
        ...

    @staticmethod
    def list_indices(
        entity_type: Optional[str] = None, entity_id: Optional[str] = None
    ):
        """List indices from the registry."""
        ...


class IndexService:
    """
    Service for managing indices and their metadata.

    This service follows dependency injection principles and is framework-agnostic.
    It manages both the index registry in MongoDB and the actual indices in Elasticsearch.
    """

    def __init__(
        self,
        index_operations: IndexOperations,
        registry_operations: IndexRegistryOperations = IndexRegistry,
    ):
        """
        Initialize IndexService with required dependencies.

        Args:
            index_operations: Implementation of index operations (e.g., Elasticsearch)
            registry_operations: Implementation of registry operations (default: IndexRegistry)
        """
        self._index_ops = index_operations
        self._registry_ops = registry_operations

    def _create_index_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        display_name: str,
    ) -> str:
        """
        Create an index for a given entity.

        Args:
            entity_type: Type of entity ('user' or 'organization')
            entity_id: Unique identifier of the entity
            entity_name: Name of the entity
            display_name: Display name for the index

        Returns:
            str: Name of the created index

        Raises:
            Exception: If index creation fails
        """
        try:
            # Register the index in registry
            base_name = f"{entity_type}_{entity_name.lower().replace(' ', '_')}"
            index_registry = self._registry_ops.register_index(
                base_name, display_name, entity_type, entity_id, str(entity_id)
            )

            # Create the index in storage
            self._index_ops.create_index(index_registry.index_name)

            logger.info(
                f"Successfully created index for {entity_type} {display_name}: {index_registry.index_name}"
            )
            return index_registry.index_name
        except Exception as e:
            error_message, _ = log_error(
                e, f"Index creation for {entity_type} {display_name}"
            )
            raise Exception(error_message)

    def create_user_index(self, user_id: str, username: str, display_name: str) -> str:
        """Create an index for a user."""
        return self._create_index_for_entity("user", user_id, username, display_name)

    def create_organization_index(
        self, org_id: str, org_name: str, display_name: str
    ) -> str:
        """Create an index for an organization."""
        return self._create_index_for_entity(
            "organization", org_id, org_name, display_name
        )

    def archive_index(self, index_name: str) -> str:
        """
        Archive an index by:
        1. Marking it as archived in registry
        2. Renaming it with an archive prefix
        3. Making it read-only
        """
        try:
            # Get the index from registry
            index = self._registry_ops.get(index_name=index_name)
            if not index:
                error_message, _ = log_error(
                    ValueError(f"Index {index_name} not found in registry"),
                    "Index archive validation",
                )
                raise ValueError(error_message)

            # Generate archive name
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            archive_name = f"archived_{index_name}_{timestamp}"

            # Update index registry
            index.update(
                is_archived=True,
                archived_at=datetime.now(timezone.utc),
                archived_name=archive_name,
            )

            # Make index read-only and clone it
            if isinstance(self._index_ops, VectorStore):
                self._index_ops.client.indices.put_settings(
                    index=index_name,
                    body={
                        "settings": {
                            "index.blocks.write": True,
                            "index.blocks.read": False,
                        }
                    },
                )

                self._index_ops.client.indices.clone(
                    index=index_name,
                    target=archive_name,
                    body={
                        "settings": {
                            "index.blocks.write": True,
                            "index.blocks.read": False,
                        }
                    },
                )

                # Delete original index after successful clone
                self._index_ops.client.indices.delete(index=index_name)

            logger.info(f"Successfully archived index {index_name} to {archive_name}")
            return archive_name

        except Exception as e:
            error_message, _ = log_error(e, f"Index archival process for {index_name}")
            raise Exception(error_message)

    def delete_index(self, index_name: str) -> None:
        """Delete an index from both Registry and storage."""
        try:
            # Delete from registry
            self._registry_ops.delete_index(index_name)

            # Delete from storage
            self._index_ops.delete_index(index_name)

            logger.info(f"Successfully deleted index: {index_name}")
        except Exception as e:
            error_message, _ = log_error(e, f"Index deletion for {index_name}")
            raise Exception(error_message)

    def list_indices(self, entity_type: str = None, entity_id: str = None):
        """List indices from the registry."""
        return self._registry_ops.list_indices(entity_type, entity_id)


# Adapter for VectorStore to implement IndexOperations
class VectorStoreAdapter(IndexOperations):
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def create_index(self, index_name: str) -> None:
        self.vector_store.create_index(self.vector_store.client, index_name)

    def delete_index(self, index_name: str) -> None:
        self.vector_store.client.indices.delete(index=index_name, ignore=[404])
