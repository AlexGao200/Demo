from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid
from loguru import logger

from models.user import User
from models.user_organization import UserOrganization
from models.organization import Organization
from services.index_service import IndexService
from services.stripe_service import StripeService


class UserService:
    """
    Service for managing user-related operations.

    This service encapsulates all user-related business logic and coordinates with other services.
    It follows dependency injection principles and is framework-agnostic.
    """

    def __init__(
        self,
        index_service: IndexService,
        stripe_service: Optional[StripeService] = None,
    ):
        """
        Initialize UserService with required dependencies.

        Args:
            index_service: Service for managing indices
            stripe_service: Optional service for managing Stripe operations
        """
        self._index_service = index_service
        self._stripe_service = stripe_service

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by their username.

        Args:
            username: The username to look up

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        try:
            return User.objects(username=username).first()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {str(e)}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get a user by their ID.

        Args:
            user_id: The user ID to look up

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        try:
            return User.objects(id=user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None

    def create_user_index(self, user: User) -> Optional[str]:
        """
        Create a personal index for a user.

        Args:
            user: The user to create an index for

        Returns:
            str: The name of the created index, or None if creation failed
        """
        try:
            index_name = self._index_service.create_user_index(
                str(user.id),
                user.username,
                f"{user.first_name} {user.last_name}'s Personal Index",
            )
            logger.info(f"Created personal index {index_name} for user {user.username}")
            return index_name
        except Exception as e:
            logger.error(
                f"Error creating personal index for user {user.username}: {str(e)}"
            )
            return None

    def archive_user_index(self, user: User) -> bool:
        """
        Archive a user's personal index.

        Args:
            user: The user whose index should be archived

        Returns:
            bool: True if archival was successful, False otherwise
        """
        try:
            if user.personal_index_name:
                archived_name = self._index_service.archive_index(
                    user.personal_index_name
                )
                logger.info(
                    f"Archived index {user.personal_index_name} to {archived_name} "
                    f"for user {user.username}"
                )
                return True
            return False
        except Exception as e:
            logger.error(
                f"Error archiving index {user.personal_index_name} "
                f"for user {user.username}: {str(e)}"
            )
            return False

    def blacklist_token(self, user: User, token: str) -> None:
        """
        Add a token to the user's blacklist.

        Args:
            user: The user whose tokens to manage
            token: The token to blacklist
        """
        if token not in user.blacklisted_tokens:
            user.blacklisted_tokens.append(token)
            user.save()
            logger.info(f"Token blacklisted for user {user.username}")

    def is_token_blacklisted(self, user: User, token: str) -> bool:
        """
        Check if a token is blacklisted for a user.

        Args:
            user: The user whose tokens to check
            token: The token to verify

        Returns:
            bool: True if token is blacklisted, False otherwise
        """
        return token in user.blacklisted_tokens

    def soft_delete(self, user: User, reason: Optional[str] = None) -> None:
        """
        Soft delete a user account by anonymizing personal data and marking as deleted.

        Args:
            user: The user to delete
            reason: Optional reason for deletion
        """
        try:
            # Cancel Stripe subscription if it exists
            if self._stripe_service and user.stripe_subscription_id:
                try:
                    self._stripe_service.cancel_subscription(
                        user.stripe_subscription_id
                    )
                except Exception as e:
                    logger.error(
                        f"Error canceling subscription for user {user.id}: {str(e)}"
                    )
                    # Continue with deletion even if subscription cancellation fails

            # Generate anonymous identifier
            anon_id = f"deleted_user_{str(uuid.uuid4())[:8]}"

            # Update user fields
            user.update(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                deletion_reason=reason,
                email=f"{anon_id}@deleted.user",
                username=anon_id,
                first_name="Deleted",
                last_name="User",
                password="DELETED",
                is_verified=False,
                verification_token=None,
                reset_token=None,
            )

            # Mark organization memberships as inactive
            UserOrganization.objects(user=user.id).update(set__is_active=False)

            # Archive personal index
            self.archive_user_index(user)

            logger.info(f"User {user.username} successfully deleted")
        except Exception as e:
            logger.error(f"Error during user deletion for {user.username}: {str(e)}")
            raise

    def get_role_for_organization(
        self, user_id: str, organization_id: str
    ) -> Optional[str]:
        """
        Get user's role in an organization.

        Args:
            user: The user whose role to check
            organization_id: The organization's ID

        Returns:
            str: The user's role, or None if not a member
        """
        membership = UserOrganization.objects(
            user=user_id, organization=organization_id
        ).first()
        return membership.role if membership else None

    def set_role_for_organization(
        self, user: User, organization_id: str, role: str
    ) -> None:
        """
        Set user's role in an organization.

        Args:
            user: The user whose role to set
            organization_id: The organization's ID
            role: The role to assign
        """
        UserOrganization.objects(user=user.id, organization=organization_id).update_one(
            set__role=role, upsert=True
        )
        logger.info(
            f"Updated role to {role} for user {user.username} in org {organization_id}"
        )

    def get_organizations(self, user: User) -> list[Organization]:
        """
        Get all organizations the user belongs to.

        Args:
            user: The user whose organizations to retrieve

        Returns:
            list[Organization]: list of organizations the user belongs to
        """
        memberships = UserOrganization.objects(user=user.id)
        return [membership.organization for membership in memberships]

    def get_organization_index_names(self, user: User) -> list[str]:
        """
        Get index names of all organizations the user belongs to.

        Args:
            user: The user whose organization indices to retrieve

        Returns:
            list[str]: list of organization index names
        """
        memberships = UserOrganization.objects(user=user.id)
        org_ids = [membership.organization.id for membership in memberships]
        organizations = Organization.objects(id__in=org_ids)
        return [org.index_name for org in organizations if org.index_name]

    def add_to_organization(
        self, user: User, organization: Organization, role: str
    ) -> None:
        """
        Add user to an organization with specified role.

        Args:
            user: The user to add
            organization: The organization to add the user to
            role: The role to assign
        """
        UserOrganization(
            user=user,
            organization=organization,
            role=role,
            index_name=organization.index_name,
        ).save()
        logger.info(f"Added user {user.username} to organization {organization.name}")

    def remove_from_organization(self, user: User, organization: Organization) -> None:
        """
        Remove user from an organization.

        Args:
            user: The user to remove
            organization: The organization to remove the user from
        """
        UserOrganization.objects(user=user.id, organization=organization.id).delete()
        logger.info(
            f"Removed user {user.username} from organization {organization.name}"
        )

    def generate_verification_token(self, user: User) -> None:
        """
        Generate new verification token for user.

        Args:
            user: The user to generate token for
        """
        user.verification_token = str(uuid.uuid4())
        user.verification_expiration = datetime.now(timezone.utc) + timedelta(days=1)
        user.save()
        logger.info(f"Generated verification token for user {user.username}")

    def manage_subscription(self, user: User, updates: dict) -> None:
        """
        Manage user's subscription details.

        Args:
            user: The user whose subscription to manage
            updates: Dictionary of subscription fields to update
        """
        allowed_fields = {
            "subscription_status",
            "subscription_paid_by",
            "subscription_start_date",
            "subscription_end_date",
            "cycle_token_limit",
            "stripe_customer_id",
            "stripe_subscription_id",
            "subscription_plan_name",
            "has_failed_payment",
        }

        update_dict = {k: v for k, v in updates.items() if k in allowed_fields}
        if update_dict:
            user.update(**update_dict)
            logger.info(f"Updated subscription details for user {user.username}")

    def manage_message_counts(self, user: User, action: str) -> None:
        """
        Manage user's message counts.

        Args:
            user: The user whose counts to manage
            action: The action to perform ('increment' or 'reset')
        """
        if action == "increment":
            user.current_cycle_message_count += 1
            user.total_message_count += 1
            user.save()
        elif action == "reset":
            user.current_cycle_message_count = 0
            user.save()
        logger.info(f"Updated message counts for user {user.username}: {action}")

    def has_reached_message_limit(self, user: User) -> bool:
        """
        Check if user has reached their message limit.

        Args:
            user: The user to check

        Returns:
            bool: True if limit reached, False otherwise
        """
        if user.cycle_token_limit is None:
            return False
        return user.current_cycle_message_count >= user.cycle_token_limit

    def get_user_indices(self, user: User) -> List[Dict]:
        """
        Get all indices accessible to a user, including personal and organization indices.

        Args:
            user: The user whose indices to retrieve

        Returns:
            List[Dict]: List of indices with their metadata
        """
        indices = []

        # Get personal index directly from index service
        try:
            personal_indices = self._index_service.list_indices(
                entity_type="user", entity_id=str(user.id)
            )
            if personal_indices:
                indices.append(
                    {
                        "display_name": personal_indices[0].index_display_name,
                        "visibility_options_for_user": ["private"],
                        "name": personal_indices[0].index_name,
                        "role_of_current_user": "admin",
                    }
                )
                # Update user's personal_index_name if not set
                if not user.personal_index_name:
                    user.personal_index_name = personal_indices[0].index_name
                    user.save()
                    logger.info(f"Updated personal_index_name for user {user.username}")
        except Exception as e:
            logger.warning(
                f"Error fetching personal index for user {user.id}: {str(e)}"
            )

        # Add organization indices
        user_organizations = UserOrganization.objects(user=user)
        for user_org in user_organizations:
            org = user_org.organization
            visibilities = (
                ["private", "public"]
                if user_org.role in ["admin", "editor"]
                else ["private", "petition"]
            )
            indices.append(
                {
                    "display_name": org.name,
                    "visibility_options_for_user": visibilities,
                    "name": org.index_name,
                    "role_of_current_user": user_org.role,
                }
            )

        return indices

    def set_token_limit(self, user: User, token_limit: int) -> None:
        """
        Set the token limit for a user.

        Args:
            user: The user whose token limit to set
            token_limit: The new token limit
        """
        user.cycle_token_limit = token_limit
        user.save()
        logger.info(f"Updated token limit for user {user.username} to {token_limit}")

    def set_initial_organization(self, user: User, organization_id: str) -> None:
        """
        Set the initial organization for a user and add them as a member.

        Args:
            user: The user whose initial organization to set
            organization: The organization to set as initial
        """
        organization = Organization.objects(id=organization_id).first()
        user.initial_organization = organization
        user.save()
        self.add_to_organization(user, organization, "member")
        logger.info(
            f"Set initial organization {organization.name} for user {user.username}"
        )
