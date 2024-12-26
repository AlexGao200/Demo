import re
from typing import Optional, List, Dict, Any
from mongoengine import (
    Document,
    StringField,
    DictField,
    ListField,
    ReferenceField,
    QuerySet,
)
from bson import ObjectId
from mongoengine.errors import NotUniqueError
from utils.error_handlers import log_error
from loguru import logger


class FilterDimension(Document):
    name: StringField = StringField(required=True)
    description: StringField = StringField()
    values: ListField = ListField(StringField())

    meta = {"collection": "filter_dimensions"}


class IndexRegistry(Document):
    index_name: StringField = StringField(required=True, unique=True)
    index_display_name: StringField = StringField(required=True, unique=False)
    entity_type: StringField = StringField(required=True)  # 'user' or 'organization'
    entity_id: StringField = StringField(required=True)
    metadata: DictField = DictField()
    filter_dimensions: ListField = ListField(ReferenceField(FilterDimension))

    meta = {"collection": "index_registry"}

    @staticmethod
    def validate_base_name(base_name: str) -> bool:
        return bool(base_name) and re.search(r"\w", base_name) is not None

    @classmethod
    def generate_unique_index_name(cls, base_name: str, document_id: str) -> str:
        if not cls.validate_base_name(base_name):
            raise ValueError(
                "Invalid base_name. It must not be empty and contain at least one alphanumeric character."
            )

        sanitized_base_name = re.sub(r"[^\w]", "_", base_name)
        return f"{sanitized_base_name}_{document_id}"

    @classmethod
    def register_index(
        cls,
        base_name: str,
        entity_name: str,
        entity_type: str,
        entity_id: str,
        document_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "IndexRegistry":
        try:
            index_name = cls.generate_unique_index_name(base_name, document_id)
            new_index = cls(
                index_name=index_name,
                index_display_name=entity_name,
                entity_type=entity_type,
                entity_id=str(entity_id),
                metadata=metadata or {},
            )
            new_index.save()
            logger.info(f"Successfully created index: {new_index.index_name}")
            return new_index
        except NotUniqueError as e:
            error_message, _ = log_error(
                e, f"Failed to create index: {index_name} already exists"
            )
            raise ValueError(error_message)
        except Exception as e:
            error_message, _ = log_error(e, "Failed to create index")
            raise ValueError(error_message)

    @classmethod
    def get_index(cls, index_name: str) -> Optional["IndexRegistry"]:
        return cls.objects(index_name=index_name).first()

    @classmethod
    def delete_index(cls, index_name: str) -> int:
        try:
            result = cls.objects(index_name=index_name).delete()
            if not result:
                logger.warning(f"No index found with name: {index_name}")
            else:
                logger.info(f"Successfully deleted index: {index_name}")
            return result
        except Exception as e:
            error_message, _ = log_error(e, f"Failed to delete index {index_name}")
            raise ValueError(error_message)

    @classmethod
    def list_indices(
        cls, entity_type: Optional[str] = None, entity_id: Optional[str] = None
    ) -> QuerySet:
        query = {}
        if entity_type:
            query["entity_type"] = entity_type
        if entity_id:
            query["entity_id"] = str(entity_id)
        return cls.objects(**query)

    @classmethod
    def add_filter_dimension(
        cls,
        index_name: str,
        dimension_name: str,
        description: str = "",
        values: Optional[List[str]] = None,
    ) -> FilterDimension:
        index_entry = cls.objects(index_name=index_name).first()
        if not index_entry:
            error_message, _ = log_error(
                ValueError(f"Index {index_name} not found"),
                "Failed to add filter dimension",
            )
            raise ValueError(error_message)

        # Check if a filter dimension with the same name already exists
        existing_dimension = next(
            (
                dim
                for dim in index_entry.filter_dimensions
                if dim.name == dimension_name
            ),
            None,
        )
        if existing_dimension:
            logger.info(
                f"Filter dimension '{dimension_name}' already exists for index '{index_name}'. Returning existing dimension."
            )
            return existing_dimension

        try:
            new_dimension = FilterDimension(
                name=dimension_name, description=description, values=values or []
            ).save()

            index_entry.filter_dimensions.append(new_dimension)
            index_entry.save()
            logger.info(
                f"Added new filter dimension {dimension_name} to index {index_name}"
            )
            return new_dimension
        except Exception as e:
            error_message, _ = log_error(
                e, f"Failed to add filter dimension to index {index_name}"
            )
            raise ValueError(error_message)

    @classmethod
    def get_filter_dimensions(cls, index_name: str) -> list[FilterDimension]:
        index_entry = cls.objects(index_name=index_name).first()
        if not index_entry:
            error_message, _ = log_error(
                ValueError(f"Index {index_name} not found"),
                "Failed to get filter dimensions",
            )
            raise ValueError(error_message)

        return index_entry.filter_dimensions

    @classmethod
    def get_filter_dimension_name(cls, dimension_id: ObjectId) -> str:
        """Retrieve the name of the filter dimension based on its ObjectId."""
        filter_dimension = FilterDimension.objects(id=dimension_id).first()
        if filter_dimension:
            return filter_dimension.name
        return "Unknown"

    @classmethod
    def update_index_metadata(
        cls, index_name: str, metadata: Dict[str, Any]
    ) -> "IndexRegistry":
        index_entry = cls.objects(index_name=index_name).first()
        if not index_name:
            error_message, _ = log_error(
                ValueError(f"Index {index_name} not found"),
                "Failed to update index metadata",
            )
            raise ValueError(error_message)

        try:
            index_entry.metadata.update(metadata)
            index_entry.save()
            logger.info(f"Successfully updated metadata for index: {index_name}")
            return index_entry
        except Exception as e:
            error_message, _ = log_error(
                e, f"Failed to update metadata for index {index_name}"
            )
            raise ValueError(error_message)
