# ContextHub SOTA Backend Architecture Blueprint (2026)
### Principal Architect Review — Supersedes "v6" Plan

---

## 0. Why This Replaces the v6 Plan

The v6 plan gets the shape right (UoW, unified context, event separation) but has three gaps that matter in production:

| Gap in v6 | Consequence | Fix in this blueprint |
| :--- | :--- | :--- |
| Tenant isolation is ORM-hook-only | One raw query, one forgotten filter, one new module = silent cross-tenant leak | **Postgres Row-Level Security** as a DB-enforced second layer, independent of app code |
| Post-commit events fire via in-memory bus only | Process crash between commit and dispatch = lost event, permanently | **Transactional Outbox pattern** — the event write is part of the same DB transaction, so it's never lost |
| UoW commits implicitly / repository pattern left vague | Hard to unit test, hard to reason about transaction boundaries | Explicit `commit()` call owned by the service/router; repositories are structural, not per-entity boilerplate |

Everything below is designed to be written once, per abstraction, and never touched again as you add domains.

---

## 1. Unified Request Context

One dataclass, one `ContextVar`, bound once per request. Everything downstream (repos, UoW, RLS, workers) reads from this single source of truth.

```python
# app/core/context.py
from __future__ import annotations
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, asdict
from typing import Iterator

@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    correlation_id: str
    tenant_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    is_platform_admin: bool = False
    ip_address: str | None = None
    user_agent: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tenant_id"] = str(self.tenant_id) if self.tenant_id else None
        d["actor_id"] = str(self.actor_id) if self.actor_id else None
        return d

_ctx_var: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)

def current_context() -> RequestContext:
    ctx = _ctx_var.get()
    if ctx is None:
        raise RuntimeError("RequestContext accessed outside a bound scope")
    return ctx

def current_context_or_none() -> RequestContext | None:
    return _ctx_var.get()

@contextmanager
def bind_context(ctx: RequestContext) -> Iterator[RequestContext]:
    """Bind a context for the current scope. Safe to call from middleware,
    background workers, or tests. Auto-resets on exit, including on exception."""
    token: Token = _ctx_var.set(ctx)
    try:
        yield ctx
    finally:
        _ctx_var.reset(token)
```

**Propagation notes (this is the part teams get wrong):**

- **`asyncio.create_task` / `TaskGroup`** — contextvars propagate automatically; Python copies the context at task-creation time. No extra code needed. Do *not* manually `_ctx_var.set()` inside a spawned task — it already has the parent's snapshot.
- **`loop.run_in_executor` (thread pool)** — also propagates automatically since Python 3.9.
- **Cross-process workers (Celery / arq / RQ)** — contextvars do **not** cross process boundaries. You must serialize and rehydrate explicitly:

```python
# Enqueueing from request-handling code
from app.core.context import current_context
task_payload = {"order_id": order_id}
process_order.delay(task_payload, current_context().to_dict())

# Worker side
@celery_app.task
def process_order(payload: dict, ctx_dict: dict) -> None:
    ctx = RequestContext(
        request_id=ctx_dict["request_id"],
        correlation_id=ctx_dict["correlation_id"],
        tenant_id=uuid.UUID(ctx_dict["tenant_id"]) if ctx_dict["tenant_id"] else None,
        actor_id=uuid.UUID(ctx_dict["actor_id"]) if ctx_dict["actor_id"] else None,
        is_platform_admin=ctx_dict["is_platform_admin"],
    )
    with bind_context(ctx):
        asyncio.run(_process_order_async(payload))
```

### Middleware (replaces `RequestIdMiddleware` + `TenantAuthMiddleware`)

```python
# app/api/middleware.py
class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode() or uuid.uuid4().hex
        correlation_id = headers.get(b"x-correlation-id", b"").decode() or request_id

        # AuthContext resolution (JWT decode, spoofing checks) unchanged from your
        # current TenantAuthMiddleware — just feed the result into RequestContext.
        auth = await resolve_auth_context(scope)  # returns tenant_id / actor_id / is_admin

        ctx = RequestContext(
            request_id=request_id,
            correlation_id=correlation_id,
            tenant_id=auth.tenant_id,
            actor_id=auth.user_id,
            is_platform_admin=auth.is_platform_admin,
            ip_address=scope.get("client", (None,))[0],
            user_agent=headers.get(b"user-agent", b"").decode() or None,
        )

        with bind_context(ctx):
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    message.setdefault("headers", []).append(
                        (b"x-request-id", request_id.encode())
                    )
                await send(message)
            await self.app(scope, receive, send_wrapper)
```

---

## 2. Fail-Safe Multi-Tenancy: Defense in Depth

Keep your existing ORM hooks (`do_orm_execute` / `before_flush`) exactly as they are — they're good for developer convenience and query performance (avoids full-table scans before the WHERE clause is even needed). But **do not treat them as your security boundary.** Add Postgres Row-Level Security underneath as the layer that cannot be bypassed by a bug, a raw query, or a new dev who doesn't know the codebase conventions.

### 2.1 Database roles (one-time setup)

```sql
-- Migrations run as an owner role that is NOT used by the app.
-- Table owners bypass RLS by default — the app must never connect as this role.
CREATE ROLE migrations_owner NOLOGIN;

-- The application's normal runtime role. Owns nothing, RLS applies to it fully.
CREATE ROLE app_user LOGIN PASSWORD '...';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

-- A narrow, separately-audited role for legitimate cross-tenant operations
-- (tenant lookup during login, platform admin console, system metrics).
CREATE ROLE app_admin LOGIN PASSWORD '...' BYPASSRLS;
```

### 2.2 Policy definition (per tenant-scoped table)

```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY; -- applies even to the table owner in this session

CREATE POLICY tenant_isolation ON invoices
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

Generate this migration once via a small script that loops over every model inheriting `TenantBaseModel` — you never hand-write it per table.

### 2.3 Setting the GUC per transaction

This is the one line of glue code connecting `RequestContext` to Postgres. It lives in the Unit of Work (Section 5), not scattered in services:

```python
await session.execute(
    text("SET LOCAL app.tenant_id = :tid"),
    {"tid": str(context.tenant_id) if context.tenant_id else ""},
)
```

`SET LOCAL` is transaction-scoped — it resets automatically at `COMMIT`/`ROLLBACK`, which matters because connections are pooled and reused across requests. There is no risk of tenant A's setting leaking into tenant B's transaction on the same pooled connection.

**Critical failure mode to guard against:** `SET LOCAL` issued *outside* an active transaction block is not an error in Postgres — it is silently a no-op. If the UoW ever executes this statement before a transaction has actually started, the GUC is never set, and RLS policies fall back to reading an empty/default `current_setting()`. Depending on how the policy is written, that either blocks everything (safe but broken) or, worse, evaluates permissively. Section 5's `UnitOfWork.__aenter__` addresses this by calling `session.begin()` explicitly — never relying on SQLAlchemy's implicit autobegin — and asserting `session.in_transaction()` immediately after, so this fails loudly at startup of the request rather than silently at the RLS layer.

This also means `SET LOCAL` is compatible with PgBouncer in **transaction pooling mode** (the setting is scoped to exactly one transaction, same as the pooling boundary) — this is in fact the reason to prefer `SET LOCAL` over a plain `SET`, which would leak across pooled connections under transaction-mode pooling.

### 2.4 The escape hatch, made explicit instead of implicit

Your current codebase uses `.execution_options(skip_tenant_filter=True)` as a flag any developer can pass anywhere — that's exactly the kind of thing that causes leaks under RLS-less architectures. Replace it with a distinct, reviewable code path.

A full parallel class hierarchy is more ceremony than this needs. Instead, it's a single factory method on `UnitOfWork` itself (Section 5) that (a) still routes through the separate `app_admin` **DB role** — the actual, non-spoofable isolation boundary — and (b) makes an audit trail structurally mandatory rather than a convention someone can forget:

```python
@classmethod
def as_admin(cls, context: RequestContext, event_bus: EventBus, *, reason: str) -> "UnitOfWork":
    """The only sanctioned cross-tenant path. Routes through the BYPASSRLS
    `app_admin` role — not an app-layer flag, which a bug could flip
    incorrectly and silently defeat the entire RLS defense. Cannot be
    constructed without a reason string; the audit event is automatic,
    not something a caller can forget to add."""
    if not context.is_platform_admin:
        raise PermissionError("as_admin() requires a platform-admin RequestContext")
    if not reason.strip():
        raise ValueError("a reason is required for any cross-tenant access")
    return cls(admin_session_factory, context, event_bus, admin_reason=reason)
```

```python
# Usage — greppable, code-reviewable, and self-documenting at the call site:
async with UnitOfWork.as_admin(context, event_bus, reason="tenant lookup during login") as uow:
    tenant = await uow.repo(TenantRepository).get_by_slug(slug)
```

Why keep the separate DB role instead of a simpler `skip_rls=True` app-layer flag: a flag is just another line of application code that can be set incorrectly by a future bug, same failure mode as `skip_tenant_filter` today. A distinct Postgres role with `BYPASSRLS` means the actual security boundary lives outside the reach of an application-layer mistake — the whole point of adding RLS in the first place.

**Net effect:** even if a service forgets to filter, calls raw SQL, or a new junior engineer writes `select(Invoice)` with no `.where()`, the database itself returns zero rows for other tenants. This is the single highest-leverage change in this blueprint.

---

## 3. Database Lifecycle & Session Management

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,      # avoids stale-connection errors after DB failover
    pool_recycle=1800,       # recycle before typical cloud LB idle-timeout kills it
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False,
)
```

Key decision: **`get_db` as a bare FastAPI dependency is retired.** In the current architecture, session creation and transaction-commit ownership are split across `deps.py` and services, which is what makes the "does this endpoint auto-commit or not" question hard to answer at a glance. The Unit of Work now owns the entire session lifecycle — created on entry, closed on exit, committed only when a service explicitly calls `uow.commit()`. One place to look, always.

---

## 4. Generic Repository (No Per-Entity Boilerplate)

```python
# app/core/repository.py
from typing import Generic, TypeVar, Any
from sqlalchemy import select, Select
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
        return entity  # no implicit flush — see UnitOfWork.flush() below.
                        # A repository shouldn't decide transaction-internal
                        # timing; that call belongs to whoever owns the UoW.

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)

    def query(self) -> Select[tuple[ModelT]]:
        return select(self.model)


def make_repository(model_cls: type[ModelT]) -> type[Repository[ModelT]]:
    """For entities that need nothing beyond CRUD — no hand-written class needed."""
    return type(f"{model_cls.__name__}Repository", (Repository,), {"model": model_cls})
```

For entities that need custom queries, subclass explicitly — this is the *only* place domain-specific query logic should live:

```python
# app/modules/tenant/repository.py
class TenantRepository(Repository[Tenant]):
    model = Tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        return await self.session.scalar(self.query().where(Tenant.slug == slug))
```

```python
# For a CRUD-only entity elsewhere in the codebase — zero boilerplate:
InvoiceRepository = make_repository(Invoice)
```

---

## 5. Unit of Work

```python
# app/core/uow.py
from __future__ import annotations
from typing import TypeVar, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.context import RequestContext
from app.core.events import EventBus, DomainEvent, OutboxEvent

R = TypeVar("R", bound="Repository")

class UnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        context: RequestContext,
        event_bus: EventBus,
        *,
        admin_reason: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._context = context
        self._event_bus = event_bus
        self._repos: dict[type, Any] = {}
        self._events: list[DomainEvent] = []
        self._admin_reason = admin_reason
        self.session: AsyncSession

    @classmethod
    def as_admin(cls, context: RequestContext, event_bus: EventBus, *, reason: str) -> "UnitOfWork":
        """See Section 2.4 — the sole sanctioned cross-tenant path."""
        if not context.is_platform_admin:
            raise PermissionError("as_admin() requires a platform-admin RequestContext")
        if not reason.strip():
            raise ValueError("a reason is required for any cross-tenant access")
        return cls(admin_session_factory, context, event_bus, admin_reason=reason)

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        # Explicit begin — never rely on SQLAlchemy's implicit autobegin here.
        # SET LOCAL issued outside an active transaction is a silent no-op in
        # Postgres (see Section 2.3), which would otherwise fail the tenant
        # isolation boundary open instead of raising anything.
        await self.session.begin()

        if self._admin_reason:
            # BYPASSRLS role — no tenant GUC needed. The audit event below is
            # mandatory, not optional: this is what makes cross-tenant access
            # reviewable rather than silent.
            self.record_event(DomainEvent("admin.cross_tenant_access", {
                "actor_id": str(self._context.actor_id),
                "reason": self._admin_reason,
            }))
        else:
            await self.session.execute(
                text("SET LOCAL app.tenant_id = :tid"),
                {"tid": str(self._context.tenant_id) if self._context.tenant_id else ""},
            )

        assert self.session.in_transaction(), "UoW session must be inside a transaction"
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None and self.session.in_transaction():
            await self.session.rollback()
        await self.session.close()

    def repo(self, repo_cls: type[R]) -> R:
        if repo_cls not in self._repos:
            self._repos[repo_cls] = repo_cls(self.session)
        return self._repos[repo_cls]

    async def flush(self) -> None:
        """Explicit, on-demand — e.g. to populate a generated PK/default before
        using it later in the same request. Repository.add() no longer does
        this implicitly (Section 4); the UoW/service decides the timing."""
        await self.session.flush()

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    async def commit(self) -> None:
        try:
            # 1. Transactional handlers — MUST succeed for the transaction to
            #    commit. e.g. audit_logs write. If this raises, everything
            #    below rolls back together with it.
            for event in self._events:
                await self._event_bus.dispatch_transactional(event, self.session)

            # 2. Outbox rows — written in the SAME transaction, so the event
            #    write is exactly as durable as the business data write.
            #    id is a client-side uuid4 default, so it's already available
            #    below without needing a flush.
            outbox_rows = [OutboxEvent.from_domain_event(e, self._context) for e in self._events]
            for row in outbox_rows:
                self.session.add(row)

            await self.session.commit()
        except Exception:
            if self.session.in_transaction():
                await self.session.rollback()
            raise

        # 3. Best-effort immediate dispatch for low-latency consumers. This is
        #    purely a latency optimization — claim_and_dispatch (Section 6.2)
        #    guarantees at most one handler execution per row even if the
        #    relay (Section 6.3) also picks it up around the same time.
        #    The relay remains the actual durability guarantee, not this.
        for row in outbox_rows:
            self._event_bus.dispatch_post_commit_nowait(self._session_factory, row.id)

        self._events.clear()
```

---

## 6. Event-Driven Architecture: Transactional vs. Post-Commit

### 6.1 Domain event & outbox row

```python
# app/core/events.py
import uuid, datetime, enum
from dataclasses import dataclass, field
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: str
    payload: dict
    occurred_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

class OutboxStatus(str, enum.Enum):
    PENDING = "pending"        # waiting to be dispatched (or waiting for retry)
    PROCESSING = "processing"  # claimed by a dispatcher, handler currently running
    DISPATCHED = "dispatched"  # terminal success
    DEAD_LETTER = "dead_letter"  # terminal failure — exhausted retries, needs a human

class OutboxEvent(Base):
    __tablename__ = "event_outbox"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    correlation_id: Mapped[str]
    status: Mapped[str] = mapped_column(String(20), default=OutboxStatus.PENDING, index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    next_retry_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(nullable=True)
    dispatched_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    @classmethod
    def from_domain_event(cls, event: DomainEvent, ctx) -> "OutboxEvent":
        return cls(
            event_type=event.event_type,
            payload=event.payload,
            tenant_id=ctx.tenant_id,
            correlation_id=ctx.correlation_id,
        )
```

### 6.2 The bus itself, and the claim pattern that prevents double-dispatch

The risk with having two independent triggers (immediate optimistic dispatch + the relay poller) is that both could pick up the same row and run handlers twice. The fix is to never let either trigger invoke handlers directly — both instead call one shared `claim_and_dispatch()` function whose claim step is a single atomic `UPDATE ... WHERE status = 'pending'`. Whichever caller's `UPDATE` actually matches a row wins it; the other gets zero rows back and does nothing. This isn't a lock or a distributed coordination mechanism — it's just relying on Postgres row-level atomicity, which is already there for free.

```python
# app/core/event_bus.py
import asyncio, datetime, random
from collections import defaultdict
from typing import Awaitable, Callable
from sqlalchemy import update

TransactionalHandler = Callable[[DomainEvent, "AsyncSession"], Awaitable[None]]
PostCommitHandler = Callable[[DomainEvent], Awaitable[None]]

MAX_ATTEMPTS = 8
BASE_BACKOFF_SECONDS = 2

def _next_backoff(attempts: int) -> datetime.timedelta:
    exp = min(BASE_BACKOFF_SECONDS * (2 ** attempts), 900)  # cap at 15 minutes
    jitter = random.uniform(0, exp * 0.2)  # avoid thundering-herd retries
    return datetime.timedelta(seconds=exp + jitter)


async def claim_and_dispatch(session_factory, outbox_id, event_bus: "EventBus") -> None:
    """The ONLY place post-commit handlers are ever invoked from. Called by
    both the immediate optimistic path and the relay poller — safe to call
    from either or both, since the UPDATE below guarantees at most one of them
    actually proceeds to run handlers for a given row."""
    async with session_factory() as session:
        result = await session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == outbox_id, OutboxEvent.status == OutboxStatus.PENDING)
            .values(status=OutboxStatus.PROCESSING)
            .returning(OutboxEvent)
        )
        row = result.scalar_one_or_none()
        await session.commit()
        if row is None:
            return  # already claimed/dispatched by someone else — expected, not an error

        event = DomainEvent(event_type=row.event_type, payload=row.payload)
        try:
            for handler in event_bus._post_commit[event.event_type]:
                await handler(event)  # handlers MUST be idempotent regardless of this pattern —
                                       # a crash after a handler runs but before the status update
                                       # below still means at-least-once, not exactly-once, delivery
        except Exception as exc:
            row.attempts += 1
            if row.attempts >= MAX_ATTEMPTS:
                row.status = OutboxStatus.DEAD_LETTER
                row.last_error = str(exc)
                # alert/metric here — dead letters need a human or a replay tool, not a retry loop
            else:
                row.status = OutboxStatus.PENDING
                row.next_retry_at = datetime.datetime.now(datetime.timezone.utc) + _next_backoff(row.attempts)
                row.last_error = str(exc)
            await session.merge(row)
            await session.commit()
            return

        row.status = OutboxStatus.DISPATCHED
        row.dispatched_at = datetime.datetime.now(datetime.timezone.utc)
        await session.merge(row)
        await session.commit()


class EventBus:
    def __init__(self) -> None:
        self._transactional: dict[str, list[TransactionalHandler]] = defaultdict(list)
        self._post_commit: dict[str, list[PostCommitHandler]] = defaultdict(list)

    def on_transactional(self, event_type: str, handler: TransactionalHandler) -> None:
        self._transactional[event_type].append(handler)

    def on_post_commit(self, event_type: str, handler: PostCommitHandler) -> None:
        self._post_commit[event_type].append(handler)

    async def dispatch_transactional(self, event: DomainEvent, session) -> None:
        for handler in self._transactional[event.event_type]:
            await handler(event, session)  # same tx — failure rolls everything back

    def dispatch_post_commit_nowait(self, session_factory, outbox_id) -> None:
        """Latency optimization only. Fires an early claim attempt so common-case
        consumers see the event in milliseconds instead of waiting for the next
        relay poll — but this is not the durability guarantee, the relay is."""
        asyncio.create_task(claim_and_dispatch(session_factory, outbox_id, self))

# Registration, once at startup:
event_bus = EventBus()
event_bus.on_transactional("user.logged_in", write_audit_log)
event_bus.on_post_commit("user.logged_in", send_login_notification)
event_bus.on_post_commit("user.logged_in", record_metric)
```

### 6.3 Outbox relay (the durability guarantee)

A lightweight poller — run as a separate asyncio task or a small standalone process — is what actually guarantees delivery even across a process crash. It now defers entirely to `claim_and_dispatch()` for the actual work, so there is exactly one code path that ever runs a handler:

```python
# app/workers/outbox_relay.py
from sqlalchemy import select
from app.core.event_bus import claim_and_dispatch

async def relay_loop(session_factory, event_bus: EventBus, poll_interval: float = 0.5):
    while True:
        async with session_factory() as session:
            now = datetime.datetime.now(datetime.timezone.utc)
            outbox_ids = (await session.execute(
                select(OutboxEvent.id)
                .where(
                    OutboxEvent.status == OutboxStatus.PENDING,
                    (OutboxEvent.next_retry_at.is_(None)) | (OutboxEvent.next_retry_at <= now),
                )
                .order_by(OutboxEvent.id)
                .limit(100)
            )).scalars().all()

        for outbox_id in outbox_ids:
            await claim_and_dispatch(session_factory, outbox_id, event_bus)

        await asyncio.sleep(poll_interval)
```

Note this SELECT no longer needs `FOR UPDATE SKIP LOCKED` for correctness — the atomic `UPDATE ... WHERE status = 'pending'` inside `claim_and_dispatch` is what actually prevents double-processing, so multiple relay instances (or the relay racing the immediate-dispatch path) are already safe without row locks here. `SKIP LOCKED` is still worth adding back in if you run several relay processes and want to avoid them repeatedly attempting to claim rows another instance is mid-processing, but it's a throughput optimization, not a correctness requirement.

**Dead-letter handling:** rows that exhaust `MAX_ATTEMPTS` land in `status = 'dead_letter'` and stop being retried automatically — this is intentional, since an event that has failed 8 times with exponential backoff is far more likely to indicate a bug in the handler or a permanently invalid payload than a transient blip. Add a scheduled check (a cron query, a metric, or an alert) on `SELECT count(*) FROM event_outbox WHERE status = 'dead_letter'`, and a small admin/CLI action that resets a row back to `status = 'pending', attempts = 0` once the underlying issue is fixed, so dead-lettered events can be replayed deliberately rather than automatically.

---

## 7. FastAPI Wiring

```python
# app/api/deps.py
from app.core.context import current_context, RequestContext

def get_context() -> RequestContext:
    return current_context()

async def get_uow(
    context: RequestContext = Depends(get_context),
) -> AsyncIterator[UnitOfWork]:
    async with UnitOfWork(async_session_factory, context, event_bus) as uow:
        yield uow
```

```python
# app/modules/tenant/router.py
tenant_router = APIRouter(prefix="/tenant", tags=["Tenant"])

@tenant_router.get("", response_model=TenantResponse)
async def get_current_tenant(
    context: RequestContext = Depends(get_context),
    uow: UnitOfWork = Depends(get_uow),
):
    tenant = await uow.repo(TenantRepository).get(context.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return tenant

@tenant_router.patch("", response_model=TenantResponse)
async def update_tenant(
    data: TenantUpdate,
    context: RequestContext = Depends(get_context),
    uow: UnitOfWork = Depends(get_uow),
):
    tenant = await uow.repo(TenantRepository).get(context.tenant_id)
    tenant.name = data.name  # apply patch
    uow.record_event(DomainEvent("tenant.updated", {"tenant_id": str(tenant.id)}))
    await uow.commit()   # explicit — the only place a transaction boundary closes
    return tenant
```

Commit is always explicit, always in the router or a thin service function it calls directly — never buried inside a dependency's `finally` block. This is what makes multi-step flows (e.g., "update tenant, then provision resources, then commit once") straightforward to write correctly.

---

## 8. Testing Strategy This Unlocks

- **Repository/UoW abstraction** → integration tests run against a real Postgres test DB with each test wrapped in an outer transaction that's rolled back at teardown (standard `pytest-asyncio` + savepoint pattern) — RLS policies get exercised for real, which is the whole point.
- **Pure unit tests** → since services depend on `UnitOfWork` and `Repository[T]` as their only DB touchpoint, an in-memory fake implementing the same two methods (`get`/`add`/`query`) lets you unit test business logic with zero DB at all.
- **Event handlers** → transactional handlers can be tested by asserting DB state after `uow.commit()`; post-commit handlers are tested in isolation since they're plain `async def handler(event)` functions with no framework coupling.

---

## 9. Migration Path (Incremental, No Big-Bang Rewrite)

1. **Add RLS policies + roles** (Section 2). Zero application code changes — purely additive. Ship this first; it's your biggest risk reduction for the least effort.
2. **Introduce `RequestContext`** (Section 1), replacing the two separate ContextVars. Update the one middleware file.
3. **Introduce `UnitOfWork` + `Repository`** module by module, starting with a low-traffic domain, leaving `get_db`-style services untouched elsewhere until migrated.
4. **Introduce the outbox table + relay** (Section 6.3) once at least one domain emits events; existing synchronous side effects can stay as-is until you have a concrete reason to decouple them.

Each step ships independently and is individually revertible — nothing here requires a freeze.
