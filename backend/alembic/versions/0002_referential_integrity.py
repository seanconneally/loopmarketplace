"""Add cross-domain referential integrity without granting cross-domain query access."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

REFERENCES = [
    ("listings", "seller_id", "users"),
    ("saves", "user_id", "users"),
    ("refresh_sessions", "user_id", "users"),
    ("media_assets", "listing_id", "listings"),
    ("conversations", "listing_id", "listings"),
    ("conversations", "buyer_id", "users"),
    ("conversations", "seller_id", "users"),
    ("messages", "sender_id", "users"),
    ("messages", "viewing_id", "viewings"),
    ("viewings", "conversation_id", "conversations"),
    ("viewings", "proposed_by", "users"),
    ("reports", "reporter_id", "users"),
    ("blocks", "blocker_id", "users"),
    ("blocks", "blocked_id", "users"),
    ("moderation_actions", "moderator_id", "users"),
    ("notifications", "user_id", "users"),
    ("events", "user_id", "users"),
    ("events", "listing_id", "listings"),
    ("dealer_imports", "user_id", "users"),
]


def upgrade() -> None:
    for table, column, target in REFERENCES:
        op.create_foreign_key(f"fk_{table}_{column}_{target}", table, target, [column], ["id"])


def downgrade() -> None:
    for table, column, target in reversed(REFERENCES):
        op.drop_constraint(f"fk_{table}_{column}_{target}", table, type_="foreignkey")
