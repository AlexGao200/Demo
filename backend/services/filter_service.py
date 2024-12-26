from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import parse_qs
from flask import jsonify
from loguru import logger
from mongoengine import Q
from mongoengine.errors import DoesNotExist

from models.file_metadata import FileMetadata
from models.index_registry import IndexRegistry
from models.user_organization import UserOrganization
from models.user import User


class FilterService:
    @staticmethod
    def parse_indices(
        parsed_params: Dict[str, List[str]],
    ) -> List[Dict[str, Optional[str]]]:
        """Parse indices from query parameters."""
        indices = []
        index_count = 0

        while f"indices[{index_count}][name]" in parsed_params:
            index_data = {
                "display_name": parsed_params.get(
                    f"indices[{index_count}][display_name]", [None]
                )[0],
                "name": parsed_params.get(f"indices[{index_count}][name]", [None])[0],
                "role_of_current_user": parsed_params.get(
                    f"indices[{index_count}][role_of_current_user]", [None]
                )[0],
            }
            indices.append(index_data)
            index_count += 1

        return indices

    @staticmethod
    def parse_filter_dimensions(
        parsed_params: Dict[str, List[str]],
    ) -> Tuple[List[str], List[List[str]]]:
        """Parse filter dimension names and values."""
        filter_dim_names = parsed_params.get("filterDimNames[]", [])
        filter_dim_values = []

        value_index = 0
        while f"filterDimValues[{value_index}][0]" in parsed_params:
            values = []
            inner_value_index = 0
            while (
                f"filterDimValues[{value_index}][{inner_value_index}]" in parsed_params
            ):
                values.append(
                    parsed_params[
                        f"filterDimValues[{value_index}][{inner_value_index}]"
                    ][0]
                )
                inner_value_index += 1
            filter_dim_values.append(values)
            value_index += 1

        return filter_dim_names, filter_dim_values

    @staticmethod
    def parse_pagination_sorting(parsed_params: Dict[str, List[str]]) -> Dict[str, Any]:
        """Parse pagination and sorting parameters."""
        page = int(parsed_params.get("page", [1])[0])
        sort_field = parsed_params.get("sortField", ["title"])[0]
        sort_order = parsed_params.get("sortOrder", ["asc"])[0]
        per_page = 9 if sort_field == "title" else 1000

        return {
            "page": page,
            "sort_field": sort_field,
            "sort_order": sort_order,
            "per_page": per_page,
        }

    @staticmethod
    def build_query(
        indices: List[Dict[str, Optional[str]]],
        filter_dim_names: List[str],
        filter_dim_values: List[List[str]],
    ) -> Q:
        """Build MongoDB query from parameters."""
        query = Q()

        # Apply index filter
        if indices:
            index_names = [ind.get("name") for ind in indices if "name" in ind]
            query &= Q(index_names__in=index_names)

        # Apply filter dimensions
        if (
            filter_dim_names
            and filter_dim_values
            and len(filter_dim_names) == len(filter_dim_values)
        ):
            for dim_name, dim_value in zip(filter_dim_names, filter_dim_values):
                if dim_value:
                    query &= Q(**{f"filter_dimensions__{dim_name}__in": dim_value})

        return query

    @staticmethod
    def get_dimension_mapping(all_index_names: Set[str]) -> Dict[str, str]:
        """Create mapping of dimension IDs to names from indices."""
        dimension_mapping = {}

        for index_name in all_index_names:
            index_registry = IndexRegistry.objects(index_name=index_name).first()
            if index_registry and index_registry.filter_dimensions:
                for dim in index_registry.filter_dimensions:
                    dimension_mapping[str(dim.id)] = dim.name

        logger.info(f"Found dimension mapping: {dimension_mapping}")
        return dimension_mapping

    @staticmethod
    def check_document_access(doc: FileMetadata, current_user: User) -> bool:
        """Check if current user has access to document."""
        if doc.visibility == "public":
            return True

        try:
            if doc.originating_user and doc.originating_user.id == current_user.id:
                return True

            user_orgs = UserOrganization.objects(
                user=current_user.id, organization__in=doc.organizations, is_active=True
            )
            return bool(user_orgs)
        except (DoesNotExist, AttributeError):
            user_orgs = UserOrganization.objects(
                user=current_user.id, organization__in=doc.organizations, is_active=True
            )
            return bool(user_orgs)

    @staticmethod
    def process_document(
        doc: FileMetadata, dimension_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Process a single document into the required format."""
        filter_dims = {}
        for dim_id, values in doc.filter_dimensions.items():
            if dim_id in dimension_mapping:
                dim_name = dimension_mapping[dim_id]
                if isinstance(values, list):
                    filter_dims[dim_name] = ", ".join(
                        [str(v) for v in values if v is not None]
                    )
                else:
                    filter_dims[dim_name] = str(values)

        return {
            "id": str(doc.id),
            "title": doc.title,
            "s3_url": doc.s3_url,
            "thumbnail_urls": [doc.thumbnail_urls[0]] if doc.thumbnail_urls else [],
            "organization": doc.nominal_creator_name,
            "index_name": doc.index_names[0] if doc.index_names else None,
            "filter_dimensions": filter_dims,
            "file_visibility": doc.visibility,
        }

    @staticmethod
    def group_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group documents by filter dimensions."""
        grouped_docs = {}
        all_dimensions = set()

        # Get all unique dimensions
        for doc in documents:
            all_dimensions.update(doc["filter_dimensions"].keys())

        # Create groups for each dimension
        for dimension in all_dimensions:
            for doc in documents:
                if dimension in doc["filter_dimensions"]:
                    group_key = dimension
                    if group_key not in grouped_docs:
                        grouped_docs[group_key] = []
                    grouped_docs[group_key].append(doc)

        # Sort groups
        return [
            {"groupName": k, "documents": sorted(v, key=lambda x: x["title"].lower())}
            for k, v in sorted(grouped_docs.items())
        ]

    def filter_documents(self, query_string: str, current_user: User):
        """Main method to filter documents based on query parameters."""
        try:
            # Parse query string
            parsed_params = parse_qs(query_string)

            # Parse parameters
            indices = self.parse_indices(parsed_params)
            filter_dim_names, filter_dim_values = self.parse_filter_dimensions(
                parsed_params
            )
            params = self.parse_pagination_sorting(parsed_params)

            # Build and execute query
            query = self.build_query(indices, filter_dim_names, filter_dim_values)
            all_documents = FileMetadata.objects(query).order_by(
                f"{params['sort_order']}_{params['sort_field']}"
            )

            # Get dimension mapping
            all_index_names = {idx for doc in all_documents for idx in doc.index_names}
            dimension_mapping = self.get_dimension_mapping(all_index_names)

            # Process documents
            processed_docs = []
            for doc in all_documents:
                if self.check_document_access(doc, current_user):
                    processed_docs.append(self.process_document(doc, dimension_mapping))

            # Handle pagination and response
            if params["sort_field"] == "title":
                total_documents = len(processed_docs)
                start_idx = (params["page"] - 1) * params["per_page"]
                end_idx = start_idx + params["per_page"]
                paginated_docs = processed_docs[start_idx:end_idx]

                return jsonify(
                    {
                        "documents": paginated_docs,
                        "total": total_documents,
                        "page": params["page"],
                        "per_page": params["per_page"],
                        "total_pages": (total_documents + params["per_page"] - 1)
                        // params["per_page"],
                    }
                ), 200
            else:
                grouped_docs = self.group_documents(processed_docs)
                groups_per_page = 3
                total_groups = len(grouped_docs)
                total_pages = max(
                    (total_groups + groups_per_page - 1) // groups_per_page, 1
                )

                start_idx = (params["page"] - 1) * groups_per_page
                end_idx = start_idx + groups_per_page
                paginated_groups = grouped_docs[start_idx:end_idx]

                return jsonify(
                    {
                        "groups": paginated_groups,
                        "total": total_groups,
                        "page": params["page"],
                        "per_page": groups_per_page,
                        "total_pages": total_pages,
                    }
                ), 200

        except Exception as e:
            logger.error(f"Error in filter_documents: {str(e)}")
            return jsonify(
                {"error": "An error occurred while filtering documents"}
            ), 500
