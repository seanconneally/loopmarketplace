"""Seller lifecycle, resumable file identity and audio metadata."""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listings", sa.Column("revision", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "listings", sa.Column("is_paused", sa.Boolean(), nullable=False, server_default="false")
    )
    op.drop_constraint(op.f("ck_listings_valid_status"), "listings", type_="check")
    op.create_check_constraint(
        op.f("ck_listings_valid_status"),
        "listings",
        "status in ('draft','processing','pending_review','live','paused','sold','removed','failed')",
    )
    op.create_index("ix_listings_owner_history", "listings", ["seller_id", "created_at", "id"])
    for column in [
        sa.Column("original_filename", sa.String(200), nullable=False, server_default=""),
        sa.Column("file_sha256", sa.String(64)),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_key", sa.String(64)),
        sa.Column("error_code", sa.String(64)),
        sa.Column("has_audio", sa.Boolean(), nullable=False, server_default="false"),
    ]:
        op.add_column("media_assets", column)


def downgrade() -> None:
    # Never silently republish a paused advert during rollback.
    op.execute("UPDATE listings SET status='draft' WHERE status='paused'")
    op.drop_constraint(op.f("ck_listings_valid_status"), "listings", type_="check")
    op.create_check_constraint(
        op.f("ck_listings_valid_status"),
        "listings",
        "status in ('draft','processing','pending_review','live','sold','removed','failed')",
    )
    op.drop_index("ix_listings_owner_history", table_name="listings")
    op.drop_column("listings", "is_paused")
    op.drop_column("listings", "revision")
    for name in [
        "original_filename",
        "file_sha256",
        "generation",
        "retry_count",
        "retry_key",
        "error_code",
        "has_audio",
    ]:
        op.drop_column("media_assets", name)
