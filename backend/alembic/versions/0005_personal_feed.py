"""Explicit feed dismissals, reset cutoffs and bounded interest history lookup."""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feed_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "feed_dismissals",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_user_history", "events", ["user_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_events_user_history", table_name="events")
    op.drop_table("feed_dismissals")
    op.drop_table("feed_preferences")
