"""Dealer import workflow reuses normal draft validation and upload authorization."""

import csv
import io
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity
from app.core.dependencies import CurrentUser, IdempotencyKey, Session
from app.core.errors import DomainError, require
from app.core.outbox import emit
from app.modules.listings.schemas import ListingCreate
from app.modules.listings.service import ListingService
from app.modules.users.service import UserService


class DealerImport(Identity, Base):
    __tablename__ = "dealer_imports"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    csv_text: Mapped[str] = mapped_column(String(200000))
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True)


class ImportInput(BaseModel):
    csv_text: str = Field(min_length=20, max_length=200000)
    rights_confirmed: Literal[True]


class ImportView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    rows: list[dict[str, Any]]


class DealerService:
    def __init__(self, session: Session) -> None:
        self.session = session

    async def authorized(self, user: UUID) -> None:
        """Check dealer grant and business verification before any bulk operation."""
        member = await UserService(self.session).active(user)
        require(
            member.role == "dealer", 403, "dealer_required", "Verified dealer account required."
        )
        require(
            await UserService(self.session).dealer_verified(user),
            403,
            "dealer_required",
            "Business verification required.",
        )

    async def create(self, user: UUID, data: ImportInput, key: str) -> ImportView:
        """Enqueue bounded CSV validation and draft creation."""
        from sqlalchemy import select

        await self.authorized(user)
        scoped = f"{user}:{key}"
        existing = await self.session.scalar(
            select(DealerImport).where(DealerImport.idempotency_key == scoped)
        )
        if existing:
            require(
                existing.csv_text == data.csv_text,
                409,
                "idempotency_conflict",
                "This key belongs to another import.",
            )
            return ImportView.model_validate(existing)
        job = DealerImport(user_id=user, csv_text=data.csv_text, idempotency_key=scoped)
        self.session.add(job)
        await self.session.flush()
        await emit(self.session, "dealer.import", {"import_id": str(job.id)})
        return ImportView.model_validate(job)

    async def status(self, user: UUID, job_id: UUID) -> ImportView:
        """Return only an authorized dealer's own import results."""
        await self.authorized(user)
        job = await self.session.get(DealerImport, job_id)
        require(job and job.user_id == user, 404, "import_missing", "Import not found.")
        return ImportView.model_validate(job)

    async def process(self, job_id: UUID) -> None:
        """Validate each CSV row independently and produce uploadable draft IDs."""
        from sqlalchemy import select

        job = await self.session.scalar(
            select(DealerImport).where(DealerImport.id == job_id).with_for_update()
        )
        if job is None or job.status == "completed":
            return
        await self.authorized(job.user_id)
        reader = csv.DictReader(io.StringIO(job.csv_text))
        results: list[dict[str, Any]] = []
        for index, row in enumerate(reader):
            if index >= 100:
                results.append({"row": index + 2, "error": "Maximum 100 rows per import."})
                break
            try:
                data = ListingCreate.model_validate(
                    {
                        "title": row.get("title"),
                        "description": row.get("description", ""),
                        "price_cents": row.get("price_cents"),
                        "area": row.get("area", "Dublin"),
                        "latitude": row.get("latitude", "53.3498"),
                        "longitude": row.get("longitude", "-6.2603"),
                        "rights_confirmed": True,
                        "car": {
                            key: row.get(key)
                            for key in [
                                "make",
                                "model",
                                "year",
                                "mileage_km",
                                "fuel",
                                "transmission",
                            ]
                        },
                    }
                )
                listing = await ListingService(self.session).create(
                    job.user_id, data, f"import:{job.id}:{index}"
                )
                results.append(
                    {
                        "row": index + 2,
                        "listing_id": str(listing.id),
                        "video_filename": row.get("video_filename", ""),
                    }
                )
            except (ValidationError, DomainError):
                results.append(
                    {"row": index + 2, "error": "Invalid or ineligible listing details."}
                )
        job.rows, job.status = results, "completed"


router = APIRouter(prefix="/dealer/imports", tags=["dealer"])


@router.post("", response_model=ImportView, status_code=202)
async def create(
    data: ImportInput, session: Session, user: CurrentUser, key: IdempotencyKey
) -> ImportView:
    return await DealerService(session).create(user, data, key)


@router.get("/{job_id}", response_model=ImportView)
async def status(job_id: UUID, session: Session, user: CurrentUser) -> ImportView:
    return await DealerService(session).status(user, job_id)
