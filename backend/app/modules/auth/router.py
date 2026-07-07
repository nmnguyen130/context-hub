from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_current_admin_user,
    get_current_user,
)
from app.core.enums import InvitationStatus
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    InviteCreateRequest,
    InviteResponse,
    JoinRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserRoleUpdateRequest,
    UserUpdateRequest,
)
from app.modules.auth.services.auth_service import AuthService
from app.modules.auth.services.invitation_service import InvitationService
from app.modules.auth.services.registration_service import RegistrationService
from app.modules.auth.services.user_service import UserService

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
user_router = APIRouter(prefix="/users", tags=["User Management"])


# ============================================================
# Auth Endpoints
# ============================================================


@auth_router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterRequest,
    reg_service: RegistrationService = Depends(),
):
    """Registers a new tenant organization along with its first Administrator user."""
    user, _ = await reg_service.register(data)
    return user


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(),
):
    """Authenticates credentials and returns a stateless access token and DB-stored refresh token."""
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("user-agent")

    return await auth_service.login(
        data, ip_address=ip_address, device_info=device_info
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    request: Request,
    auth_service: AuthService = Depends(),
):
    """Refreshes the session. Performs token rotation and theft detection."""
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("user-agent")

    return await auth_service.refresh(
        data.refresh_token, ip_address=ip_address, device_info=device_info
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequest,
    auth_service: AuthService = Depends(),
):
    """Revokes a specific refresh token session (logs out of current device)."""
    await auth_service.logout(data.refresh_token)


@auth_router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(),
):
    """Revokes ALL active refresh token sessions for the authenticated user (logs out of all devices)."""
    await auth_service.logout_all(current_user.id, current_user.tenant_id)


@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieves profile info for the currently authenticated user."""
    return current_user


@auth_router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(),
):
    """Allows a user to self-update their first name and last name."""
    return await user_service.update_profile(current_user.id, data)


@auth_router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(),
):
    """Allows a user to change their password after verifying the old one. Invalidates all active sessions."""
    await user_service.change_password(current_user.id, data)


# ============================================================
# Invitation Endpoints (Admin Only, except Accept)
# ============================================================


@auth_router.post(
    "/invitations", response_model=dict, status_code=status.HTTP_201_CREATED
)
async def invite_user(
    data: InviteCreateRequest,
    current_user: User = Depends(get_current_admin_user),
    invite_service: InvitationService = Depends(),
):
    """Creates a new user invitation and returns the raw invitation link/token. Admin only."""
    invitation, raw_token = await invite_service.create(
        tenant_id=current_user.tenant_id,
        invited_by=current_user.id,
        data=data,
    )
    return {
        "invitation_id": str(invitation.id),
        "email": invitation.email,
        "role": invitation.role,
        "invite_token": raw_token,
        "expires_at": invitation.expires_at.isoformat(),
    }


@auth_router.get("/invitations", response_model=list[InviteResponse])
async def list_invitations(
    status: InvitationStatus | None = Query(
        None, description="Filter by status (PENDING, ACCEPTED, REVOKED, EXPIRED)"
    ),
    current_user: User = Depends(get_current_admin_user),
    invite_service: InvitationService = Depends(),
):
    """Lists invitations sent by this tenant organization. Admin only."""
    return await invite_service.list_invitations(current_user.tenant_id, status=status)


@auth_router.delete("/invitations/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    id: str,
    current_user: User = Depends(get_current_admin_user),
    invite_service: InvitationService = Depends(),
):
    """Revokes a pending user invitation. Admin only."""
    # Convert id string to UUID
    try:
        uuid_id = UUID(id)
    except ValueError:
        raise ValueError("Invalid invitation ID format")

    await invite_service.revoke(
        tenant_id=current_user.tenant_id,
        invitation_id=uuid_id,
        revoked_by=current_user.id,
    )


@auth_router.post("/invitations/{id}/resend", response_model=dict)
async def resend_invitation(
    id: str,
    current_user: User = Depends(get_current_admin_user),
    invite_service: InvitationService = Depends(),
):
    """Resends/regenerates a pending or expired invitation. Admin only."""
    try:
        uuid_id = UUID(id)
    except ValueError:
        raise ValueError("Invalid invitation ID format")

    invitation, raw_token = await invite_service.resend(
        tenant_id=current_user.tenant_id,
        invitation_id=uuid_id,
        resending_user_id=current_user.id,
    )
    return {
        "invitation_id": str(invitation.id),
        "email": invitation.email,
        "invite_token": raw_token,
        "expires_at": invitation.expires_at.isoformat(),
    }


@auth_router.post(
    "/invitations/accept",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def accept_invitation(
    data: JoinRequest,
    reg_service: RegistrationService = Depends(),
):
    """Registers a user into the system by accepting a valid invitation token. Publicly accessible."""
    return await reg_service.join_via_invitation(data)


# ============================================================
# User Management Endpoints (Admin Only)
# ============================================================


@user_router.get("", response_model=dict)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(),
):
    """Lists users in the organization with pagination and filtering. Admin only."""
    users, total = await user_service.list_users(
        current_user.tenant_id, skip=skip, limit=limit, is_active=is_active
    )
    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@user_router.get("/{id}", response_model=UserResponse)
async def get_user(
    id: str,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(),
):
    """Retrieves profile details of a user inside the organization. Admin only."""
    try:
        uuid_id = UUID(id)
    except ValueError:
        raise ValueError("Invalid user ID format")
    return await user_service.get_user(current_user.tenant_id, uuid_id)


@user_router.patch("/{id}/role", response_model=UserResponse)
async def update_user_role(
    id: str,
    data: UserRoleUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(),
):
    """Changes a user's role. Admin only."""
    try:
        uuid_id = UUID(id)
    except ValueError:
        raise ValueError("Invalid user ID format")
    return await user_service.update_role(
        current_user.tenant_id, uuid_id, data, acting_user_id=current_user.id
    )


@user_router.post("/{id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    id: str,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(),
):
    """Deactivates a user account and revokes all active session tokens. Admin only."""
    try:
        uuid_id = UUID(id)
    except ValueError:
        raise ValueError("Invalid user ID format")
    await user_service.deactivate(
        current_user.tenant_id, uuid_id, acting_user_id=current_user.id
    )


@user_router.post("/{id}/reactivate", status_code=status.HTTP_204_NO_CONTENT)
async def reactivate_user(
    id: str,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(),
):
    """Re-enables a deactivated user account. Admin only."""
    try:
        uuid_id = UUID(id)
    except ValueError:
        raise ValueError("Invalid user ID format")
    await user_service.reactivate(
        current_user.tenant_id, uuid_id, acting_user_id=current_user.id
    )
