from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status

from app.api.dependencies import (
    get_authenticated_context,
    get_service,
    require_roles,
)
from app.core.context import RequestContext, UserRole
from app.core.pagination import PaginatedResponse, PaginationParams
from app.modules.auth.models import InvitationStatus
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    InvitationAccept,
    InvitationCreate,
    InvitationResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserUpdate,
)
from app.modules.auth.services import (
    AuthService,
    InvitationService,
    RegistrationService,
    UserService,
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


# 1. Public Authentication & Registration Endpoints (RLS Bypassed via Admin UoW)


@auth_router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterRequest,
    reg_service: RegistrationService = Depends(
        get_service(RegistrationService, public=True)
    ),
):
    """Public signup to register a new Tenant organization and its first Administrator user."""
    user, _ = await reg_service.register(data)
    await reg_service.uow.commit()
    return user


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    x_tenant_slug: str = Header(..., description="Tenant organization slug identifier"),
    auth_service: AuthService = Depends(get_service(AuthService, public=True)),
):
    """Authenticates a user and issues a TokenResponse (Access + Refresh tokens)."""
    tokens = await auth_service.login(data, tenant_slug=x_tenant_slug)
    await auth_service.uow.commit()
    return tokens


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    auth_service: AuthService = Depends(get_service(AuthService, public=True)),
):
    """Refreshes active user tokens using a valid RefreshToken."""
    tokens = await auth_service.refresh(data.refresh_token)
    await auth_service.uow.commit()
    return tokens


@auth_router.post(
    "/invitations/accept",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def accept_invitation(
    data: InvitationAccept,
    reg_service: RegistrationService = Depends(
        get_service(RegistrationService, public=True)
    ),
):
    """Allows an invited user to accept their invitation and complete account creation."""
    user = await reg_service.join_via_invitation(data)
    await reg_service.uow.commit()
    return user


# 2. Authenticated Session Endpoints (Scoped to Logged-in Tenant)


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_authenticated_context)],
)
async def logout(
    data: RefreshRequest,
    auth_service: AuthService = Depends(get_service(AuthService)),
):
    """Logs out the user by revoking the specified refresh token."""
    await auth_service.logout(data.refresh_token)
    await auth_service.uow.commit()


@auth_router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    context: RequestContext = Depends(get_authenticated_context),
    auth_service: AuthService = Depends(get_service(AuthService)),
):
    """Logs out all active sessions for the current authenticated user."""
    await auth_service.logout_all(context.user_id)
    await auth_service.uow.commit()


# 3. User Management Endpoints (Scoped to Logged-in Tenant)


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user(
    context: RequestContext = Depends(get_authenticated_context),
    user_service: UserService = Depends(get_service(UserService)),
):
    """Retrieve the current authenticated user profile."""
    return await user_service.get_user(context.tenant_id, context.user_id)


@auth_router.put("/users/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    context: RequestContext = Depends(get_authenticated_context),
    user_service: UserService = Depends(get_service(UserService)),
):
    """Updates the password of the active authenticated user."""
    await user_service.change_password(context.user_id, data)
    await user_service.uow.commit()


@auth_router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    pagination: PaginationParams = Depends(),
    is_active: bool | None = None,
    context: RequestContext = Depends(get_authenticated_context),
    user_service: UserService = Depends(get_service(UserService)),
):
    """Lists all users belonging to the current tenant organization."""
    users, total = await user_service.list_users(
        tenant_id=context.tenant_id, pagination=pagination, is_active=is_active
    )
    return PaginatedResponse[UserResponse].create(
        items=users, total=total, pagination=pagination
    )


@auth_router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    data: UserUpdate,
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    user_service: UserService = Depends(get_service(UserService)),
):
    """Updates a user's role. Admin only."""
    user = await user_service.update_role(
        tenant_id=context.tenant_id,
        target_user_id=user_id,
        data=data,
        acting_user_id=context.user_id,
        acting_user_role=context.role,
    )
    await user_service.uow.commit()
    return user


@auth_router.post("/users/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID,
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    user_service: UserService = Depends(get_service(UserService)),
):
    """Deactivates a user's account and terminates their sessions. Admin only."""
    await user_service.deactivate(
        tenant_id=context.tenant_id,
        user_id=user_id,
        acting_user_id=context.user_id,
        acting_user_role=context.role,
    )
    await user_service.uow.commit()


@auth_router.post("/users/{user_id}/reactivate", status_code=status.HTTP_204_NO_CONTENT)
async def reactivate_user(
    user_id: UUID,
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    user_service: UserService = Depends(get_service(UserService)),
):
    """Reactivates a deactivated user's account. Admin only."""
    await user_service.reactivate(
        tenant_id=context.tenant_id,
        user_id=user_id,
        acting_user_role=context.role,
    )
    await user_service.uow.commit()


# 4. Invitation Management Endpoints (Scoped to Logged-in Tenant)


@auth_router.post("/invitations", response_model=InvitationResponse)
async def create_invitation(
    data: InvitationCreate,
    response: Response,
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    invite_service: InvitationService = Depends(get_service(InvitationService)),
):
    """Creates a new invitation. Admin only. Returns token in custom header X-Invite-Token."""
    invitation, token = await invite_service.create_invitation(
        tenant_id=context.tenant_id,
        invited_by=context.user_id,
        data=data,
        acting_user_role=context.role,
    )
    await invite_service.uow.commit()

    response.headers["X-Invite-Token"] = token
    return invitation


@auth_router.get("/invitations", response_model=PaginatedResponse[InvitationResponse])
async def list_invitations(
    pagination: PaginationParams = Depends(),
    status: InvitationStatus | None = None,
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    invite_service: InvitationService = Depends(get_service(InvitationService)),
):
    """Lists all invitations sent from this tenant. Admin only."""
    items, total = await invite_service.list_invitations(
        tenant_id=context.tenant_id, status=status, pagination=pagination
    )
    return PaginatedResponse[InvitationResponse].create(
        items=items, total=total, pagination=pagination
    )


@auth_router.post(
    "/invitations/{invitation_id}/revoke", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_invitation(
    invitation_id: UUID,
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    invite_service: InvitationService = Depends(get_service(InvitationService)),
):
    """Revokes a pending invitation. Admin only."""
    await invite_service.revoke_invitation(
        tenant_id=context.tenant_id, invitation_id=invitation_id
    )
    await invite_service.uow.commit()


@auth_router.post(
    "/invitations/{invitation_id}/resend", response_model=InvitationResponse
)
async def resend_invitation(
    invitation_id: UUID,
    response: Response,
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    invite_service: InvitationService = Depends(get_service(InvitationService)),
):
    """Extends the expiration and creates a new invite token for a pending/expired invite. Admin only."""
    invitation, token = await invite_service.resend_invitation(
        tenant_id=context.tenant_id,
        invitation_id=invitation_id,
        resending_user_id=context.user_id,
    )
    await invite_service.uow.commit()
    response.headers["X-Invite-Token"] = token
    return invitation
