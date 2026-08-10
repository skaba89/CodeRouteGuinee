"""Migration 0015 — architecture média premium normalisée.

Crée media_assets et question_media sans modifier ni supprimer les colonnes
legacy questions.media_type/media_url/media_alt. La migration de contenu
legacy sera volontairement réalisée dans une phase ultérieure.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def _table_exists(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def _index_names(bind, table: str) -> set[str]:
    if not _table_exists(bind, table):
        return set()
    try:
        return {str(item.get("name")) for item in sa.inspect(bind).get_indexes(table) if item.get("name")}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "media_assets"):
        op.create_table(
            "media_assets",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("uuid", sa.String(36), nullable=False),
            sa.Column("media_type", sa.String(20), nullable=False),
            sa.Column("usage_type", sa.String(20), nullable=False),
            sa.Column("storage_provider", sa.String(40), nullable=True),
            sa.Column("storage_key", sa.Text(), nullable=True),
            sa.Column("public_url", sa.Text(), nullable=True),
            sa.Column("secure_url", sa.Text(), nullable=True),
            sa.Column("mime_type", sa.String(100), nullable=True),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("duration_seconds", sa.Float(), nullable=True),
            sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
            sa.Column("checksum_sha256", sa.String(64), nullable=True),
            sa.Column("poster_media_id", sa.String(36), nullable=True),
            sa.Column("fallback_media_id", sa.String(36), nullable=True),
            sa.Column("theme", sa.String(80), nullable=True),
            sa.Column("subtheme", sa.String(120), nullable=True),
            sa.Column("country_code", sa.String(2), nullable=False, server_default=sa.text("'GN'")),
            sa.Column("regulatory_scope", sa.String(120), nullable=True),
            sa.Column("source_type", sa.String(24), nullable=False, server_default=sa.text("'internal'")),
            sa.Column("source_reference", sa.Text(), nullable=True),
            sa.Column("license_type", sa.String(80), nullable=True),
            sa.Column("license_reference", sa.Text(), nullable=True),
            sa.Column("license_expiration_date", sa.Date(), nullable=True),
            sa.Column("copyright_owner", sa.String(255), nullable=True),
            sa.Column("quality_status", sa.String(24), nullable=False, server_default=sa.text("'draft'")),
            sa.Column("regulatory_status", sa.String(24), nullable=False, server_default=sa.text("'not_reviewed'")),
            sa.Column("regulatory_authority_reference", sa.Text(), nullable=True),
            sa.Column("validated_by", sa.String(36), nullable=True),
            sa.Column("validated_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("archived_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint("media_type IN ('image','video','audio')", name="ck_media_assets_media_type"),
            sa.CheckConstraint(
                "usage_type IN ('exam','course','explanation','thumbnail')",
                name="ck_media_assets_usage_type",
            ),
            sa.CheckConstraint(
                "source_type IN ('original','licensed','partner','public_domain','internal','generated','legacy')",
                name="ck_media_assets_source_type",
            ),
            sa.CheckConstraint(
                "quality_status IN ('draft','review_required','validated','rejected')",
                name="ck_media_assets_quality_status",
            ),
            sa.CheckConstraint(
                "regulatory_status IN ('not_reviewed','under_review','validated','rejected')",
                name="ck_media_assets_regulatory_status",
            ),
            sa.CheckConstraint("width IS NULL OR width > 0", name="ck_media_assets_width_positive"),
            sa.CheckConstraint("height IS NULL OR height > 0", name="ck_media_assets_height_positive"),
            sa.CheckConstraint(
                "duration_seconds IS NULL OR duration_seconds >= 0",
                name="ck_media_assets_duration_nonnegative",
            ),
            sa.CheckConstraint(
                "file_size_bytes IS NULL OR file_size_bytes >= 0",
                name="ck_media_assets_size_nonnegative",
            ),
            sa.ForeignKeyConstraint(["poster_media_id"], ["media_assets.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["fallback_media_id"], ["media_assets.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["validated_by"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid", name="uq_media_assets_uuid"),
        )

    existing_media_indexes = _index_names(bind, "media_assets")
    for name, columns in (
        ("ix_media_assets_uuid", ["uuid"]),
        ("ix_media_assets_media_type", ["media_type"]),
        ("ix_media_assets_usage_type", ["usage_type"]),
        ("ix_media_assets_storage_provider", ["storage_provider"]),
        ("ix_media_assets_checksum_sha256", ["checksum_sha256"]),
        ("ix_media_assets_theme", ["theme"]),
        ("ix_media_assets_country_code", ["country_code"]),
        ("ix_media_assets_source_type", ["source_type"]),
        ("ix_media_assets_quality_status", ["quality_status"]),
        ("ix_media_assets_regulatory_status", ["regulatory_status"]),
        ("ix_media_assets_archived_at", ["archived_at"]),
    ):
        if name not in existing_media_indexes:
            op.create_index(name, "media_assets", columns, unique=False)

    if not _table_exists(bind, "question_media"):
        op.create_table(
            "question_media",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("question_id", sa.String(36), nullable=False),
            sa.Column("media_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default=sa.text("'primary'")),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint(
                "role IN ('primary','poster','fallback','explanation')",
                name="ck_question_media_role",
            ),
            sa.CheckConstraint("display_order >= 0", name="ck_question_media_display_order_nonnegative"),
            sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["media_id"], ["media_assets.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "question_id", "media_id", "role", name="uq_question_media_question_asset_role"
            ),
        )

    existing_question_indexes = _index_names(bind, "question_media")
    for name, columns in (
        ("ix_question_media_question_id", ["question_id"]),
        ("ix_question_media_media_id", ["media_id"]),
        ("ix_question_media_role", ["role"]),
        ("ix_question_media_question_role", ["question_id", "role"]),
    ):
        if name not in existing_question_indexes:
            op.create_index(name, "question_media", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "question_media"):
        op.drop_table("question_media")
    if _table_exists(bind, "media_assets"):
        op.drop_table("media_assets")
