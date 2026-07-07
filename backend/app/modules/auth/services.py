from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.exceptions import ServiceError
from app.core.security import decode_invite_token, hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import UserJoin, UserLogin, UserRegister
from app.modules.tenant.models import Tenant


async def get_user_by_email_global(db: AsyncSession, email: str) -> User | None:
    """Fetches a user globally across all tenants by email.

    Args:
        db (AsyncSession): Database session.
        email (str): The target user email.

    Returns:
        User | None: The user object if found, otherwise None.
    """
    stmt = (
        select(User)
        .where(User.email == email)
        .execution_options(skip_tenant_filter=True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, data: UserRegister) -> User:
    """Registers a new Tenant and creates its first Administrator user.

    Args:
        db (AsyncSession): Database session.
        data (UserRegister): Registration input data.

    Returns:
        User: The newly created administrator user.

    Raises:
        ServiceError: If the email is already registered.
    """
    # 1. Verify global email uniqueness
    existing_user = await get_user_by_email_global(db, data.email)
    if existing_user:
        raise ServiceError("Email already registered", status_code=409)

    # 2. Create the new Tenant
    tenant = Tenant(name=data.tenant_name, plan_tier="Starter", metadata_json={})
    db.add(tenant)
    await db.flush()  # Flush to populate tenant.id

    # 3. Create the Admin User
    hashed_pwd = hash_password(data.password)
    user = User(
        email=data.email,
        password_hash=hashed_pwd,
        first_name=data.first_name,
        last_name=data.last_name,
        role=UserRole.ADMIN,
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def join_user(db: AsyncSession, data: UserJoin) -> User:
    """Registers a new employee user using a signed invitation token.

    Args:
        db (AsyncSession): Database session.
        data (UserJoin): Employee registration join details.

    Returns:
        User: The newly registered employee user.

    Raises:
        ServiceError: If invitation validation, matching, or email checks fail.
    """
    # 1. Decode and validate invitation token
    payload = decode_invite_token(data.invite_token)
    if not payload:
        raise ServiceError("Invalid or expired invitation token", status_code=400)

    tenant_id_str = payload.get("invite_tenant_id")
    invite_email = payload.get("invite_email")
    invite_role = UserRole(payload.get("invite_role", UserRole.MEMBER))

    # 2. Verify email matches invitation
    if data.email != invite_email:
        raise ServiceError("Email does not match invitation recipient", status_code=400)

    # 3. Verify global email uniqueness
    existing_user = await get_user_by_email_global(db, data.email)
    if existing_user:
        raise ServiceError("Email already registered", status_code=409)

    # 4. Verify tenant exists
    tenant_id = UUID(tenant_id_str)
    tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant_result = await db.execute(tenant_stmt)
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise ServiceError("Tenant organization not found", status_code=404)

    # 5. Create the employee User
    hashed_pwd = hash_password(data.password)
    user = User(
        email=data.email,
        password_hash=hashed_pwd,
        first_name=data.first_name,
        last_name=data.last_name,
        role=invite_role,
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, data: UserLogin) -> User:
    """Authenticates a user globally by email and credentials.

    Args:
        db (AsyncSession): Database session.
        data (UserLogin): User login credentials.

    Returns:
        User: The authenticated user object.

    Raises:
        ServiceError: If credentials are incorrect or the user is inactive.
    """
    user = await get_user_by_email_global(db, data.email)
    if not user or not verify_password(data.password, user.password_hash):
        raise ServiceError("Incorrect email or password", status_code=401)

    if not user.is_active:
        raise ServiceError("Inactive user", status_code=400)

    return user
