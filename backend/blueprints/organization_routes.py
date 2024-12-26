from utils.error_handlers import handle_errors
from flask_mail import Message as MailMessage
from models.user import User
from flask import make_response, Blueprint, jsonify, request, current_app
from auth.utils import (
    token_required,
    validate_input,
    role_required,
    superadmin_required,
)
from services.organization_service import OrganizationService


def create_organization_blueprint(
    email_service, organization_service: OrganizationService
):
    organization_bp = Blueprint(
        "organization", __name__, url_prefix="/api/organization"
    )

    @organization_bp.route("/create_organization", methods=["POST"])
    @token_required
    @validate_input(["name", "organization_password"])
    @handle_errors
    def create_organization(current_user):
        data = request.get_json()
        organization = organization_service.create_organization(
            name=data.get("name"),
            password=data.get("organization_password").strip(),
            email_suffix=data.get("email_suffix", "").strip().lower(),
            creator=current_user,
        )
        return jsonify(
            {
                "message": "Organization created successfully",
                "organization_id": str(organization.id),
            }
        ), 201

    @organization_bp.route("/get-all", methods=["GET"])
    @token_required
    @handle_errors
    def get_all_organizations(current_user):
        organizations = organization_service.get_all_organizations()
        return jsonify({"organizations": organizations}), 200

    @organization_bp.route("/add_admin", methods=["POST"])
    @token_required
    @validate_input(["organization_id", "password"])
    @handle_errors
    def add_admin(current_user):
        data = request.get_json()

        # Verify organization password
        if not organization_service.verify_password(
            data.get("organization_id"), data.get("password")
        ):
            return jsonify({"error": "Invalid organization password"}), 403

        # Look up the user by email or username
        user = None
        if data.get("email"):
            user = User.objects(email=data.get("email")).first()
        elif data.get("username"):
            user = User.objects(username=data.get("username")).first()
        else:
            return jsonify({"error": "Either email or username must be provided"}), 400

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Add/update user as admin
        organization_service.manage_member(
            organization_id=data.get("organization_id"),
            user=user,
            role="admin",
            actor=current_user,
        )

        return jsonify(
            {
                "message": f"{user.first_name} {user.last_name} has been added/updated as an admin."
            }
        ), 200

    @organization_bp.route("/check_admin_access", methods=["POST"])
    @token_required
    @validate_input(["organization_id"])
    @handle_errors
    def check_admin_access(current_user):
        data = request.get_json()
        org_id = data.get("organization_id")

        organization = organization_service._get_organization(org_id)
        if organization_service.is_admin(current_user, organization):
            return jsonify(
                {
                    "message": "Access granted",
                    "dashboard_url": f"/organization/{org_id}",
                }
            ), 200
        return jsonify({"error": "Access denied"}), 403

    @organization_bp.route("/invite", methods=["POST"])
    @token_required
    @role_required("admin")
    @validate_input(["email", "organization_id"])
    @handle_errors
    def send_invitation(current_user):
        data = request.get_json()
        invitation = organization_service.create_invitation(
            organization_id=data.get("organization_id"),
            email=data.get("email"),
            inviter=current_user,
        )

        invite_url = f"{current_app.config['FRONTEND_BASE_URL']}/register?token={invitation.token}"

        email_message = MailMessage(
            subject="Invitation to join an organization",
            sender=email_service.mail.default_sender,
            recipients=[data.get("email")],
            body=f"You have been invited to join {invitation.organization.name}. Click here to register: {invite_url}",
        )
        email_service.mail.send(email_message)
        return jsonify({"message": "Invitation sent successfully"}), 200

    @organization_bp.route("/join-request", methods=["POST"])
    @validate_input(["organization_id"])
    @handle_errors
    @token_required  # Move this to be the innermost decorator
    def submit_join_request(user):  # Must match what token_required passes
        data = request.get_json()
        organization_service.submit_join_request(
            organization_id=data.get("organization_id"),
            user=user,  # Use the user object passed by token_required
            message=data.get("message", ""),
        )
        return jsonify(
            {"message": "Request to join organization submitted successfully."}
        ), 201

    @organization_bp.route("/<organization_id>", methods=["DELETE"])
    @token_required
    @validate_input(["organization_id"])
    @handle_errors
    def delete_organization(current_user, organization_id):
        organization_service.delete_organization(
            organization_id=organization_id, deleter=current_user
        )
        return jsonify({"message": "Organization deleted successfully"}), 200

    @organization_bp.route("/pending-requests/<organization_id>", methods=["GET"])
    @token_required
    @role_required("admin")
    @handle_errors
    def get_pending_requests(current_user, organization_id):
        pending_requests = organization_service.get_pending_requests(organization_id)
        return jsonify({"pending_requests": pending_requests}), 200

    @organization_bp.route("/approve-request", methods=["POST"])
    @token_required
    @role_required("admin")
    @validate_input(["request_id", "approve", "organization_id"])
    @handle_errors
    def approve_request(current_user):
        data = request.get_json()
        organization_service.handle_join_request(
            request_id=data.get("request_id"),
            approve=data.get("approve"),
            membership_type=data.get("membershipType"),
            handler=current_user,
        )
        return jsonify({"message": "Request handled successfully"}), 200

    @organization_bp.route("/update_member_role", methods=["POST"])
    @token_required
    @role_required("admin")
    @validate_input(["username", "new_role", "organization_id"])
    @handle_errors
    def update_member_role(current_user):
        data = request.get_json()
        user = User.objects(username=data.get("username")).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        organization_service.manage_member(
            organization_id=data.get("organization_id"),
            user=user,
            role=data.get("new_role"),
            actor=current_user,
        )

        return jsonify(
            {"message": f"User {user.username} role updated to {data.get('new_role')}"}
        ), 200

    @organization_bp.route("/<org_id>/members", methods=["GET"])
    @token_required
    @handle_errors
    def get_organization_members(current_user, org_id):
        organization = organization_service._get_organization(org_id)
        if not organization_service.has_access(current_user, organization):
            return jsonify({"error": "Unauthorized"}), 403

        members = organization_service.get_members(org_id)
        return jsonify({"members": members}), 200

    @organization_bp.route("/user_actions", methods=["GET"])
    @token_required
    @handle_errors
    def get_user_actions(current_user):
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))

        result = organization_service.get_user_actions(
            user=current_user, page=page, per_page=per_page
        )
        return jsonify(result), 200

    @organization_bp.route("/authenticate", methods=["POST"])
    @validate_input(["org_id", "password"])
    @handle_errors
    def authenticate_admin():
        data = request.get_json()
        org_id, token = organization_service.authenticate_admin(
            organization_id=data.get("org_id"),
            password=data.get("password"),
            secret_key=current_app.config["SECRET_KEY"],
        )

        response = make_response(
            jsonify({"success": True, "organization_id": org_id}), 200
        )
        response.set_cookie("org_token", token, httponly=True)
        return response

    @organization_bp.route("/<organization_id>", methods=["GET"])
    @token_required
    @handle_errors
    def get_organization_details(current_user, organization_id):
        organization = organization_service._get_organization(organization_id)
        if not organization_service.has_access(current_user, organization):
            return jsonify({"error": "Unauthorized"}), 403

        details = organization_service.get_organization_details(organization_id)
        return jsonify(details), 200

    @organization_bp.route("/message_count_by_org", methods=["POST"])
    @token_required
    @validate_input(["org_id"])
    @handle_errors
    def message_count_by_org(current_user):
        data = request.get_json()
        org_id = data.get("org_id").strip().lower()

        organization = organization_service._get_organization(org_id)
        if not organization_service.has_access(current_user, organization):
            return jsonify({"error": "Unauthorized"}), 403

        result = organization_service.get_message_count_by_month(org_id)
        return jsonify(result)

    @organization_bp.route("/change_contract_status", methods=["POST"])
    @token_required
    @superadmin_required
    @validate_input(["org_id", "new_status"])
    @handle_errors
    def change_contract_status(current_user):
        data = request.get_json()
        try:
            organization_service.manage_contract(
                organization_id=data.get("org_id"),
                action="activate"
                if data.get("new_status") == "active"
                else "deactivate",
                actor=current_user,
            )
            return jsonify(
                {
                    "message": f"Organization contract status changed to {data.get('new_status')}."
                }
            ), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @organization_bp.route("/generate_registration_code", methods=["POST"])
    @token_required
    @role_required("admin")
    @validate_input(["membership_type", "organization_id"])
    @handle_errors
    def generate_registration_code(current_user):
        data = request.get_json()
        registration_code = organization_service.create_registration_code(
            organization_id=data.get("organization_id"),
            membership_type=data.get("membership_type"),
            creator=current_user,
        )

        registration_link = f"{current_app.config['FRONTEND_BASE_URL']}/register?code={registration_code.code}"

        return jsonify(
            {
                "message": "Registration link generated",
                "registration_link": registration_link,
            }
        ), 201

    return organization_bp
