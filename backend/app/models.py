"""Metadata registration only; domain code must use service interfaces."""

from app.core.outbox import DeadLetter, Outbox
from app.modules.analytics.models import Event
from app.modules.auth.models import RefreshSession
from app.modules.feed.models import Candidate
from app.modules.listings.dealer import DealerImport
from app.modules.listings.models import CarDetails, Listing, Save
from app.modules.media.models import MediaAsset
from app.modules.messaging.models import Conversation, Message
from app.modules.moderation.models import Block, ModerationAction, Report
from app.modules.notifications.models import Notification
from app.modules.users.models import Dealer, User
from app.modules.viewings.models import Viewing

__all__ = [
    "DeadLetter",
    "Outbox",
    "Event",
    "RefreshSession",
    "Candidate",
    "CarDetails",
    "Listing",
    "Save",
    "MediaAsset",
    "Conversation",
    "Message",
    "Block",
    "ModerationAction",
    "Report",
    "Notification",
    "Dealer",
    "User",
    "Viewing",
    "DealerImport",
]
