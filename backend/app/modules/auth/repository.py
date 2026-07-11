# app/modules/auth/repository.py
import uuid
from app.core.repository import Repository
from app.modules.auth.models import Invitation, RefreshToken, User

class UserRepository(Repository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(self.query().where(User.email == email))

class RefreshTokenRepository(Repository[RefreshToken]):
    model = RefreshToken

    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        return await self.session.scalar(
            self.query().where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None)
            )
        )

class InvitationRepository(Repository[Invitation]):
    model = Invitation

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        return await self.session.scalar(self.query().where(Invitation.token_hash == token_hash))
