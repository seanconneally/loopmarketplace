"""Universal listing attributes and indexed category discovery; preserve existing cars."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listings", sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default="{}")
    )
    op.add_column(
        "feed_candidates",
        sa.Column("category", sa.String(30), nullable=False, server_default="cars"),
    )
    op.alter_column("feed_candidates", "make", nullable=True)
    op.alter_column("feed_candidates", "year", nullable=True)
    op.create_index(
        "ix_feed_category",
        "feed_candidates",
        ["region_id", "category", "published_at", "listing_id"],
    )


def downgrade() -> None:
    # Refuse to discard category facts or leave inventory unreadable by the old app.
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM listings WHERE category <> 'cars')")
    ):
        raise RuntimeError(
            "Cannot downgrade while non-car listings exist. Preserve or migrate that inventory first."
        )
    op.drop_index("ix_feed_category", table_name="feed_candidates")
    op.alter_column("feed_candidates", "make", nullable=False)
    op.alter_column("feed_candidates", "year", nullable=False)
    op.drop_column("feed_candidates", "category")
    op.drop_column("listings", "attributes")
