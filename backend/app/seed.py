"""Original illustrated marketplace samples, strictly for local development."""

import asyncio
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5

from PIL import Image, ImageDraw, ImageFilter

from app.core.config import settings
from app.core.db import sessions, utcnow
from app.modules.listings.schemas import ListingCreate
from app.modules.listings.service import ListingService
from app.modules.media.models import MediaAsset
from app.modules.media.provider import LocalVideoProvider, run_ffmpeg, storage
from app.modules.users.models import Dealer, User

SEEDS = [
    (
        "Volkswagen Golf R-Line",
        "Volkswagen",
        "Golf",
        2021,
        42000,
        2495000,
        "petrol",
        "automatic",
        "Rathmines",
        (182, 193, 186),
    ),
    (
        "BMW 320d M Sport",
        "BMW",
        "320d",
        2020,
        68000,
        2795000,
        "diesel",
        "automatic",
        "Dundrum",
        (44, 83, 111),
    ),
    (
        "Toyota Yaris Hybrid",
        "Toyota",
        "Yaris",
        2022,
        26000,
        1995000,
        "hybrid",
        "automatic",
        "Clontarf",
        (189, 65, 51),
    ),
]
# Clearly labelled illustrations let the mixed marketplace be explored locally.
SEEDS += [
    (
        "Sample Dublin townhouse",
        "",
        "",
        2021,
        0,
        48500000,
        "petrol",
        "manual",
        "Rathmines",
        (212, 179, 124),
    ),
    (
        "Sample golf iron set",
        "",
        "",
        2021,
        0,
        32000,
        "petrol",
        "manual",
        "Clontarf",
        (177, 201, 158),
    ),
    ("Sample reading chair", "", "", 2021, 0, 8500, "petrol", "manual", "Dundrum", (206, 141, 110)),
]


def marketplace_art(path: Path, category: str) -> None:
    image = Image.new("RGB", (720, 1280), (28, 53, 43))
    draw = ImageDraw.Draw(image)
    draw.ellipse((380, 180, 850, 650), fill=(48, 78, 59))
    draw.rounded_rectangle((42, 110, 678, 1170), radius=32, outline=(110, 137, 96), width=2)
    draw.text((80, 160), "LOOP MARKETPLACE / SAMPLE INVENTORY", fill=(207, 226, 163))
    if category == "homes":
        draw.polygon([(110, 580), (360, 360), (610, 580)], fill=(170, 133, 93))
        draw.rectangle((150, 580, 570, 940), fill=(218, 197, 158))
        draw.rectangle((300, 750, 405, 940), fill=(55, 85, 65))
        for x in (205, 435):
            draw.rectangle((x, 630, x + 75, 710), fill=(99, 136, 133))
            draw.line((x + 37, 630, x + 37, 710), fill=(236, 225, 199), width=5)
    elif category == "golf":
        draw.ellipse((100, 910, 640, 990), fill=(57, 82, 52))
        for x in (220, 320, 420):
            draw.line((x, 400, x + 85, 895), fill=(184, 203, 190), width=13)
            draw.line((x, 400, x + 16, 495), fill=(54, 68, 59), width=22)
            draw.rounded_rectangle((x + 55, 870, x + 155, 930), radius=18, fill=(202, 215, 199))
    else:
        draw.rounded_rectangle((215, 480, 505, 820), radius=64, fill=(194, 128, 97))
        draw.rounded_rectangle((170, 730, 550, 900), radius=40, fill=(218, 154, 116))
        for x in (190, 480):
            draw.line((x, 850, x, 1010), fill=(155, 122, 81), width=25)
    draw.text((80, 1080), "ORIGINAL ILLUSTRATION - NOT A REAL ADVERT", fill=(196, 211, 171))
    image.save(path)


def car_art(path: Path, colour: tuple[int, int, int], variation: int) -> None:
    """Draw an original stylised car scene; no third-party imagery is used."""
    width, height = 720, 1280
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    assert pixels is not None
    for y in range(height):
        for x in range(width):
            glow = max(0, 1 - math.hypot((x - 500) / 850, (y - 380) / 950))
            pixels[x, y] = (int(19 + 43 * glow), int(42 + 57 * glow), int(38 + 39 * glow))
    draw = ImageDraw.Draw(image)
    draw.ellipse((480, 180, 565, 265), fill=(192, 201, 146))
    draw.polygon(
        [(0, 460), (180, 340), (340, 455), (520, 310), (720, 430), (720, 680), (0, 680)],
        fill=(43, 70, 58),
    )
    draw.polygon(
        [(0, 560), (170, 480), (330, 540), (570, 440), (720, 520), (720, 730), (0, 730)],
        fill=(31, 53, 46),
    )
    draw.polygon([(0, 680), (720, 640), (720, 1280), (0, 1280)], fill=(46, 58, 52))
    draw.polygon([(330, 675), (345, 675), (170, 1280), (120, 1280)], fill=(105, 116, 91))
    draw.line([(680, 665), (720, 710)], fill=(128, 141, 107), width=3)
    # Original low-angle three-quarter silhouette with glass, wheels and body highlights.
    shadow = Image.new("RGBA", image.size)
    ImageDraw.Draw(shadow).ellipse((75, 797, 705, 922), fill=(0, 10, 7, 160))
    image = Image.alpha_composite(
        image.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(24))
    )
    draw = ImageDraw.Draw(image)
    body = colour
    dark = (max(0, body[0] - 48), max(0, body[1] - 48), max(0, body[2] - 48))
    light = (min(255, body[0] + 35), min(255, body[1] + 35), min(255, body[2] + 35))
    for bounds in [(147, 727, 264, 881), (519, 727, 632, 873)]:
        draw.ellipse(bounds, fill=(11, 19, 18), outline=(69, 78, 72), width=4)
        inner = (bounds[0] + 18, bounds[1] + 20, bounds[2] - 18, bounds[3] - 20)
        draw.ellipse(inner, fill=(107, 119, 115), outline=(37, 49, 45), width=8)
        cx, cy = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
        for spoke in range(5):
            angle = spoke * 2 * math.pi / 5 + variation * 0.2
            draw.line(
                (cx, cy, cx + 29 * math.cos(angle), cy + 43 * math.sin(angle)),
                fill=(194, 202, 193),
                width=5,
            )
        draw.ellipse((cx - 8, cy - 10, cx + 8, cy + 10), fill=(38, 52, 45))
    draw.polygon(
        [
            (93, 729),
            (142, 658),
            (239, 627),
            (305, 541),
            (460, 534),
            (556, 609),
            (646, 637),
            (686, 730),
            (660, 809),
            (614, 822),
            (600, 751),
            (550, 720),
            (515, 752),
            (510, 831),
            (268, 842),
            (259, 763),
            (225, 729),
            (175, 751),
            (145, 825),
            (99, 803),
        ],
        fill=body,
    )
    draw.polygon(
        [(141, 657), (239, 627), (305, 541), (460, 534), (556, 609), (374, 638)], fill=light
    )
    draw.polygon([(258, 620), (316, 553), (372, 548), (363, 627)], fill=(31, 58, 57))
    draw.polygon([(385, 547), (450, 548), (531, 607), (377, 627)], fill=(25, 47, 47))
    draw.polygon([(287, 601), (325, 557), (345, 555)], fill=(125, 158, 144))
    draw.polygon([(104, 716), (375, 672), (652, 690), (676, 727), (389, 722)], fill=light)
    draw.polygon([(103, 742), (149, 758), (145, 814), (101, 799)], fill=dark)
    draw.polygon([(272, 802), (511, 788), (510, 831), (268, 842)], fill=dark)
    draw.line([(374, 639), (385, 784)], fill=dark, width=3)
    draw.line([(477, 633), (494, 783)], fill=dark, width=3)
    draw.rounded_rectangle((410, 670, 442, 676), radius=3, fill=dark)
    draw.polygon([(540, 690), (646, 699), (651, 719), (541, 711)], fill=(226, 242, 207))
    draw.polygon([(545, 730), (659, 739), (649, 787), (544, 777)], fill=(22, 34, 31))
    for offset in range(0, 96, 12):
        draw.line([(551 + offset, 740), (549 + offset, 773)], fill=(63, 78, 67), width=3)
    draw.polygon([(564, 757), (632, 763), (629, 782), (563, 775)], fill=(226, 232, 213))
    draw.text((570, 763), "LOOP MARKETPLACE", fill=(37, 54, 40))
    draw.polygon([(158, 677), (176, 668), (180, 694), (160, 700)], fill=(198, 82, 66))
    draw.polygon([(375, 637), (400, 620), (417, 628), (412, 645)], fill=dark)
    # Small typographic markers make the synthetic nature of demo inventory explicit.
    draw.text((42, 130), "LOOP MARKETPLACE ORIGINAL / SAMPLE INVENTORY", fill=(167, 189, 155))
    draw.text(
        (43, 1120), "ORIGINAL ILLUSTRATION - NOT A VEHICLE ADVERTISEMENT", fill=(145, 166, 134)
    )
    image.convert("RGB").save(path)


def initialize_storage() -> None:
    cfg, client = settings(), storage()
    for bucket in [cfg.source_bucket, cfg.playback_bucket]:
        if not any(item["Name"] == bucket for item in client.list_buckets()["Buckets"]):
            client.create_bucket(Bucket=bucket)
    client.put_bucket_policy(
        Bucket=cfg.playback_bucket,
        Policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{cfg.playback_bucket}/*"],
                    },
                ],
            }
        ),
    )
    client.put_bucket_lifecycle_configuration(
        Bucket=cfg.source_bucket,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "abort-abandoned-uploads",
                    "Status": "Enabled",
                    "Filter": {"Prefix": ""},
                    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                },
            ]
        },
    )
    for bucket in [cfg.source_bucket, cfg.playback_bucket]:
        client.put_bucket_cors(
            Bucket=bucket,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedOrigins": [cfg.public_origin],
                        "AllowedMethods": ["GET", "HEAD", "PUT"],
                        "AllowedHeaders": ["*"],
                        "ExposeHeaders": ["ETag"],
                        "MaxAgeSeconds": 300,
                    }
                ]
            },
        )


async def seed() -> None:
    if not settings().seed_enabled or settings().app_env == "production":
        return
    initialize_storage()
    async with sessions() as session:
        seller_id, admin_id = (
            uuid5(NAMESPACE_URL, "motorloop:dealer"),
            uuid5(NAMESPACE_URL, "motorloop:admin"),
        )
        if await session.get(User, seller_id) is None:
            session.add(
                User(
                    id=seller_id,
                    phone="+353860000001",
                    name="Greenline Motors",
                    role="dealer",
                    adult_declared=True,
                    verified_at=utcnow(),
                )
            )
            session.add(
                User(
                    id=admin_id,
                    phone="+353860000099",
                    name="Local moderator",
                    role="admin",
                    adult_declared=True,
                    verified_at=utcnow(),
                )
            )
            await session.flush()
            session.add(
                Dealer(
                    user_id=seller_id,
                    business_name="Greenline Motors (sample)",
                    registration_number="LOCAL-DEMO-ONLY",
                    address="Dublin, Ireland",
                    verified_at=utcnow(),
                )
            )
        await session.commit()
        for index, (
            title,
            make,
            model,
            year,
            mileage,
            price,
            fuel,
            transmission,
            area,
            colour,
        ) in enumerate(SEEDS):
            data = ListingCreate.model_validate(
                {
                    "title": title,
                    "description": "Original illustrated sample inventory for local development. Explore the short video and try arranging a viewing. This is not a real advert.",
                    "price_cents": price,
                    "category": ["cars", "cars", "cars", "homes", "golf", "other"][index],
                    "attributes": (
                        {"property_type": "house", "bedrooms": 3, "bathrooms": 2}
                        if index == 3
                        else {
                            "brand": "Sample",
                            "condition": "good",
                            "club_type": "irons",
                            "hand": "right",
                        }
                        if index == 4
                        else {"condition": "good"}
                        if index == 5
                        else {}
                    ),
                    "area": area,
                    "latitude": 53.3498 + index * 0.012,
                    "longitude": -6.2603 + index * 0.009,
                    "rights_confirmed": True,
                    "car": {
                        "make": make,
                        "model": model,
                        "year": year,
                        "mileage_km": mileage,
                        "fuel": fuel,
                        "transmission": transmission,
                    }
                    if index < 3
                    else None,
                }
            )
            service = ListingService(session)
            listing = await service.repo.by_key(
                seller_id, f"seed-listing-{index}"
            ) or await service.create(seller_id, data, f"seed-listing-{index}")
            asset_id = uuid5(NAMESPACE_URL, f"motorloop:seed-asset:{index}")
            if await session.get(MediaAsset, asset_id):
                continue
            provider = LocalVideoProvider()
            with TemporaryDirectory() as temporary:
                folder = Path(temporary)
                poster, video = folder / "poster.png", folder / "video.mp4"
                if index < 3:
                    car_art(poster, colour, index)
                else:
                    marketplace_art(poster, data.category)
                run_ffmpeg(
                    [
                        "-loop",
                        "1",
                        "-i",
                        str(poster),
                        "-t",
                        "15",
                        "-vf",
                        "scale=720:1280,zoompan=z='min(zoom+0.00012,1.04)':d=360:s=360x640:fps=24",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-threads",
                        "2",
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                        str(video),
                    ]
                )
                key = f"seed/{asset_id}/source"
                storage().upload_file(str(video), settings().source_bucket, key)
                processed = provider.process(key, str(asset_id))
                provider.publish(str(asset_id))
                session.add(
                    MediaAsset(
                        id=asset_id,
                        listing_id=listing.id,
                        status="ready",
                        object_key=key,
                        upload_id="trusted-local-seed",
                        size_bytes=video.stat().st_size,
                        content_type="video/mp4",
                        playback_url=processed.playback_url,
                        poster_url=processed.poster_url,
                        duration=processed.duration,
                        perceptual_hash=processed.perceptual_hash,
                        idempotency_key=f"seed-{index}",
                        request_hash="seed",
                    )
                )
                await session.flush()
                await service.media_state(listing.id, "live")
                await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
