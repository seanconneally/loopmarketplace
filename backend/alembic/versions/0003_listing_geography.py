"""Keep the source listing's geographic point consistent with validated coordinates."""

import sqlalchemy as sa
from geoalchemy2 import Geography

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column(
            "location",
            Geography("POINT", srid=4326, spatial_index=False),
            sa.Computed(
                "ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography", persisted=True
            ),
            nullable=False,
        ),
    )
    op.create_index("ix_listings_location", "listings", ["location"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_listings_location", table_name="listings")
    op.drop_column("listings", "location")
