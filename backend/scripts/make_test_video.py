"""Generate a new original test clip, avoiding a duplicate of seeded car artwork."""

import argparse
import secrets
import struct
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from app.modules.media.provider import run_ffmpeg

parser = argparse.ArgumentParser()
parser.add_argument("destination", nargs="?", default="/tmp/walkaround.mp4")
parser.add_argument("--silent", action="store_true")
parser.add_argument("--padding-mib", type=int, default=0)
args = parser.parse_args()
destination = args.destination
with TemporaryDirectory() as temporary:
    poster = Path(temporary) / "test-art.png"
    image = Image.new("RGB", (360, 640))
    draw = ImageDraw.Draw(image)
    for row in range(8):
        for column in range(9):
            value = secrets.randbelow(220) + 20
            draw.rectangle(
                (column * 40, row * 80, (column + 1) * 40, (row + 1) * 80),
                fill=(value, value, value),
            )
    image.save(poster)
    run_ffmpeg(
        [
            "-loop",
            "1",
            "-i",
            str(poster),
            *(
                []
                if args.silent
                else [
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "96k",
                ]
            ),
            "-t",
            "15",
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
            "-movflags",
            "+faststart",
            destination,
        ]
    )
if args.padding_mib:
    # A valid ignored MP4 box exercises multipart resume without expensive noisy footage.
    with Path(destination).open("ab") as video:
        video.write(struct.pack(">I4s", args.padding_mib * 1024 * 1024 + 8, b"free"))
        for _ in range(args.padding_mib):
            video.write(bytes(1024 * 1024))
