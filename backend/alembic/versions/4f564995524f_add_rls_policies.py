"""add_rls_policies

Revision ID: 4f564995524f
Revises: 2307f98c5eff
Create Date: 2026-07-22 21:04:00.000000

"""
from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f564995524f"
down_revision: str | None = "2307f98c5eff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable RLS policies
    rls_tables = [
        "event_outbox",
        "users",
        "workspaces",
        "documents",
        "invitations",
        "refresh_tokens",
        "document_chunks",
        "chat_sessions",
        "chat_messages",
    ]
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
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
            """
        )


def downgrade() -> None:
    # Drop RLS policies
    rls_tables = [
        "chat_messages",
        "chat_sessions",
        "document_chunks",
        "refresh_tokens",
        "invitations",
        "documents",
        "workspaces",
        "users",
        "event_outbox",
    ]
    for table in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
