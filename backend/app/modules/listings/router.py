from typing import Literal
from uuid import UUID

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, IdempotencyKey, OptionalUser, Session
from app.modules.listings.schemas import (
    ListingAction,
    ListingCreate,
    ListingPage,
    ListingUpdate,
    ListingView,
    SellerListingPage,
    SellerListingView,
)
from app.modules.listings.service import ListingService

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", response_model=ListingView, status_code=201)
async def create(
    data: ListingCreate, session: Session, user: CurrentUser, key: IdempotencyKey
) -> ListingView:
    service = ListingService(session)
    listing = await service.create(user, data, key)
    return await service.detail(listing.id, user)


@router.get("/saved", response_model=ListingPage)
async def saved(session: Session, user: CurrentUser, cursor: str | None = None) -> ListingPage:
    return await ListingService(session).saved_page(user, cursor)


@router.get("/mine", response_model=SellerListingPage)
async def mine(
    session: Session,
    user: CurrentUser,
    cursor: str | None = None,
    status: Literal[
        "draft", "processing", "pending_review", "live", "paused", "sold", "removed", "failed"
    ]
    | None = None,
) -> SellerListingPage:
    return await ListingService(session).mine(user, cursor, status)


@router.get("/{listing_id}", response_model=ListingView)
async def detail(listing_id: UUID, session: Session, user: OptionalUser) -> ListingView:
    return await ListingService(session).detail(listing_id, user)


@router.get("/{listing_id}/owner", response_model=SellerListingView)
async def owner_detail(listing_id: UUID, session: Session, user: CurrentUser) -> SellerListingView:
    return await ListingService(session).seller_detail(listing_id, user)


@router.patch("/{listing_id}", response_model=SellerListingView)
async def update(
    listing_id: UUID, data: ListingUpdate, session: Session, user: CurrentUser
) -> SellerListingView:
    return await ListingService(session).update(listing_id, user, data)


@router.post("/{listing_id}/pause", response_model=SellerListingView)
async def pause(
    listing_id: UUID, data: ListingAction, session: Session, user: CurrentUser
) -> SellerListingView:
    return await ListingService(session).pause(listing_id, user, data.revision, True)


@router.post("/{listing_id}/resume", response_model=SellerListingView)
async def resume(
    listing_id: UUID, data: ListingAction, session: Session, user: CurrentUser
) -> SellerListingView:
    return await ListingService(session).pause(listing_id, user, data.revision, False)


@router.post("/{listing_id}/sold", response_model=ListingView)
async def sold(listing_id: UUID, session: Session, user: CurrentUser) -> ListingView:
    return await ListingService(session).sold(listing_id, user)


@router.put("/{listing_id}/save", status_code=204)
async def save(listing_id: UUID, session: Session, user: CurrentUser) -> None:
    await ListingService(session).save(listing_id, user, True)


@router.delete("/{listing_id}/save", status_code=204)
async def unsave(listing_id: UUID, session: Session, user: CurrentUser) -> None:
    await ListingService(session).save(listing_id, user, False)
