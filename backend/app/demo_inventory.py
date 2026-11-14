"""Optional, repeatable pilot catalogue. Every advert and video is synthetic."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5

from PIL import Image, ImageDraw

from app.core.config import settings
from app.core.db import sessions, utcnow
from app.modules.listings.schemas import ListingCreate
from app.modules.listings.service import ListingService
from app.modules.media.models import MediaAsset
from app.modules.media.provider import LocalVideoProvider, run_ffmpeg, storage
from app.modules.users.models import User
from app.seed import car_art, marketplace_art, seed

AREAS = [
    ("Rathmines", 53.323, -6.265),
    ("Dundrum", 53.289, -6.242),
    ("Clontarf", 53.359, -6.198),
    ("Smithfield", 53.349, -6.279),
    ("Swords", 53.459, -6.218),
    ("Dún Laoghaire", 53.294, -6.135),
    ("Lucan", 53.357, -6.449),
    ("Tallaght", 53.289, -6.371),
]
COLOURS = [(73, 112, 144), (183, 88, 67), (127, 145, 105), (194, 173, 119)]


def catalogue() -> list[ListingCreate]:
    """Validate all fixtures before touching the database or encoding any video."""
    rows: list[dict[str, object]] = []
    for make, model, year, mileage, price, fuel, gearbox in [
        ("Ford", "Fiesta", 2018, 92000, 1095000, "petrol", "manual"),
        ("Skoda", "Octavia", 2020, 78000, 1845000, "diesel", "manual"),
        ("Tesla", "Model 3", 2022, 41000, 2995000, "electric", "automatic"),
        ("Hyundai", "Ioniq 5", 2023, 22000, 3595000, "electric", "automatic"),
        ("Honda", "Jazz", 2021, 35000, 1695000, "hybrid", "automatic"),
        ("Kia", "Sportage", 2019, 86000, 1995000, "diesel", "manual"),
    ]:
        rows.append(
            {
                "category": "cars",
                "title": f"Demo · {make} {model}",
                "price_cents": price,
                "car": {
                    "make": make,
                    "model": model,
                    "year": year,
                    "mileage_km": mileage,
                    "fuel": fuel,
                    "transmission": gearbox,
                },
            }
        )
    for title, kind, bedrooms, bathrooms, area, price in [
        ("City studio", "apartment", 0, 1, 35, 21500000),
        ("One-bedroom apartment", "apartment", 1, 1, 52, 28500000),
        ("Two-bedroom apartment", "apartment", 2, 2, 80, 37500000),
        ("Three-bedroom terrace", "house", 3, 2, 110, 49500000),
        ("Four-bedroom family home", "house", 4, 3, 155, 68500000),
        ("Two-bedroom bungalow", "house", 2, 1, 90, 42500000),
    ]:
        rows.append(
            {
                "category": "homes",
                "title": f"Demo · {title}",
                "price_cents": price,
                "attributes": {
                    "property_type": kind,
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "floor_area_m2": area,
                },
            }
        )
    for title, brand, kind, hand, condition, price in [
        ("Left-handed driver", "Demo North", "driver", "left", "good", 12000),
        ("Mallet putter", "Demo Links", "putter", "right", "like_new", 8500),
        ("Wedge pair", "Demo Coast", "wedge", "right", "good", 11000),
        ("Beginner club set", "Demo Links", "set", "right", "fair", 18000),
        ("Forged iron set", "Demo North", "irons", "right", "like_new", 45000),
        ("Junior club set", "Demo Coast", "set", "either", "good", 6500),
    ]:
        rows.append(
            {
                "category": "golf",
                "title": f"Demo · {title}",
                "price_cents": price,
                "attributes": {
                    "brand": brand,
                    "club_type": kind,
                    "hand": hand,
                    "condition": condition,
                },
            }
        )
    for title, condition, price in [
        ("Linen reading chair", "like_new", 9500),
        ("Vintage armchair", "fair", 4500),
        ("Oak-frame lounge chair", "good", 12500),
        ("Compact bedroom chair", "good", 5500),
        ("Upholstered accent chair", "like_new", 15000),
        ("Restoration chair", "fair", 2500),
    ]:
        rows.append(
            {
                "category": "other",
                "title": f"Demo · {title}",
                "price_cents": price,
                "attributes": {"brand": "Demo Home", "condition": condition},
            }
        )
    result = []
    for index, row in enumerate(rows):
        name, latitude, longitude = AREAS[index % len(AREAS)]
        result.append(
            ListingCreate.model_validate(
                {
                    **row,
                    "area": name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "rights_confirmed": True,
                    "description": "Synthetic demo advert, not an item or property offered for sale. "
                    "The original category illustration is for testing discovery, filters and video playback. "
                    "Seller profiles, prices and details are fictional. No payment or real viewing is available.",
                }
            )
        )
    return result


def make_clip(folder: Path, data: ListingCreate, index: int) -> Path:
    poster, video = folder / "poster.png", folder / "video.mp4"
    if data.category == "cars":
        car_art(poster, COLOURS[index % len(COLOURS)], index)
    else:
        marketplace_art(poster, data.category)
    with Image.open(poster) as illustration:
        draw = ImageDraw.Draw(illustration)
        draw.rectangle((42, 50, 678, 110), fill=COLOURS[index % len(COLOURS)])
        draw.text((60, 70), data.title.replace("·", "/"), fill="white")
        illustration.save(poster)
    # A few fixtures include an original synthetic tone to exercise mute/unmute.
    audio = index % 6 == 0
    run_ffmpeg(
        [
            "-loop",
            "1",
            "-i",
            str(poster),
            *(
                ["-f", "lavfi", "-i", f"sine=frequency={220 + index * 10}:sample_rate=48000"]
                if audio
                else []
            ),
            "-t",
            "15",
            "-vf",
            "scale=360:640",
            "-r",
            "24",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-threads",
            "2",
            "-pix_fmt",
            "yuv420p",
            *(["-c:a", "aac", "-b:a", "64k"] if audio else []),
            "-movflags",
            "+faststart",
            str(video),
        ]
    )
    return video


async def expand() -> None:
    if settings().app_env != "development" or not settings().seed_enabled:
        raise RuntimeError("Demo inventory is available only in development with seeding enabled.")
    fixtures = catalogue()
    await seed()  # Preserve the original six fixture keys and all existing member data.
    async with sessions() as session:
        for seller_index in range(4):
            seller_id = uuid5(NAMESPACE_URL, f"motorloop:demo-member:{seller_index}")
            if await session.get(User, seller_id) is None:
                session.add(
                    User(
                        id=seller_id,
                        phone=f"+35386000900{seller_index}",
                        name=f"Demo seller {seller_index + 1}",
                        verified_at=utcnow(),
                        adult_declared=True,
                    )
                )
        await session.commit()
        added = 0
        for index, data in enumerate(fixtures):
            seller_id = uuid5(NAMESPACE_URL, f"motorloop:demo-member:{index % 4}")
            asset_id = uuid5(NAMESPACE_URL, f"motorloop:demo-media:v1:{index}")
            if await session.get(MediaAsset, asset_id):
                continue
            key = f"demo-inventory-v1-{index}"
            service = ListingService(session)
            listing = await service.repo.by_key(seller_id, key) or await service.create(
                seller_id, data, key
            )
            # Do not reactivate an advert a developer has deliberately closed.
            if listing.status not in {"draft", "failed"}:
                continue
            provider = LocalVideoProvider()
            with TemporaryDirectory(prefix="loop-demo-") as temporary:
                video = await asyncio.to_thread(make_clip, Path(temporary), data, index)
                object_key = f"demo-inventory/{asset_id}/source"
                await asyncio.to_thread(
                    storage().upload_file, str(video), settings().source_bucket, object_key
                )
                processed = await asyncio.to_thread(provider.process, object_key, str(asset_id))
                await asyncio.to_thread(provider.publish, str(asset_id))
                session.add(
                    MediaAsset(
                        id=asset_id,
                        listing_id=listing.id,
                        status="ready",
                        object_key=object_key,
                        upload_id="trusted-local-demo",
                        size_bytes=video.stat().st_size,
                        content_type="video/mp4",
                        playback_url=processed.playback_url,
                        poster_url=processed.poster_url,
                        duration=processed.duration,
                        perceptual_hash=processed.perceptual_hash,
                        has_audio=processed.has_audio,
                        idempotency_key=key,
                        request_hash="trusted-local-demo",
                    )
                )
                await session.flush()
                await service.media_state(listing.id, "live")
                await session.commit()
                added += 1
                print(f"Demo inventory {index + 1}/{len(fixtures)}: {data.title}", flush=True)
        print(f"Added {added} demo adverts; existing fixtures were preserved.", flush=True)


if __name__ == "__main__":
    asyncio.run(expand())
