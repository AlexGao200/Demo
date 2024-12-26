from flask import Blueprint, jsonify, request
from loguru import logger
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from auth.utils import token_required, validate_input
from models.user import User
from services.user_service import UserService
from services.guest_services import GuestService
from services.organization_service import OrganizationService


def create_user_blueprint(
    limiter, user_service: UserService, organization_service: OrganizationService
):
    user_bp = Blueprint("user", __name__, url_prefix="/api")

    def authorize_user_action(current_user, user_id):
        if not (str(current_user.id) == user_id or current_user.is_superadmin):
            raise Forbidden("Unauthorized access")

    @user_bp.route("/user/<user_id>", methods=["DELETE"])
    @token_required
    @limiter.limit("10/minute")
    def delete_user(current_user: User, user_id):
        """
        Soft delete a user account. This will:
        1. Anonymize personal data
        2. Mark the account as deleted
        3. Cancel any active subscriptions
        4. Archive their personal elasticsearch index
        5. Mark organization memberships as inactive

        Only the user themselves or a superadmin can perform this action.
        """
        try:
            authorize_user_action(current_user, user_id)
            user = user_service.get_user_by_id(user_id)
            if not user:
                raise NotFound("User not found")

            # Get deletion reason if provided
            reason = request.json.get("reason") if request.is_json else None

            # Perform soft deletion
            user_service.soft_delete(user, reason=reason)

            logger.info(f"Successfully deleted user account: {user_id}")
            return (
                jsonify(
                    {
                        "message": "User account successfully deleted",
                        "user_id": str(user_id),
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise

    @user_bp.route("/user/indices", methods=["GET"])
    @token_required
    def get_indices(current_user: User):
        """
        Unified endpoint to get indices for both authenticated users and guest sessions.
        Returns user-specific indices for authenticated users and organization indices for guests.
        """
        try:
            if current_user.is_guest:
                indices = GuestService.get_organization_indices_for_guest()
                logger.info(
                    f"Fetched organization indices for guest session: {current_user.session_id}"
                )
            else:
                indices = user_service.get_user_indices(current_user)
                logger.info(f"Fetched indices for user: {current_user.id}")

            return jsonify({"indices": indices}), 200
        except Exception as e:
            logger.error(
                f"Error fetching indices - User ID: {current_user.id}, Is Guest: {current_user.is_guest}, Error: {str(e)}"
            )
            return jsonify({"error": "Failed to fetch indices"}), 500

    @user_bp.route("/join-organization", methods=["POST"])
    @token_required
    @validate_input(["org_id", "user_id"])
    @limiter.limit("10/minute")
    def join_organization(current_user):
        data = request.get_json()
        org_id = data.get("org_id")
        user_id = data.get("user_id")
        role = data.get("role", "member")  # Default role is 'member'

        authorize_user_action(current_user, user_id)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found")

        try:
            # Using organization_service to check if organization exists
            organization_service.get_organization_details(org_id)
        except ValueError:
            raise NotFound("Organization not found")

        # Using organization_service to check existing membership
        if user_service.get_role_for_organization(user.id, org_id):
            raise BadRequest("User is already a member of this organization")

        # Using organization_service to manage member in organization
        organization_service.manage_member(org_id, user=user, role=role)
        logger.info(f"User {user_id} successfully joined organization {org_id}")
        return jsonify({"message": "Successfully joined the organization"}), 200

    @user_bp.route("/user/<user_id>/set_initial_organization", methods=["POST"])
    @token_required
    @validate_input(["organization_id"])
    @limiter.limit("5/minute")
    def set_initial_organization(current_user, user_id):
        authorize_user_action(current_user, user_id)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found")

        organization_id = request.json.get("organization_id")
        try:
            # Using organization_service to check if organization exists
            organization = organization_service.get_organization_details(
                organization_id
            )
        except ValueError:
            raise NotFound("Organization not found")

        # Using organization_service to set initial organization
        user_service.set_initial_organization(user, organization.get("id"))
        logger.info(
            f"Initial organization set for user {user_id}: {organization.get("id")}"
        )
        return jsonify({"message": "Initial organization set successfully"}), 200

    @user_bp.route("/user/<user_id>/organizations", methods=["GET"])
    @token_required
    @limiter.limit("100/minute")
    def get_user_organizations(current_user, user_id):
        authorize_user_action(current_user, user_id)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found")

        # Using organization_service to get user's organizations
        organizations = organization_service.get_user_organizations(user.id)
        if not organizations:
            logger.info(f"No organizations found for user: {user_id}")
            return jsonify({"organizations": []}), 200

        org_list = []
        for organization in organizations:
            role = user_service.get_role_for_organization(user.id, str(organization.id))
            org_list.append(
                {
                    "id": str(organization.id),
                    "name": organization.name,
                    "role": role,
                    "index_name": organization.index_name,
                }
            )

        logger.info(f"Fetched organizations for user: {user_id}")
        return jsonify({"organizations": org_list}), 200

    @user_bp.route("/user/<user_id>/leave-organization", methods=["POST"])
    @token_required
    @validate_input(["org_id"])
    @limiter.limit("10/minute")
    def leave_organization(current_user, user_id):
        authorize_user_action(current_user, user_id)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found")

        data = request.get_json()
        org_id = data.get("org_id")

        try:
            # Using organization_service to check if organization exists
            organization = organization_service.get_organization_details(org_id)
        except ValueError:
            raise NotFound("Organization not found")

        # Using organization_service to check membership
        if not user_service.get_role_for_organization(user_id, organization.get("id")):
            raise BadRequest("User is not a member of this organization")

        # Using organization_service to remove user from organization
        organization_service.remove_member(organization.get("id"), user)
        logger.info(
            f"User {user_id} successfully left organization {organization.get("id")}"
        )
        return jsonify({"message": "Successfully left the organization"}), 200

    @user_bp.route("/user/<user_id>/roles", methods=["GET"])
    @token_required
    @limiter.limit("100/minute")
    def get_user_roles(current_user, user_id):
        authorize_user_action(current_user, user_id)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found")

        organizations = user_service.get_organizations(user)
        roles = {
            str(org.id): user_service.get_role_for_organization(user.id, org.id)
            for org in organizations
        }

        logger.info(f"Fetched roles for user: {user_id}")
        return jsonify({"roles": roles}), 200

    @user_bp.route("/user/<user_id>/token_limit", methods=["POST"])
    @token_required
    @validate_input(["token_limit"])
    @limiter.limit("10/minute")
    def set_user_token_limit(current_user, user_id):
        authorize_user_action(current_user, user_id)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found")

        data = request.get_json()
        token_limit = data.get("token_limit")

        user_service.set_token_limit(user, token_limit)
        logger.info(f"Token limit updated for user: {user_id}")
        return jsonify({"message": "Token limit updated successfully"}), 200

    return user_bp
