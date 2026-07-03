"""add vector and fts indices

Revision ID: b1932c8e234f
Revises: a4834b7f5b9e
Create Date: 2026-07-03 23:25:00.000000

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1932c8e234f'
down_revision: str | None = 'a4834b7f5b9e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create Vector similarity HNSW index and FTS search vector GIN index
    op.execute("""
        CREATE INDEX IF NOT EXISTS doc_chunks_embedding_hnsw_idx 
        ON document_chunks USING hnsw (embedding vector_cosine_ops);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS doc_chunks_search_vector_gin_idx 
        ON document_chunks USING gin (search_vector);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS doc_chunks_embedding_hnsw_idx;")
    op.execute("DROP INDEX IF EXISTS doc_chunks_search_vector_gin_idx;")
