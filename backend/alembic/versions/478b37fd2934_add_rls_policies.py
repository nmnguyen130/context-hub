"""Add RLS policies

Revision ID: 478b37fd2934
Revises: aed1af0d7a3c
Create Date: 2026-07-18 08:37:04.703048

"""
# ruff: noqa: F401
from typing import Sequence

from alembic import op
import sqlalchemy as sa
import pgvector

# auto-generated imports


# revision identifiers, used by Alembic.
revision: str = '478b37fd2934'
down_revision: str | None = 'aed1af0d7a3c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = ['users', 'refresh_tokens', 'invitations', 'event_outbox']
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            AS PERMISSIVE
            FOR ALL
            TO contexthub_app
            USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            );
        """)


def downgrade() -> None:
    tables = ['users', 'refresh_tokens', 'invitations', 'event_outbox']
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
