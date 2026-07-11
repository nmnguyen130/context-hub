"""add_rls_policies_and_roles

Revision ID: 1579b90fca04
Revises: 1e48df34b6b4
Create Date: 2026-07-11 10:48:46.888076

"""
# ruff: noqa: F401
from typing import Sequence

from alembic import op
import sqlalchemy as sa
import pgvector

# auto-generated imports


# revision identifiers, used by Alembic.
revision: str = '1579b90fca04'
down_revision: str | None = '1e48df34b6b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create roles
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'migrations_owner') THEN
            CREATE ROLE migrations_owner NOLOGIN;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
            CREATE ROLE app_user LOGIN PASSWORD 'secure-db-password-placeholder';
        END IF;
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_admin') THEN
            CREATE ROLE app_admin LOGIN PASSWORD 'secure-db-password-placeholder' BYPASSRLS;
        END IF;
    END
    $$;
    """)

    tables = ["users", "refresh_tokens", "invitations", "workspaces", "documents", "document_chunks", "audit_logs"]
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """)


def downgrade() -> None:
    tables = ["users", "refresh_tokens", "invitations", "workspaces", "documents", "document_chunks", "audit_logs"]
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

