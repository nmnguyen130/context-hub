# app/core/repository.py
from typing import Generic, TypeVar, Any, Sequence
from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)

class Repository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: Any) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity

    async def add_all(self, entities: Sequence[ModelT]) -> Sequence[ModelT]:
        self.session.add_all(entities)
        return entities

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)

    def query(self) -> Select[tuple[ModelT]]:
        return select(self.model)

    async def exists(self, id_: Any) -> bool:
        stmt = select(1).where(self.model.id == id_)
        res = await self.session.execute(stmt)
        return res.scalar() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        res = await self.session.execute(stmt)
        return res.scalar_one()

def make_repository(model_cls: type[ModelT]) -> type[Repository[ModelT]]:
    """For entities that need nothing beyond CRUD — no hand-written class needed."""
    return type(f"{model_cls.__name__}Repository", (Repository,), {"model": model_cls})
