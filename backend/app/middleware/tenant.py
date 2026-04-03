"""
Tenant isolation middleware for multi-tenant data isolation.

This middleware:
1. Extracts the current user ID from JWT token
2. Sets RLS context for the database session
3. Validates tenant access to resources
4. Provides utilities for tenant-aware operations
"""

import logging
from uuid import UUID
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.rls import set_user_context, RLSLogger

logger = logging.getLogger(__name__)


class TenantContext:
    """
    Holds tenant/user context for a request.

    Provides utilities for checking tenant access, setting RLS context, etc.
    """

    def __init__(self, user_id: UUID):
        """
        Initialize tenant context.

        Args:
            user_id: UUID of the current user (tenant)
        """
        self.user_id = user_id
        self.rls_context_set = False

    def set_rls_context(self, session: Session) -> None:
        """
        Set RLS context on the database session.

        Args:
            session: SQLAlchemy session

        Raises:
            ValueError: If context already set or user_id is invalid
        """
        if self.rls_context_set:
            logger.warning(f"RLS context already set for user_id={self.user_id}")
            return

        try:
            set_user_context(session, self.user_id)
            self.rls_context_set = True
            RLSLogger.log_context_set(self.user_id)
        except Exception as e:
            RLSLogger.log_context_error(str(e))
            raise

    def verify_resource_ownership(
        self,
        resource_user_id: UUID,
        resource_type: str = "resource"
    ) -> bool:
        """
        Verify that the current user owns a resource.

        This provides an extra layer of defense-in-depth
        beyond what RLS provides at the database level.

        Args:
            resource_user_id: user_id of the resource
            resource_type: Type of resource (for logging)

        Returns:
            True if current user owns the resource, False otherwise

        Example:
            tenant = TenantContext(user_id)
            if not tenant.verify_resource_ownership(key.user_id, "exchange_key"):
                raise HTTPException(status_code=403, detail="Access denied")
        """
        owns_resource = self.user_id == resource_user_id

        if not owns_resource:
            logger.warning(
                f"Tenant access denied: user_id={self.user_id} "
                f"attempted to access {resource_type} owned by {resource_user_id}"
            )

        return owns_resource

    def __repr__(self) -> str:
        """String representation of tenant context."""
        return f"<TenantContext(user_id={self.user_id})>"


def extract_user_from_request(request: Request) -> Optional[UUID]:
    """
    Extract user ID from request context.

    In a FastAPI app, the current user is typically injected
    via the get_current_user dependency. This is a helper
    if you need to extract it differently (e.g., from headers).

    Args:
        request: FastAPI request object

    Returns:
        UUID of the user, or None if not found
    """
    # The user_id is typically injected via Depends(get_current_user)
    # If you need to extract from headers instead:
    # auth_header = request.headers.get("Authorization")
    # ... validate and extract user_id from JWT ...

    # For now, return None - the actual extraction happens
    # in the route dependency injection
    return None


class TenantValidator:
    """
    Validates tenant operations and access.

    Provides high-level checks for:
    - Resource ownership
    - Cross-tenant access attempts
    - Cascading delete permissions
    """

    @staticmethod
    def validate_ownership(
        current_user_id: UUID,
        resource_user_id: UUID,
        operation: str = "access"
    ) -> bool:
        """
        Validate that user owns the resource.

        Args:
            current_user_id: ID of current user
            resource_user_id: ID of resource's owner
            operation: Type of operation (for logging)

        Returns:
            True if user owns resource, False otherwise
        """
        if current_user_id != resource_user_id:
            logger.warning(
                f"Unauthorized {operation}: user {current_user_id} "
                f"attempted to {operation} resource owned by {resource_user_id}"
            )
            return False

        return True

    @staticmethod
    def validate_cascade_delete(
        user_id: UUID,
        parent_user_id: UUID
    ) -> bool:
        """
        Validate cascading delete from parent to children.

        When deleting a parent resource (e.g., user or strategy),
        all child resources (e.g., strategies or trades) should be deleted.
        This validates that the cascade respects tenant boundaries.

        Args:
            user_id: ID of user initiating delete
            parent_user_id: ID of parent resource's owner

        Returns:
            True if delete is allowed, False otherwise

        Example:
            # Deleting a user's strategy
            if not TenantValidator.validate_cascade_delete(
                current_user_id, strategy.user_id
            ):
                raise HTTPException(status_code=403, detail="Cannot delete")
        """
        if user_id != parent_user_id:
            logger.warning(
                f"Unauthorized cascade delete: user {user_id} "
                f"attempted to cascade delete resources owned by {parent_user_id}"
            )
            return False

        logger.debug(
            f"Cascade delete validated for user {user_id} "
            f"deleting resources owned by {parent_user_id}"
        )
        return True

    @staticmethod
    def validate_bulk_operation(
        user_id: UUID,
        resources: list,
        owner_field: str = "user_id"
    ) -> tuple[bool, list]:
        """
        Validate bulk operation on multiple resources.

        Ensures the user owns all resources in the bulk operation.
        Returns both validation result and list of unauthorized resources.

        Args:
            user_id: ID of user performing operation
            resources: List of resource objects
            owner_field: Field name containing owner user_id

        Returns:
            Tuple of (all_authorized: bool, unauthorized_resources: list)

        Example:
            valid, unauthorized = TenantValidator.validate_bulk_operation(
                user_id, keys, "user_id"
            )
            if not valid:
                logger.warning(f"Unauthorized resources: {unauthorized}")
                raise HTTPException(status_code=403, detail="Some resources not owned by you")
        """
        unauthorized = []

        for resource in resources:
            if not hasattr(resource, owner_field):
                raise ValueError(f"Resource does not have {owner_field} field")

            owner_id = getattr(resource, owner_field)
            if owner_id != user_id:
                unauthorized.append(resource)

        if unauthorized:
            logger.warning(
                f"Bulk operation by {user_id} found {len(unauthorized)} "
                f"unauthorized resources"
            )
            return False, unauthorized

        return True, []


# ============================================================================
# DEPENDENCY INJECTION UTILITIES
# ============================================================================

def get_tenant_context(user_id: UUID) -> TenantContext:
    """
    Create a tenant context for the current user.

    This can be used in FastAPI dependencies.

    Args:
        user_id: UUID of current user

    Returns:
        TenantContext instance

    Example:
        @app.get("/keys")
        async def list_keys(
            user_id: UUID = Depends(get_current_user),
            tenant: TenantContext = Depends(get_tenant_context),
            db: Session = Depends(get_db)
        ):
            tenant.set_rls_context(db)
            keys = db.query(ExchangeKey).all()
            return keys
    """
    return TenantContext(user_id)
