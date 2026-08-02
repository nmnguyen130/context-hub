import base64
import json
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Select, asc, desc


class CursorParams(BaseModel):
    """Query parameters for requesting a cursor-paginated page."""

    cursor: str | None = Field(
        default=None, description="Opaque cursor token for next page"
    )
    limit: int = Field(
        default=20, ge=1, le=100, description="Max number of items to return"
    )


class CursorPage[T](BaseModel):
    """Standardized response envelope for cursor-paginated endpoints."""

    items: list[T]
    next_cursor: str | None = Field(
        default=None, description="Cursor token for fetching the next page"
    )
    has_more: bool = Field(
        default=False, description="Flag indicating if more records exist"
    )


def encode_cursor(sort_val: object, item_id: object) -> str:
    """Encode sort value and ID to base64 cursor string."""
    payload = [str(sort_val), str(item_id)]
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[object, uuid.UUID] | None:
    """Decode base64 cursor string back to (sort_val, item_id)."""
    try:
        raw = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if not isinstance(raw, list) or len(raw) != 2:
            return None
        val, item_id = raw[0], uuid.UUID(raw[1])
        try:
            val = datetime.fromisoformat(val)
        except (ValueError, TypeError):
            pass
        return val, item_id
    except Exception:
        return None


async def paginate_cursor[T](
    session,
    stmt: Select,
    params: CursorParams | None = None,
    *,
    sort_column,
    id_column,
    ascending: bool = False,
) -> tuple[list[T], str | None, bool]:
    """Execute O(1) keyset seek pagination query."""
    params = params or CursorParams()
    query = stmt

    # 1. Apply seek filter if cursor provided
    if params.cursor and (seek := decode_cursor(params.cursor)):
        sort_val, last_id = seek
        seek_op = (sort_column > sort_val) if ascending else (sort_column < sort_val)
        query = query.where(
            seek_op | ((sort_column == sort_val) & (id_column < last_id))
        )

    # 2. Sort and fetch limit + 1 to check for next page
    order_fn = asc if ascending else desc
    query = query.order_by(order_fn(sort_column), order_fn(id_column)).limit(
        params.limit + 1
    )
    items = list((await session.scalars(query)).all())

    # 3. Check if more items exist and trim extra item
    has_more = len(items) > params.limit
    if has_more:
        items = items[: params.limit]

    # 4. Generate next cursor token from last item
    next_cursor = (
        encode_cursor(
            getattr(items[-1], sort_column.key),
            getattr(items[-1], id_column.key),
        )
        if has_more and items
        else None
    )

    return items, next_cursor, has_more
