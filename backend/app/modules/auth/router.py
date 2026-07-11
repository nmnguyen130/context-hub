from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_current_admin_user,
    get_current_user,
    get_uow,
)
from app.core.uow import UnitOfWork
from app.core.enums import InvitationStatus
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    InvitationCreateRequest,
    InvitationResponse,
    JoinRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserRoleUpdateRequest,
    UserUpdateRequest,
)
from app.modules.auth.services import (
    AuthService,
    InvitationService,
    RegistrationService,
    UserService,
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
user_router = APIRouter(prefix="/users", tags=["User Management"])


# Auth Endpoints


@auth_router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterRequest,
    reg_service: RegistrationService = Depends(),
):
    """Registers a new tenant and its admin user."""
    user, _ = await reg_service.register(data)
    return user


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(),
):
    """Authenticates credentials and returns tokens."""
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
    """Refreshes the session."""
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
    """Logs out of the current device."""
    await auth_service.logout(data.refresh_token)


@auth_router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(),
):
    """Logs out of all devices."""
    await auth_service.logout_all(current_user.id, current_user.tenant_id)


@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Gets current user profile."""
    return current_user


@auth_router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    """Updates profile details."""
    user = await user_service.update_profile(current_user.id, data)
    await uow.commit()
    return user


@auth_router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    """Changes password."""
    await user_service.change_password(current_user.id, data)
    await uow.commit()


# Invitation Endpoints (Admin Only, except Accept)


@auth_router.post(
    "/invitations", response_model=dict, status_code=status.HTTP_201_CREATED
)
async def invite_user(
    data: InvitationCreateRequest,
    current_user: User = Depends(get_current_admin_user),
    invite_service: InvitationService = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    """Creates an invitation. Admin only."""
    invitation, raw_token = await invite_service.create_invitation(
        tenant_id=current_user.tenant_id,
        invited_by=current_user.id,
        data=data,
    )
    await uow.commit()
    return {
        "invitation_id": str(invitation.id),
        "email": invitation.email,
        "role": invitation.role,
        "invite_token": raw_token,
        "expires_at": invitation.expires_at.isoformat(),
    }


@auth_router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    status: InvitationStatus | None = Query(
        None, description="Filter by status (PENDING, ACCEPTED, REVOKED, EXPIRED)"
    ),
    current_user: User = Depends(get_current_admin_user),
    invite_service: InvitationService = Depends(),
):
    """Lists invitations. Admin only."""
    return await invite_service.list_invitations(current_user.tenant_id, status=status)


@auth_router.delete("/invitations/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    id: UUID,
    current_user: User = Depends(get_current_admin_user),
    invite_service: InvitationService = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    """Revokes an invitation. Admin only."""
    await invite_service.revoke_invitation(
        tenant_id=current_user.tenant_id,
        invitation_id=id,
    )
    await uow.commit()


@auth_router.post("/invitations/{id}/resend", response_model=dict)
async def resend_invitation(
    id: UUID,
    current_user: User = Depends(get_current_admin_user),
    invite_service: InvitationService = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    """Resends/regenerates an invitation. Admin only."""
    invitation, raw_token = await invite_service.resend_invitation(
        tenant_id=current_user.tenant_id,
        invitation_id=id,
        resending_user_id=current_user.id,
    )
    await uow.commit()
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
    """Accepts an invitation."""
    return await reg_service.join_via_invitation(data)


# User Management Endpoints (Admin Only)


@user_router.get("", response_model=dict)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(),
):
    """Lists users. Admin only."""
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
    id: UUID,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(),
):
    """Gets user details. Admin only."""
    return await user_service.get_user(current_user.tenant_id, id)


@user_router.patch("/{id}/role", response_model=UserResponse)
async def update_user_role(
    id: UUID,
    data: UserRoleUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    """Updates user role. Admin only."""
    user = await user_service.update_role(
        current_user.tenant_id, id, data, acting_user_id=current_user.id
    )
    await uow.commit()
    return user


@user_router.post("/{id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    id: UUID,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    """Deactivates a user. Admin only."""
    await user_service.deactivate(
        current_user.tenant_id, id, acting_user_id=current_user.id
    )
    await uow.commit()


@user_router.post("/{id}/reactivate", status_code=status.HTTP_204_NO_CONTENT)
async def reactivate_user(
    id: UUID,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    """Reactivates a user. Admin only."""
    await user_service.reactivate(
        current_user.tenant_id, id, acting_user_id=current_user.id
    )
    await uow.commit()
