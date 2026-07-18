# ContextHub Testing Guide

A clean and minimal reference for the backend test suite.

---

## 🚀 How to Run Tests

Run commands inside the `api` container:

```bash
# Run all tests
docker compose exec api env PYTHONPATH=/app/.venv/lib/python3.13/site-packages:/app pytest

# Run by markers
docker compose exec api env PYTHONPATH=/app/.venv/lib/python3.13/site-packages:/app pytest -m unit
docker compose exec api env PYTHONPATH=/app/.venv/lib/python3.13/site-packages:/app pytest -m integration
```

---

## 🛠️ Testing Environment

We use **Pytest + Pytest-Asyncio + HTTPX** without external database mocking engines.

### Fixtures (`tests/conftest.py`)

| Fixture | Scope | Description |
| :--- | :--- | :--- |
| `test_engine` | `session` | Creates the Postgres schema once at test session startup and drops it on exit. |
| `clean_database` | `function` | Autouse. Truncates all tables in reverse dependency order before each test. |
| `db_session` | `function` | Setup database session. Automatically commits so the API client can read mock data. |
| `uow` | `function` | Admin-mode Unit of Work to set up tests bypassing RLS policies. |
| `async_client` | `function` | FastAPI HTTPX AsyncClient with database session dependencies overridden to point to the test DB. |

### Configuration (`pyproject.toml`)

To prevent event loop mismatch errors when reusing connection pools, both tests and fixtures are locked to a single session-scoped loop:
```toml
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```

---

## 📋 Test Matrix

### 1. Unit Tests (`tests/unit/`)
*Pure logic checks with zero external network or database connections.*

- **Context** (`test_context.py`): Thread-local request context isolation and dictionary serialization roundtrips.
- **Config** (`test_config.py`): Pydantic settings validations (CORS wildcard rejection, JWT secret minimum length).
- **Domain Events** (`test_events.py`): Event recording, pulling, and queue clearing on aggregate roots.
- **Security** (`test_security.py`): Bcrypt hashing checks, 72-byte password truncation limits, JWT token generation & verification.
- **Slugs** (`test_slug.py`): Slug generation formatting and normalization rules.

### 2. Integration Tests (`tests/integration/`)
*Verifies database operations, RLS constraints, and transactional unit of work.*

- **UoW** (`test_uow.py`): Unit of work commit persistence and rollback safety.
- **Tenant** (`test_tenant_service.py`): Tenant registration, profile updates, slug constraints, and soft-delete states.
- **Auth** (`test_auth_service.py`): Login logic (password validation, deactivated accounts) and JWT refresh session rotation.
- **Registration** (`test_registration.py`): Tenant self-registration and joining organizations via invitation tokens.
- **Users** (`test_user_service.py`): Role management constraints and deactivation lockout protections.
- **Invitations** (`test_invitation_service.py`): Invitation workflows (creation, list, and revocation).

### 3. API Endpoint Tests (`tests/api/`)
*Simulates client-side HTTP calls against FastAPI routers with overridden DB dependencies.*

- **Health** (`test_health.py`): `GET /health` probe checks.
- **Auth** (`test_auth_endpoints.py`): Registration and login endpoints (JWT token response payload validations).
- **Tenant** (`test_tenant_endpoints.py`): Current tenant retrieval, patching metadata, and public slug lookups.
- **Users** (`test_user_endpoints.py`): Listing tenant users, role updates, and RBAC restrictions.
