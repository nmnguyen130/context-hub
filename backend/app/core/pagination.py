from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=10, ge=1, le=100, description="Max number of items to return")


class PaginatedResponse[T](BaseModel):
    """Standardized envelope response structure for paginated lists using PEP 695 generics."""

    items: list[T]
    total: int = Field(..., description="Total matching database records")
    offset: int = Field(..., description="Starting record index offset")
    limit: int = Field(..., description="Maximum record limit requested")
    has_more: bool = Field(..., description="Flag indicating if more pages exist")

    @classmethod
    def create(
        cls, items: list[T], total: int, pagination: PaginationParams
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            offset=pagination.offset,
            limit=pagination.limit,
            has_more=(pagination.offset + len(items)) < total,
        )
