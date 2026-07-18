# ContextHub Testing Guide

This document details the configuration and execution of the backend test suite, outlining the database roles, multi-tenancy testing isolation, and a catalog of all tests.

## Running Tests

All tests run inside the `api` container:

```bash
# Run all tests
docker compose exec api pytest

# Run by directories
docker compose exec api pytest tests/unit
docker compose exec api pytest tests/integration
docker compose exec api pytest tests/api
```

## Testing Database and Roles Architecture

To enforce Row-Level Security (RLS) in tests, the test environment separates the migration owner role from the application query connection:

* **Superuser / Owner (postgres)**: Alembic migrations run in a subprocess under this superuser role via the `DATABASE_OWNER_URL` environment override to create tables and RLS policies on `contexthub_test`.
* **Application / Test Client (contexthub_app)**: The pytest engine executes test queries under this non-superuser role via `DATABASE_URL` to query `contexthub_test` with active RLS enforcement.

## Session and Transaction Isolation

We use SQLAlchemy connection pooling. To prevent connection states (like `app.bypass_rls = 'true'`) from leaking across pooled connections:

1. **Transaction-Local Configuration**: `db_session` fixture uses a session-level `after_begin` event listener to set `app.bypass_rls = 'true'` at the start of every transaction for test setup.
2. **Application Guard**: `UnitOfWork` (in `app/core/uow.py`) explicitly resets `app.bypass_rls` to `'false'` at the beginning of all non-admin transactions, ensuring RLS enforcement is always active on pooled connection checkouts.

## Pytest Fixtures

* `test_engine`: Runs Alembic migrations on `contexthub_test` as database owner, then yields the engine.
* `clean_database`: Autouse fixture that truncates all tables before each test by temporarily bypassing RLS.
* `db_session`: Session helper with RLS bypassed to set up test mock data.
* `uow`: Admin-mode Unit of Work to set up test fixtures.
* `async_client`: FastAPI HTTPX AsyncClient with overridden database session pointing to `contexthub_test`.

## Test Catalog

### Unit Tests (tests/unit/)

* **test_security_context.py**
  * `test_bcrypt_password_hashing`: Verifies password hashing, matching verification, and failure cases.
  * `test_jwt_access_and_refresh_tokens`: Verifies JWT payload claims (claims, jti, type validation) for access and refresh tokens.
  * `test_jwt_decode_type_validation`: Verifies decode raises ValueError on token type mismatches.
  * `test_request_context_propagation`: Verifies RequestContext thread-local storage propagation using context managers.

### Integration Tests (tests/integration/)

* **test_rls_isolation.py**
  * `test_rls_select_isolation`: Verifies that a tenant-scoped session cannot query or fetch rows belonging to other tenants.
  * `test_rls_insert_violation`: Verifies that trying to write another tenant's data raises a DBAPIError containing RLS violation messages.

* **test_services.py**
  * `test_user_service_cannot_demote_last_admin`: Verifies that UserService rejects demoting a tenant's last admin.
  * `test_user_service_cannot_deactivate_self`: Verifies that UserService rejects self-deactivation.
  * `test_invitation_service_flow`: Verifies invitation creation, retrieval, listing, and revocation.

### API Endpoint Tests (tests/api/)

* **test_auth.py**
  * `test_register_new_tenant_and_admin`: Tests new tenant/admin registration endpoint (`POST /auth/register`).
  * `test_login_returns_jwt_tokens`: Tests authentication login endpoint (`POST /auth/login`).

* **test_tenant_users.py**
  * `test_get_current_tenant_details`: Tests tenant retrieval endpoint (`GET /tenant`).
  * `test_patch_tenant_admin_only`: Tests tenant settings update (`PATCH /tenant`) is restricted to admins.
  * `test_role_update_rejected_for_members`: Tests that member role modification is rejected.
  * `test_api_tenant_isolation_list`: Tests that listing users returns only current tenant members.
  * `test_api_tenant_isolation_update`: Tests that updating a user from another tenant returns a 404 error due to RLS isolation.
