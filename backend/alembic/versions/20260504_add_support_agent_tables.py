# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add support agent doc_chunks and ticket tables

Revision ID: support_agent_001
Revises: indie_sample_001
Create Date: 2026-05-04

Schema-only, additive, prod-safe:
  * New doc_chunks table — RAG document chunks with pgvector embeddings
    for support agent retrieval (768-dim nomic-embed-text).
  * New agent_support_tickets table — escalation tickets from the
    support agent, separate from the patron-facing support_tickets.
  * New agent_support_ticket_replies table — replies and activity
    on agent support tickets.
  * HNSW index on doc_chunks.embedding for cosine similarity search.
  * GIN index on doc_chunks.tags for array containment queries.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "support_agent_001"
down_revision: Union[str, None] = "indie_sample_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- doc_chunks ---
    op.create_table(
        "doc_chunks",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("doc_type", sa.Text(), nullable=True),
        sa.Column("l30_version_min", sa.Text(), nullable=True),
        sa.Column("l30_version_max", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("heading_path", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_doc_chunks_id", "doc_chunks", ["id"])
    op.create_index("ix_doc_chunks_source_chunk", "doc_chunks", ["source_path", "chunk_index"], unique=True)
    op.create_index("ix_doc_chunks_doc_type", "doc_chunks", ["doc_type"])
    op.create_index("ix_doc_chunks_version_min", "doc_chunks", ["l30_version_min"])
    op.create_index("ix_doc_chunks_tags", "doc_chunks", ["tags"], postgresql_using="gin")
    # HNSW vector index for cosine similarity search
    op.execute(
        "CREATE INDEX ix_doc_chunks_embedding_hnsw ON doc_chunks "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    # --- agent_support_tickets ---
    op.create_table(
        "agent_support_tickets",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("public_id", sa.Text(), unique=True, nullable=False),
        sa.Column("library_id", sa.Text(), nullable=False),
        sa.Column("library_name", sa.Text(), nullable=False),
        sa.Column("l30_version", sa.Text(), nullable=True),
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("attempted_steps", sa.Text(), nullable=True),
        sa.Column("referenced_docs", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("config_excerpts", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("conversation_transcript", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("reporter_name", sa.Text(), nullable=True),
        sa.Column("reporter_email", sa.Text(), nullable=True),
        sa.Column("reporter_role", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'open'")),
        sa.Column("assigned_to", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_support_tickets_id", "agent_support_tickets", ["id"])
    op.create_index("ix_agent_support_tickets_library", "agent_support_tickets", ["library_id"])
    op.create_index("ix_agent_support_tickets_status", "agent_support_tickets", ["status"])
    op.create_index("ix_agent_support_tickets_destination", "agent_support_tickets", ["destination"])
    op.create_index("ix_agent_support_tickets_created", "agent_support_tickets", ["created_at"])

    # --- agent_support_ticket_replies ---
    op.create_table(
        "agent_support_ticket_replies",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("author_name", sa.Text(), nullable=False),
        sa.Column("author_role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_agent_support_ticket_replies_id", "agent_support_ticket_replies", ["id"])
    op.create_index("ix_agent_support_ticket_replies_ticket_id", "agent_support_ticket_replies", ["ticket_id"])
    op.create_index("ix_agent_support_replies_ticket", "agent_support_ticket_replies", ["ticket_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_support_replies_ticket", table_name="agent_support_ticket_replies")
    op.drop_index("ix_agent_support_ticket_replies_ticket_id", table_name="agent_support_ticket_replies")
    op.drop_index("ix_agent_support_ticket_replies_id", table_name="agent_support_ticket_replies")
    op.drop_table("agent_support_ticket_replies")

    op.drop_index("ix_agent_support_tickets_created", table_name="agent_support_tickets")
    op.drop_index("ix_agent_support_tickets_destination", table_name="agent_support_tickets")
    op.drop_index("ix_agent_support_tickets_status", table_name="agent_support_tickets")
    op.drop_index("ix_agent_support_tickets_library", table_name="agent_support_tickets")
    op.drop_index("ix_agent_support_tickets_id", table_name="agent_support_tickets")
    op.drop_table("agent_support_tickets")

    op.execute("DROP INDEX IF EXISTS ix_doc_chunks_embedding_hnsw")
    op.drop_index("ix_doc_chunks_tags", table_name="doc_chunks")
    op.drop_index("ix_doc_chunks_version_min", table_name="doc_chunks")
    op.drop_index("ix_doc_chunks_doc_type", table_name="doc_chunks")
    op.drop_index("ix_doc_chunks_source_chunk", table_name="doc_chunks")
    op.drop_index("ix_doc_chunks_id", table_name="doc_chunks")
    op.drop_table("doc_chunks")
