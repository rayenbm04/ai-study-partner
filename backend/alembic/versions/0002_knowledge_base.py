"""knowledge base: documents, chunks, concepts, concept graph, embeddings

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.core.config import settings

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("subject_id", sa.String(length=36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_subject_id", "documents", ["subject_id"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.String(length=36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_type", sa.String(length=10), nullable=False),
        sa.Column("parent_chunk_id", sa.String(length=36), sa.ForeignKey("chunks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(length=500), nullable=True),
        sa.Column("chapter", sa.String(length=500), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_subject_id", "chunks", ["subject_id"])

    op.create_table(
        "concepts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("subject_id", sa.String(length=36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_concept_id", sa.String(length=36), sa.ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("subject_id", "name", name="uq_concept_subject_name"),
    )
    op.create_index("ix_concepts_subject_id", "concepts", ["subject_id"])

    op.create_table(
        "concept_prerequisites",
        sa.Column("concept_id", sa.String(length=36), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("prerequisite_id", sa.String(length=36), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "concept_chunks",
        sa.Column("concept_id", sa.String(length=36), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("chunk_id", sa.String(length=36), sa.ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relevance", sa.Float(), nullable=False),
    )

    op.create_table(
        "embeddings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("chunk_id", sa.String(length=36), sa.ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        # Width must match settings.embedding_dimension at the time this
        # migration was written (768) — changing the embedding model's output
        # dimension later means a new migration, not editing this one.
        sa.Column("vector", Vector(settings.embedding_dimension), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_embeddings_chunk_id", "embeddings", ["chunk_id"])


def downgrade() -> None:
    op.drop_table("embeddings")
    op.drop_table("concept_chunks")
    op.drop_table("concept_prerequisites")
    op.drop_table("concepts")
    op.drop_table("chunks")
    op.drop_table("documents")
