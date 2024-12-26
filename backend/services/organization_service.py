from typing import Optional, Any, Union, Tuple, List
from datetime import datetime, timezone, timedelta
import uuid
import re
from werkzeug.security import generate_password_hash, check_password_hash
from loguru import logger

from models.organization import Organization
from models.user_organization import UserOrganization
from models.user import User
from models.invitation import Invitation, RegistrationCode
from models.pending import PendingRequest
from models.chat import Chat
from models.action_log import ActionLog
from services.index_service import IndexService
from utils.error_handlers import log_error
from services.document_ingestion_service import slugify
import calendar
import jwt


class OrganizationService:
    """
    Service for managing organization-related operations.

    This service encapsulates all organization-related business logic and coordinates with other services.
    It follows dependency injection principles and is framework-agnostic.
    """

    VALID_ROLES = ["member", "editor", "admin"]
    VALID_CONTRACT_STATUSES = ["active", "inactive"]
    VALID_MEMBERSHIP_TYPES = ["paid", "free"]
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,30}$")
    PASSWORD_MIN_LENGTH = 8

    def __init__(self, index_service: IndexService):
        """
        Initialize OrganizationService with required dependencies.

        Args:
            index_service: Service for managing indices
        """
        self._index_service = index_service

    def _validate_name(self, name: str) -> None:
        """Validate organization name."""
        if not name or not isinstance(name, str):
            raise ValueError("Organization name must be a non-empty string")
        if len(name.strip()) < 2:
            raise ValueError("Organization name must be at least 2 characters")
        if len(name.strip()) > 100:
            raise ValueError("Organization name must not exceed 100 characters")

    def _validate_password(self, password: str) -> None:
        """Validate organization password."""
        if not password or not isinstance(password, str):
            raise ValueError("Password must be a non-empty string")
        if len(password) < self.PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"Password must be at least {self.PASSWORD_MIN_LENGTH} characters"
            )

    def _validate_email(self, email: str) -> None:
        """Validate email address."""
        if not email or not isinstance(email, str):
            raise ValueError("Email must be a non-empty string")
        if not self.EMAIL_REGEX.match(email):
            raise ValueError("Invalid email format")

    def _validate_email_suffix(self, suffix: str) -> None:
        """Validate email suffix."""
        if not suffix:
            return
        if not isinstance(suffix, str):
            raise ValueError("Email suffix must be a string")
        if not re.match(r"^@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", suffix):
            raise ValueError("Invalid email suffix format")

    def _validate_username(self, username: str) -> None:
        """Validate username."""
        if not username or not isinstance(username, str):
            raise ValueError("Username must be a non-empty string")
        if not self.USERNAME_REGEX.match(username):
            raise ValueError("Invalid username format")

    def _validate_role(self, role: str) -> None:
        """Validate user role."""
        if role not in self.VALID_ROLES:
            raise ValueError(
                f"Invalid role. Must be one of: {', '.join(self.VALID_ROLES)}"
            )

    def _validate_membership_type(self, membership_type: str) -> None:
        """Validate membership type."""
        if membership_type not in self.VALID_MEMBERSHIP_TYPES:
            raise ValueError(
                f"Invalid membership type. Must be one of: {', '.join(self.VALID_MEMBERSHIP_TYPES)}"
            )

    def _validate_contract_status(self, status: str) -> None:
        """Validate contract status."""
        if status not in self.VALID_CONTRACT_STATUSES:
            raise ValueError(
                f"Invalid contract status. Must be one of: {', '.join(self.VALID_CONTRACT_STATUSES)}"
            )

    def _get_organization(self, organization_id: str) -> Organization:
        """Get organization by ID with validation."""
        try:
            organization = Organization.objects.get(id=organization_id)
            return organization
        except Organization.DoesNotExist:
            raise ValueError(f"Organization with ID {organization_id} not found")

    def _get_user(self, user_id: str) -> User:
        """Get user by ID with validation."""
        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            raise ValueError(f"User with ID {user_id} not found")

    def _get_user_by_identifier(self, identifier: str, identifier_type: str) -> User:
        """
        Get user by email or username.

        Args:
            identifier: Email or username to look up
            identifier_type: Type of identifier ('email' or 'username')

        Returns:
            User: The found user

        Raises:
            ValueError: If user not found or invalid identifier type
        """
        if identifier_type not in ["email", "username"]:
            raise ValueError("Invalid identifier type. Must be 'email' or 'username'")

        if identifier_type == "email":
            self._validate_email(identifier)
            user = User.objects(email=identifier).first()
        else:
            self._validate_username(identifier)
            user = User.objects(username=identifier).first()

        if not user:
            raise ValueError(f"User not found with {identifier_type}: {identifier}")

        return user

    def get_user_organizations(self, user_id: str) -> List[Organization]:
        """
        Get all organizations a user belongs to.

        Args:
            user_id: The ID of the user

        Returns:
            List[Organization]: List of organizations the user belongs to

        Raises:
            ValueError: If user not found
        """
        try:
            user = self._get_user(user_id)
            memberships = UserOrganization.objects(user=user.id, is_active=True)
            organizations = [membership.organization for membership in memberships]
            logger.info(f"Retrieved organizations for user {user.username}")
            return organizations
        except Exception as e:
            error_message, _ = log_error(e, f"Getting organizations for user {user_id}")
            raise type(e)(error_message)

    def create_organization(
        self,
        name: str,
        password: str,
        email_suffix: Optional[str] = None,
        creator: Optional[User] = None,
    ) -> Organization:
        """
        Create a new organization with optional email suffix.
        """
        try:
            # Add debug prints
            print(f"\nStarting organization creation for: {name}")

            # Validate inputs
            self._validate_name(name)
            self._validate_password(password)
            if email_suffix:
                self._validate_email_suffix(email_suffix)

            slug_name = slugify(name)
            print(f"Generated slug name: {slug_name}")

            if Organization.objects(slug_name__iexact=slug_name).first():
                raise ValueError(f'Organization "{name}" already exists.')

            # Generate a temporary index name with explicit string conversion
            temp_index_name = str(f"temp_{slug_name}_{uuid.uuid4().hex}")
            print(f"Generated temp index name: {temp_index_name}")

            org_args = {
                "name": str(name),
                "slug_name": str(slug_name),
                "password": str(generate_password_hash(password)),
                "index_name": str(temp_index_name),  # Ensure string
            }
            if email_suffix:
                org_args["email_suffix"] = str(email_suffix.strip().lower())

            print(f"Organization args: {org_args}")

            organization = Organization(**org_args)
            print(
                f"Created organization object with index_name: {organization.index_name}"
            )
            organization.save()
            print("Saved organization with temp index")

            # Create Elasticsearch index with explicit string conversion
            index_name = str(
                self._index_service.create_organization_index(
                    str(organization.id), str(name), str(f"{name}'s Index")
                )
            )
            print(f"Generated permanent index name: {index_name}")

            # Update with actual index name
            organization.index_name = str(index_name)  # Ensure string
            print(
                f"Updating organization with permanent index name: {organization.index_name}"
            )
            organization.save()

            if creator:
                self.manage_member(
                    organization_id=str(organization.id), user=creator, role="admin"
                )
                ActionLog.log_action(
                    creator,
                    "create_org",
                    target_orgs=[organization],
                    description=f"Created organization: {name}",
                )

            logger.info(f"Created organization: {name}")
            return organization

        except Exception as e:
            error_message, _ = log_error(e, f"Organization creation for {name}")
            raise type(e)(error_message)

    def delete_organization(self, organization_id: str, deleter: User) -> None:
        """
        Delete an organization and clean up related resources.

        Args:
            organization_id: ID of organization to delete
            deleter: User performing the deletion

        Raises:
            ValueError: If organization not found or user unauthorized
        """
        try:
            organization = self._get_organization(organization_id)

            # Verify deleter is admin
            if not self.is_admin(deleter, organization):
                raise ValueError("Only admins can delete organizations")

            # Log action before deletion
            ActionLog.log_action(
                deleter,
                "delete_org",
                target_orgs=[organization],
                description=f"Deleted organization: {organization.name}",
            )

            # Delete all user relationships
            UserOrganization.objects(organization=organization.id).delete()

            # Delete the organization's index
            if organization.index_name:
                self._index_service.delete_index(organization.index_name)

            # Delete the organization
            organization.delete()

            logger.info(f"Deleted organization: {organization.name}")

        except Exception as e:
            error_message, _ = log_error(
                e, f"Organization deletion for {organization_id}"
            )
            raise type(e)(error_message)

    def manage_member(
        self,
        organization_id: str,
        user: Optional[User] = None,
        user_identifier: Optional[str] = None,
        identifier_type: Optional[str] = None,
        role: str = "member",
        is_paid: bool = False,
        actor: Optional[User] = None,
    ) -> None:
        """
        Add or update a member in an organization.

        Args:
            organization_id: ID of organization
            user: The user to add/update (optional if user_identifier provided)
            user_identifier: Email or username to look up user (optional if user provided)
            identifier_type: Type of identifier ('email' or 'username')
            role: The role to assign
            is_paid: Whether this is a paid membership
            actor: User performing the action

        Raises:
            ValueError: If validation fails or unauthorized
        """
        try:
            self._validate_role(role)
            organization = self._get_organization(organization_id)

            # Verify actor authorization if provided
            if actor and not self.is_admin(actor, organization):
                raise ValueError("Only admins can manage members")

            # Get user by identifier if not provided directly
            if not user and user_identifier and identifier_type:
                user = self._get_user_by_identifier(user_identifier, identifier_type)
            elif not user:
                raise ValueError(
                    "Either user or user_identifier with type must be provided"
                )

            # Check if user is already a member
            user_org = UserOrganization.objects(
                user=user.id, organization=organization.id
            ).first()

            action_performer = actor if actor else user

            if user_org:
                # Update existing membership
                old_role = user_org.role
                user_org.role = role
                user_org.is_paid = is_paid
                user_org.save()

                ActionLog.log_action(
                    action_performer,
                    "update_user_role",
                    target_orgs=[organization],
                    target_users=[user],
                    description=(
                        f"Updated {user.username}'s role from {old_role} to {role} "
                        f"in organization: {organization.name}"
                    ),
                )
            else:
                # Create new membership
                UserOrganization(
                    user=user,
                    organization=organization,
                    role=role,
                    is_paid=is_paid,
                    index_name=organization.index_name,
                ).save()

                ActionLog.log_action(
                    action_performer,
                    "add_member",
                    target_orgs=[organization],
                    target_users=[user],
                    description=(
                        f"Added {user.username} as {role} to organization: "
                        f"{organization.name}"
                    ),
                )

            logger.info(
                f"{'Updated' if user_org else 'Added'} user {user.username} in "
                f"organization {organization.name} with role {role}"
            )

        except Exception as e:
            error_message, _ = log_error(e, f"Managing member in {organization_id}")
            raise type(e)(error_message)

    def remove_member(
        self, organization_id: str, user: User, remover: Optional[User] = None
    ) -> None:
        """
        Remove a user from an organization.

        Args:
            organization_id: ID of organization
            user: The user to remove
            remover: User performing the removal

        Raises:
            ValueError: If organization not found or unauthorized
        """
        try:
            organization = self._get_organization(organization_id)

            # Verify remover authorization if provided
            if remover and not self.is_admin(remover, organization):
                raise ValueError("Only admins can remove members")

            # Check if user is a member
            user_org = UserOrganization.objects(
                user=user.id, organization=organization.id
            ).first()
            if not user_org:
                raise ValueError(
                    f"User {user.username} is not a member of this organization"
                )

            user_org.delete()

            action_performer = remover if remover else user
            ActionLog.log_action(
                action_performer,
                "remove_user_from_org",
                target_orgs=[organization],
                target_users=[user],
                description=(
                    f"Removed {user.username} from organization: {organization.name}"
                ),
            )

            logger.info(
                f"Removed user {user.username} from organization {organization.name}"
            )

        except Exception as e:
            error_message, _ = log_error(
                e, f"Removing member {user.username} from {organization_id}"
            )
            raise type(e)(error_message)

    def get_members(self, organization_id: str) -> list[dict]:
        """
        Get all members of an organization with their roles.

        Args:
            organization_id: ID of organization

        Returns:
            list[dict]: list of member details

        Raises:
            ValueError: If organization not found
        """
        try:
            organization = self._get_organization(organization_id)
            members = []
            user_orgs = UserOrganization.objects(organization=organization.id)

            for user_org in user_orgs:
                user = user_org.user
                members.append(
                    {
                        "id": str(user.id),
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "role": user_org.role,
                        "is_paid": user_org.is_paid,
                    }
                )

            return members

        except Exception as e:
            error_message, _ = log_error(e, f"Getting members for {organization_id}")
            raise type(e)(error_message)

    def create_invitation(
        self, organization_id: str, email: str, inviter: User
    ) -> Invitation:
        """
        Create an invitation to join an organization.

        Args:
            organization_id: ID of organization
            email: Email address to invite
            inviter: User creating the invitation

        Returns:
            Invitation: The created invitation

        Raises:
            ValueError: If validation fails or unauthorized
        """
        try:
            self._validate_email(email)
            organization = self._get_organization(organization_id)

            # Verify inviter is admin
            if not self.is_admin(inviter, organization):
                raise ValueError("Only admins can create invitations")

            invitation = Invitation(
                organization=organization,
                email=email,
                token=str(uuid.uuid4()),
                sent_at=datetime.now(timezone.utc),
                inviter=inviter,
            )
            invitation.save()

            ActionLog.log_action(
                inviter,
                "create_invitation",
                target_orgs=[organization],
                description=f"Created invitation for {email} to join {organization.name}",
            )

            logger.info(f"Created invitation for {email} to join {organization.name}")
            return invitation

        except Exception as e:
            error_message, _ = log_error(
                e, f"Creating invitation for {email} to {organization_id}"
            )
            raise type(e)(error_message)

    def create_registration_code(
        self, organization_id: str, membership_type: str, creator: User
    ) -> RegistrationCode:
        """
        Create a registration code for an organization.

        Args:
            organization_id: ID of organization
            membership_type: Type of membership ('paid' or 'free')
            creator: User creating the code

        Returns:
            RegistrationCode: The created registration code

        Raises:
            ValueError: If validation fails or unauthorized
        """
        try:
            self._validate_membership_type(membership_type)
            organization = self._get_organization(organization_id)

            # Verify creator is admin
            if not self.is_admin(creator, organization):
                raise ValueError("Only admins can create registration codes")

            code = RegistrationCode(
                code=str(uuid.uuid4()),
                organization=organization,
                membership_type=membership_type,
                creator=creator,
            )
            code.save()

            ActionLog.log_action(
                creator,
                "create_registration_code",
                target_orgs=[organization],
                description=(
                    f"Created {membership_type} registration code for "
                    f"organization: {organization.name}"
                ),
            )

            logger.info(
                f"Created {membership_type} registration code for {organization.name}"
            )
            return code

        except Exception as e:
            error_message, _ = log_error(
                e, f"Creating registration code for {organization_id}"
            )
            raise type(e)(error_message)

    def submit_join_request(
        self, organization_id: str, user: User, message: Optional[str] = ""
    ) -> PendingRequest:
        """
        Submit a request to join an organization.
        Args:
            organization_id: ID of organization
            user: User submitting the request
            message: Optional message with the request
        Returns:
            PendingRequest: The created request
        Raises:
            ValueError: If user already has a pending request
        """
        try:
            organization = self._get_organization(organization_id)
            # Check for existing request
            existing_request = PendingRequest.objects(
                user=user, organization=organization, status="pending"
            ).first()
            if existing_request:
                raise ValueError(
                    "You already have a pending request for this organization."
                )

            request = PendingRequest(
                user=user,
                organization=organization,
                request_message=message,
                first_name=user.first_name,  # Add this
                last_name=user.last_name,  # Add this
                status="pending",  # Explicitly set status
            )
            request.save()

            ActionLog.log_action(
                user,
                "submit_join_request",
                target_orgs=[organization],
                description=f"Submitted request to join {organization.name}",
            )
            logger.info(
                f"Created join request for {user.username} to {organization.name}"
            )
            return request

        except Exception as e:
            error_message, _ = log_error(
                e, f"Creating join request for {user.username} to {organization_id}"
            )
            raise type(e)(error_message)

    def handle_join_request(
        self,
        request_id: str,
        approve: bool,
        membership_type: Optional[str] = None,
        handler: User = None,
    ) -> None:
        """
        Handle (approve/reject) a request to join an organization.

        Args:
            request_id: ID of the request
            approve: Whether to approve the request
            membership_type: Type of membership if approved
            handler: User handling the request

        Raises:
            ValueError: If request not found or validation fails
        """
        try:
            request = PendingRequest.objects.get(id=request_id)
            if not request:
                raise ValueError("Request not found")

            if approve and membership_type:
                self._validate_membership_type(membership_type)

            # Verify handler is admin
            if handler and not self.is_admin(handler, request.organization):
                raise ValueError("Only admins can handle join requests")

            if approve:
                is_paid = membership_type == "paid"
                self.manage_member(
                    str(request.organization.id),
                    request.user,
                    role="member",
                    is_paid=is_paid,
                    actor=handler,
                )

                if is_paid:
                    request.user.subscription_status = "active"
                    request.user.subscription_paid_by = request.organization
                else:
                    request.user.subscription_status = "inactive"
                request.user.save()

            ActionLog.log_action(
                handler if handler else request.user,
                "handle_join_request",
                target_orgs=[request.organization],
                target_users=[request.user],
                description=(
                    f"{'Approved' if approve else 'Rejected'} join request for "
                    f"{request.user.username} to {request.organization.name}"
                ),
            )

            request.delete()

            logger.info(
                f"{'Approved' if approve else 'Rejected'} join request for "
                f"{request.user.username} to {request.organization.name}"
            )

        except Exception as e:
            error_message, _ = log_error(e, f"Handling join request {request_id}")
            raise type(e)(error_message)

    def manage_contract(self, organization_id: str, action: str, actor: User) -> None:
        """
        Manage an organization's contract status.

        Args:
            organization_id: ID of organization
            action: Action to perform ('activate' or 'deactivate')
            actor: User performing the action

        Raises:
            ValueError: If validation fails or unauthorized
        """
        try:
            if action not in ["activate", "deactivate"]:
                raise ValueError("Invalid action. Must be 'activate' or 'deactivate'")

            self._validate_contract_status(
                "active" if action == "activate" else "inactive"
            )
            organization = self._get_organization(organization_id)

            # Verify actor is superadmin
            if not actor.is_superadmin:
                raise ValueError("Only superadmins can manage contracts")

            if action == "activate":
                organization.activate_contract()
            else:
                organization.deactivate_contract()

            ActionLog.log_action(
                actor,
                "update_org_contract",
                target_orgs=[organization],
                description=(
                    f"Changed contract status to {action} for organization: "
                    f"{organization.name}"
                ),
            )

            logger.info(
                f"{action.title()}d contract for organization {organization.name}"
            )

        except Exception as e:
            error_message, _ = log_error(
                e, f"{action.title()}ing contract for {organization_id}"
            )
            raise type(e)(error_message)

    # Access control methods
    def is_admin(self, user: User, organization: Organization) -> bool:
        """Check if user is an admin of the organization."""
        user_org = UserOrganization.objects(
            user=user.id, organization=organization.id, role="admin"
        ).first()
        return bool(user_org)

    def has_access(self, user: User, organization: Union[Organization, str]) -> bool:
        """
        Check if user has access to the organization.

        Args:
            user: User to check access for
            organization: Organization object or ID

        Returns:
            bool: True if user has access

        Raises:
            ValueError: If organization not found
        """
        if isinstance(organization, str):
            organization = self._get_organization(organization)

        user_org = UserOrganization.objects(
            user=user.id, organization=organization.id
        ).first()
        return bool(user_org)

    def verify_password(self, organization_id: str, password: str) -> bool:
        """
        Verify organization password.

        Args:
            organization_id: ID of organization
            password: Password to verify

        Returns:
            bool: True if password matches

        Raises:
            ValueError: If organization not found
        """
        try:
            self._validate_password(password)
            organization = self._get_organization(organization_id)
            return check_password_hash(organization.password, password)
        except Exception as e:
            error_message, _ = log_error(e, f"Verifying password for {organization_id}")
            raise type(e)(error_message)

    def authenticate_admin(
        self,
        organization_id: str,
        password: str,
        secret_key: str,
        expiry_hours: int = 1,
    ) -> Tuple[str, str]:
        """
        Authenticate organization admin and generate token.

        Args:
            organization_id: ID of organization
            password: Password to verify
            secret_key: Key for token generation
            expiry_hours: Token expiry in hours (default: 1)

        Returns:
            tuple[str, str]: (organization_id, token)

        Raises:
            ValueError: If authentication fails
        """
        try:
            organization = self._get_organization(organization_id)

            if not self.verify_password(organization_id, password):
                raise ValueError("Invalid password")

            payload = {
                "organization_id": str(organization.id),
                "organization_name": organization.name,
                "exp": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
            }
            token = jwt.encode(payload, secret_key, algorithm="HS256")

            return str(organization.id), token

        except Exception as e:
            error_message, _ = log_error(
                e, f"Authenticating admin for {organization_id}"
            )
            raise type(e)(error_message)

    # Analytics methods
    def get_user_actions(
        self, user: User, page: int = 1, per_page: int = 20
    ) -> dict[str, Any]:
        """
        Get paginated user actions across their organizations.

        Args:
            user: User to get actions for
            page: Page number (default: 1)
            per_page: Items per page (default: 20)

        Returns:
            dict[str, Any]: Paginated actions with metadata

        Raises:
            ValueError: If validation fails
        """
        try:
            # Get all organizations the user is a member of
            user_organizations = UserOrganization.objects(user=user.id, is_active=True)
            org_ids = [str(uo.organization.id) for uo in user_organizations]

            # Get action logs for all these organizations
            actions = ActionLog.objects(target_orgs__in=org_ids)

            # Sort actions by timestamp (most recent first)
            actions = sorted(actions, key=lambda x: x.timestamp, reverse=True)

            # Implement pagination
            start = (page - 1) * per_page
            end = start + per_page

            # Format actions
            action_list = [
                {
                    "id": str(action.id),
                    "username": action.originating_user.username,
                    "first_name": action.originating_user.first_name,
                    "last_name": action.originating_user.last_name,
                    "action_type": action.action_type,
                    "document_title": (
                        action.target_documents[0].title
                        if action.target_documents
                        else None
                    ),
                    "document_url": (
                        action.target_documents[0].s3_url
                        if action.target_documents
                        else None
                    ),
                    "index_name": (
                        action.target_indices[0].name if action.target_indices else None
                    ),
                    "timestamp": action.timestamp.isoformat(),
                    "organization": (
                        action.target_orgs[0].name if action.target_orgs else None
                    ),
                }
                for action in actions[start:end]
            ]

            return {
                "actions": action_list,
                "total": len(actions),
                "page": page,
                "per_page": per_page,
            }

        except Exception as e:
            error_message, _ = log_error(e, f"Getting user actions for {user.username}")
            raise type(e)(error_message)

    def get_pending_requests(self, organization_id: str) -> list[dict[str, Any]]:
        """
        Get all pending join requests for an organization.

        Args:
            organization_id: ID of organization

        Returns:
            list[dict[str, Any]]: list of pending requests

        Raises:
            ValueError: If organization not found
        """
        try:
            organization = self._get_organization(organization_id)
            pending_requests = PendingRequest.objects(
                organization=organization.id, status="pending"
            )

            return [
                {
                    "request_id": str(req.id),
                    "requesting_user": str(req.user.id),
                    "user_email": req.user.email,
                    "first_name": req.user.first_name,
                    "last_name": req.user.last_name,
                    "organization_name": organization.name,
                    "created_at": req.created_at,
                    "message": req.request_message,
                }
                for req in pending_requests
            ]

        except Exception as e:
            error_message, _ = log_error(
                e, f"Getting pending requests for {organization_id}"
            )
            raise type(e)(error_message)

    def get_message_count_by_month(self, organization_id: str) -> list[dict[str, Any]]:
        """
        Get organization's message count grouped by month.

        Args:
            organization_id: ID of organization

        Returns:
            list[dict[str, Any]]: Message counts by month

        Raises:
            ValueError: If organization not found
        """
        try:
            organization = self._get_organization(organization_id)

            pipeline = [
                {"$match": {"messages.organization": organization.id}},
                {"$unwind": "$messages"},
                {"$match": {"messages.organization": organization.id}},
                {
                    "$group": {
                        "_id": {
                            "month": {"$month": "$messages.timestamp"},
                            "year": {"$year": "$messages.timestamp"},
                        },
                        "total_messages": {"$sum": 1},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "month": "$_id.month",
                        "year": "$_id.year",
                        "total_messages": 1,
                    }
                },
                {"$sort": {"year": 1, "month": 1}},
            ]

            result = list(Chat.objects.aggregate(pipeline))

            # Convert numeric months to month names
            for item in result:
                if isinstance(item.get("month"), int):
                    item["month"] = calendar.month_name[item["month"]]

            return result

        except Exception as e:
            error_message, _ = log_error(
                e, f"Getting message count for {organization_id}"
            )
            raise type(e)(error_message)

    def get_organization_details(self, organization_id: str) -> dict[str, Any]:
        """
        Get detailed organization information.

        Args:
            organization_id: ID of organization

        Returns:
            dict[str, Any]: Organization details

        Raises:
            ValueError: If organization not found
        """
        try:
            organization = self._get_organization(organization_id)

            return {
                "id": organization.id,
                "name": organization.name,
                "email_suffix": organization.email_suffix,
                "index_name": organization.index_name,
                "members": self.get_members(organization_id),
                "organization_contract": organization.organization_contract,
                "has_public_documents": organization.has_public_documents,
                "created_at": organization.created_at,
                "updated_at": organization.updated_at,
            }

        except Exception as e:
            error_message, _ = log_error(e, f"Getting details for {organization_id}")
            raise type(e)(error_message)

    def get_all_organizations(self) -> list[dict[str, Any]]:
        """
        Get a list of all organizations.

        Returns:
            list[dict[str, Any]]: List of organization details

        Raises:
            Exception: If there's an error retrieving organizations
        """
        try:
            organizations = Organization.objects()
            return [
                {"organization_id": str(org.id), "organization_name": org.name}
                for org in organizations
            ]
        except Exception as e:
            error_message, _ = log_error(e, "Getting all organizations")
            raise type(e)(error_message)

    from typing import List, Optional, Dict, Any, Union, Tuple
