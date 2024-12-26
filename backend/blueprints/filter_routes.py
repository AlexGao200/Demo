from flask import Blueprint, jsonify, request, current_app
from loguru import logger
from models.index_registry import IndexRegistry, FilterDimension
from models.organization import Organization
from auth.utils import token_required, validate_input
from services.elasticsearch_service import create_elasticsearch_client_with_retries
from utils.error_handlers import handle_errors
from services.filter_service import FilterService


def create_filter_blueprint():
    filter_bp = Blueprint("filter", __name__, url_prefix="/api/filter")
    filter_service = FilterService()

    @filter_bp.route("/get-visibilities", methods=["POST"])
    @token_required
    @handle_errors
    def get_visibilities(current_user):
        """
        Returns available visibility options based on index names.
        If any index name starts with 'user', only 'private' visibility is available.
        Otherwise, both 'public' and 'private' are available.
        """
        if not current_user:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.json
        logger.debug(f"Request data: {data}")

        index_names = data.get("indexNames")
        logger.info(f"Index names received: {index_names}")

        if not index_names or not isinstance(index_names, list):
            logger.warning("indexNames is either missing or not a list.")
            return (
                jsonify(
                    {"error": "indexNames must be a non-empty list", "visibilities": []}
                ),
                400,
            )

        visibilities = {"public", "private"}  # Start with both visibility options
        try:
            for index_name in index_names:
                logger.debug(f"Processing index: {index_name}")
                index = IndexRegistry.objects(index_name=index_name).first()

                if not index:
                    logger.warning(f"Index not found: {index_name}")
                    return (
                        jsonify(
                            {
                                "error": f"Index not found: {index_name}",
                                "visibilities": [],
                            }
                        ),
                        404,
                    )

                # If any index name starts with "user", limit to 'private'
                if index.index_name.startswith("user"):
                    logger.info(
                        f"Index {index_name} is a user index. Restricting visibility to 'private'."
                    )
                    visibilities = {"private"}  # Restrict visibility to private only

            # Return the final set of visibilities
            logger.info(f"Returning visibilities: {list(visibilities)}")
            return (
                jsonify(
                    {
                        "visibilities": list(
                            visibilities
                        )  # Return as list for JSON compatibility
                    }
                ),
                200,
            )

        except Exception as e:
            logger.error(f"Error retrieving visibilities: {e}")
            logger.exception("Exception occurred while processing visibilities")
            return (
                jsonify(
                    {
                        "error": f"Failed to retrieve visibilities: {str(e)}",
                        "visibilities": [],
                    }
                ),
                500,
            )

    @filter_bp.route("/get-filter-dimensions", methods=["GET"])
    @token_required
    @handle_errors
    def get_filter_dimensions(current_user):
        """
        Retrieves the filter dimensions for given indices with pagination.
        Handles both authenticated users and guest sessions.
        """
        logger.info(f"Request args: {request.args}")
        logger.info(
            f"User accessing filters - ID: {current_user.id}, Is Guest: {current_user.is_guest}"
        )

        index_names = request.args.getlist("index_names[]")
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))

        if not index_names:
            logger.info("index_names not included in request.")
            return jsonify({"error": "index_names is required"}), 400

        try:
            # For guest sessions, verify these are organization indices they can access
            if current_user.is_guest:
                # Get organization indices that guest can access
                organizations = Organization.objects()
                allowed_index_names = [
                    org.index_name for org in organizations if org.index_name
                ]

                # Check if requested indices are allowed
                authorized_indices = [
                    name for name in index_names if name in allowed_index_names
                ]
                if not authorized_indices:
                    logger.warning(
                        f"Guest user attempted to access unauthorized indices: {index_names}"
                    )
                    return jsonify({"error": "No authorized indices found"}), 403

                # Use the first authorized index
                index_name = authorized_indices[0]
            else:
                index_name = index_names[0]

            # Get the IndexRegistry document
            index_registry = IndexRegistry.objects.get(index_name=index_name)
            filter_dimensions_refs = index_registry.filter_dimensions
            logger.info(
                f"Retrieved {len(filter_dimensions_refs)} filter dimensions for index {index_name}"
            )

            # Paginate filter dimensions
            total_filters = len(filter_dimensions_refs)
            start = (page - 1) * limit
            end = start + limit
            filter_dimensions = []

            for dimension in filter_dimensions_refs[start:end]:
                try:
                    filter_dimensions.append(
                        {
                            "id": str(dimension.id),
                            "name": dimension.name,
                            "values": dimension.values,
                        }
                    )
                except Exception as e:
                    logger.error(f"Error processing FilterDimension: {e}")
                    continue

            return jsonify(
                {
                    "filter_dimensions": filter_dimensions,
                    "index_name": index_registry.index_name,
                    "total_filters": total_filters,
                    "page": page,
                    "limit": limit,
                }
            ), 200

        except IndexRegistry.DoesNotExist:
            logger.error(f"IndexRegistry not found for index: {index_name}")
            return jsonify({"error": "Index registry not found"}), 404
        except Exception as e:
            logger.error(f"Unexpected error in get_filter_dimensions: {str(e)}")
            return jsonify({"error": "An unexpected error occurred"}), 500

    @filter_bp.route("/get-filter-names-values", methods=["POST"])
    @token_required
    @handle_errors
    def get_filter_names_and_values(current_user):
        """
        Fetches filter dimension names and values using object IDs.
        """
        data = request.json
        filter_ids = data.get("filterIds", [])

        # Log the incoming filterIds
        logger.info(f"Received filterIds: {filter_ids}")

        if not filter_ids or not isinstance(filter_ids, list):
            return jsonify({"error": "Invalid or missing filterIds"}), 400

        try:
            # Retrieve filter dimensions by their IDs
            filter_dimensions = FilterDimension.objects.filter(id__in=filter_ids)

            if not filter_dimensions:
                logger.warning(f"No filter dimensions found for IDs: {filter_ids}")
                return (
                    jsonify(
                        {"error": "No filter dimensions found for the provided IDs"}
                    ),
                    404,
                )

            # Prepare the response with name and values for each filter dimension
            filters_info = []
            for dimension in filter_dimensions:
                filters_info.append(
                    {
                        "id": str(dimension.id),
                        "name": dimension.name,
                        "values": dimension.values,
                    }
                )

            # Log the filter dimensions being returned
            logger.info(f"Returning filter dimensions: {filters_info}")

            return jsonify({"filters": filters_info}), 200

        except Exception as e:
            logger.error(f"Error fetching filter dimensions: {e}")
            return jsonify({"error": "Server error"}), 500

    @filter_bp.route("/get-filter-dimension-values", methods=["GET"])
    @token_required
    @handle_errors
    def get_filter_dimension_values(current_user):
        dimension_id = request.args.get("dimension_id")
        if not dimension_id:
            return jsonify({"error": "Missing dimension_id"}), 400

        filter_dimension = FilterDimension.objects.get(id=dimension_id)
        values = list(set(filter_dimension.values))
        return jsonify({"values": values}), 200

    @filter_bp.route("/create-filter-dimension", methods=["POST"])
    @token_required
    @validate_input(["dimension_name", "index_names"])
    @handle_errors
    def create_filter_dimension(current_user):
        data = request.json
        dimension_name = data["dimension_name"]
        index_names = data["index_names"]

        if not isinstance(index_names, list) or len(index_names) == 0:
            return jsonify({"error": "index_names must be a non-empty list"}), 400

        new_dimension = FilterDimension(name=dimension_name, values=[])
        new_dimension.save()
        es_client = create_elasticsearch_client_with_retries(
            host=current_app.config["ELASTICSEARCH_HOST"],
            port=current_app.config["ELASTICSEARCH_PORT"],
        )

        for index_name in index_names:
            index_registry = IndexRegistry.objects(index_name=index_name).first()
            if not index_registry:
                logger.warning(f"Index registry not found for index_name: {index_name}")
                continue

            index_registry.filter_dimensions.append(new_dimension)
            index_registry.save()

            # Update Elasticsearch mapping to include the new filter dimension
            es_client.indices.put_mapping(
                index=index_name,
                body={
                    "properties": {
                        f"filter_dimensions.{dimension_name}": {"type": "keyword"}
                    }
                },
            )

        return (
            jsonify(
                {
                    "message": "Filter dimension created successfully",
                    "dimension_id": str(new_dimension.id),
                    "dimension_name": new_dimension.name,
                }
            ),
            201,
        )

    @filter_bp.route("/add-value-to-filter-dimension", methods=["POST"])
    @token_required
    @validate_input(["dimension_id", "value"])
    @handle_errors
    def add_value_to_filter_dimension(current_user):
        data = request.get_json()
        dimension_id = data["dimension_id"]
        new_value = data["value"]

        filter_dimension = FilterDimension.objects.get(id=dimension_id)

        logger.info(f"Filter dimension: {filter_dimension}")

        if new_value not in filter_dimension.values:
            # Update FilterDimension document
            filter_dimension.values.append(new_value)
            filter_dimension.save()

            logger.info(
                f"Value '{new_value}' added to filter dimension '{filter_dimension.name}'"
            )
            return (
                jsonify({"message": f'Value "{new_value}" added to filter dimension.'}),
                200,
            )
        return (
            jsonify(
                {
                    "message": f'Value "{new_value}" already exists in the selected filter dimension.'
                }
            ),
            403,
        )

    @filter_bp.route("/filter_documents", methods=["GET"])
    @token_required
    @handle_errors
    def filter_documents(current_user):
        """Filter documents based on query parameters."""
        return filter_service.filter_documents(
            request.query_string.decode("utf-8"), current_user
        )

    return filter_bp
