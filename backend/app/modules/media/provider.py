import hashlib
import json
import math
import mimetypes
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image

if TYPE_CHECKING:
    from types_boto3_s3.client import S3Client

from app.core.config import settings
from app.core.errors import DomainError, require

PART_SIZE = 8 * 1024 * 1024


def storage(public: bool = False) -> "S3Client":
    cfg = settings()
    return boto3.client(
        "s3",
        endpoint_url=cfg.storage_public_endpoint if public else cfg.storage_endpoint,
        aws_access_key_id=cfg.storage_access_key,
        aws_secret_access_key=cfg.storage_secret_key,
        region_name=cfg.storage_region,
        config=Config(
            signature_version="s3v4",
            connect_timeout=3,
            read_timeout=20,
            retries={"max_attempts": 2},
            s3={"addressing_style": "path"},
        ),
    )


@dataclass(frozen=True)
class ProcessedVideo:
    playback_url: str
    poster_url: str
    duration: float
    perceptual_hash: str
    has_audio: bool = False


@dataclass(frozen=True)
class UploadProgress:
    parts: list[tuple[int, str]]
    uploaded_bytes: int
    complete: bool = False


class VideoProvider(Protocol):
    def create_upload(self, key: str, content_type: str) -> str: ...
    def part_urls(self, key: str, upload_id: str, size: int) -> list[str]: ...
    def complete(
        self, key: str, upload_id: str, parts: list[tuple[int, str]], size: int
    ) -> None: ...
    def progress(self, key: str, upload_id: str, size: int) -> UploadProgress: ...
    def abort(self, key: str, upload_id: str) -> None: ...
    def source_ready(self, key: str, size: int) -> bool: ...
    def process(
        self, key: str, asset_id: str, expected_sha256: str | None = None
    ) -> ProcessedVideo: ...
    def publish(self, asset_id: str) -> None: ...


def run_ffmpeg(arguments: list[str], timeout: int = 120) -> None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *arguments],
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise DomainError(422, "invalid_video", "Video could not be processed.")


def perceptual_hash(path: Path) -> str:
    with Image.open(path) as image:
        pixels = list(image.convert("L").resize((9, 8)).getdata())
    bits = sum(
        (1 << (row * 8 + col))
        for row in range(8)
        for col in range(8)
        if pixels[row * 9 + col] > pixels[row * 9 + col + 1]
    )
    return f"{bits:016x}"


class LocalVideoProvider:
    """Development ffmpeg implementation; production managed adapter is a release gate."""

    def create_upload(self, key: str, content_type: str) -> str:
        result = storage().create_multipart_upload(
            Bucket=settings().source_bucket, Key=key, ContentType=content_type
        )
        return result["UploadId"]

    def part_urls(self, key: str, upload_id: str, size: int) -> list[str]:
        return [
            storage(public=True).generate_presigned_url(
                "upload_part",
                Params={
                    "Bucket": settings().source_bucket,
                    "Key": key,
                    "UploadId": upload_id,
                    "PartNumber": number,
                },
                ExpiresIn=900,
            )
            for number in range(1, math.ceil(size / PART_SIZE) + 1)
        ]

    def source_ready(self, key: str, size: int) -> bool:
        try:
            return (
                storage().head_object(Bucket=settings().source_bucket, Key=key)["ContentLength"]
                == size
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def progress(self, key: str, upload_id: str, size: int) -> UploadProgress:
        client = storage()
        try:
            uploaded = client.list_parts(
                Bucket=settings().source_bucket, Key=key, UploadId=upload_id
            ).get("Parts", [])
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "NoSuchUpload":
                raise
            require(
                self.source_ready(key, size),
                410,
                "upload_expired",
                "This upload session expired. Start over on the same advert.",
            )
            return UploadProgress([], size, complete=True)
        parts: list[tuple[int, str]] = []
        total = 0
        for part in uploaded:
            number = part.get("PartNumber", 0)
            expected_size = min(PART_SIZE, max(0, size - (number - 1) * PART_SIZE))
            if (
                1 <= number <= math.ceil(size / PART_SIZE)
                and part.get("Size") == expected_size
                and part.get("ETag")
            ):
                parts.append((number, part["ETag"]))
                total += expected_size
        return UploadProgress(parts, total)

    def abort(self, key: str, upload_id: str) -> None:
        try:
            storage().abort_multipart_upload(
                Bucket=settings().source_bucket, Key=key, UploadId=upload_id
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "NoSuchUpload":
                raise

    def complete(self, key: str, upload_id: str, parts: list[tuple[int, str]], size: int) -> None:
        client = storage()
        try:
            uploaded = client.list_parts(
                Bucket=settings().source_bucket, Key=key, UploadId=upload_id
            ).get("Parts", [])
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "NoSuchUpload":
                raise
            # S3 may have completed successfully just before a process/response loss.
            head = client.head_object(Bucket=settings().source_bucket, Key=key)
            require(
                head["ContentLength"] == size,
                422,
                "size_mismatch",
                "Completed object size differs from declaration.",
            )
            return
        require(
            sum(part.get("Size", 0) for part in uploaded) == size,
            422,
            "size_mismatch",
            "Upload size differs from declaration.",
        )
        expected = [(part.get("PartNumber"), part.get("ETag")) for part in uploaded]
        require(
            parts == expected and len(parts) == math.ceil(size / PART_SIZE),
            422,
            "parts_mismatch",
            "Uploaded parts do not match completion request.",
        )
        client.complete_multipart_upload(
            Bucket=settings().source_bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={
                "Parts": [{"PartNumber": number, "ETag": etag} for number, etag in parts]
            },
        )

    def process(
        self, key: str, asset_id: str, expected_sha256: str | None = None
    ) -> ProcessedVideo:
        cfg, client = settings(), storage()
        head = client.head_object(Bucket=cfg.source_bucket, Key=key)
        require(
            0 < head["ContentLength"] <= 500 * 1024 * 1024, 422, "size_limit", "Video is too large."
        )
        with TemporaryDirectory(prefix="motorloop-") as temporary:
            folder = Path(temporary)
            source = folder / "source.mp4"
            client.download_file(cfg.source_bucket, key, str(source))
            if expected_sha256:
                with source.open("rb") as uploaded:
                    require(
                        hashlib.file_digest(uploaded, "sha256").hexdigest() == expected_sha256,
                        422,
                        "file_mismatch",
                        "The video does not match the selected original. Start over with the correct file.",
                    )
            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_format",
                    "-show_streams",
                    "-of",
                    "json",
                    str(source),
                ],
                capture_output=True,
                timeout=30,
                check=False,
            )
            require(
                probe.returncode == 0,
                422,
                "invalid_video",
                "Video could not be read. Choose a valid MP4 or MOV.",
            )
            metadata = json.loads(probe.stdout)
            has_audio = any(stream["codec_type"] == "audio" for stream in metadata["streams"])
            duration = float(metadata["format"]["duration"])
            require(15 <= duration <= 60.1, 422, "duration_limit", "Video must be 15–60 seconds.")
            require(
                "mp4" in metadata["format"]["format_name"]
                or "mov" in metadata["format"]["format_name"],
                422,
                "invalid_container",
                "Use an MP4 or MOV file.",
            )
            require(
                any(stream["codec_type"] == "video" for stream in metadata["streams"]),
                422,
                "missing_video",
                "No video stream found.",
            )
            output = folder / "output"
            output.mkdir()
            for width, height, bitrate in [(360, 640, "650k"), (720, 1280, "1800k")]:
                rendition = output / str(height)
                rendition.mkdir()
                run_ffmpeg(
                    [
                        "-i",
                        str(source),
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a:0?",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "96k",
                        "-ac",
                        "2",
                        "-ar",
                        "48000",
                        "-map_metadata",
                        "-1",
                        "-vf",
                        f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-threads",
                        "2",
                        "-pix_fmt",
                        "yuv420p",
                        "-b:v",
                        bitrate,
                        "-r",
                        "24",
                        "-g",
                        "48",
                        "-sc_threshold",
                        "0",
                        "-hls_time",
                        "2",
                        "-hls_list_size",
                        "0",
                        "-hls_playlist_type",
                        "vod",
                        "-hls_segment_filename",
                        str(rendition / "%04d.ts"),
                        str(rendition / "index.m3u8"),
                    ]
                )
            (output / "master.m3u8").write_text(
                "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=850000,RESOLUTION=360x640\n640/index.m3u8\n"
                "#EXT-X-STREAM-INF:BANDWIDTH=2150000,RESOLUTION=720x1280\n1280/index.m3u8\n",
                encoding="utf-8",
            )
            run_ffmpeg(
                [
                    "-ss",
                    "1",
                    "-i",
                    str(source),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=360:-2",
                    str(output / "poster.jpg"),
                ]
            )
            run_ffmpeg(
                [
                    "-i",
                    str(source),
                    "-vf",
                    "fps=1/5,scale=120:-2,tile=4x3",
                    "-frames:v",
                    "1",
                    str(output / "thumbnails.jpg"),
                ]
            )
            for path in output.rglob("*"):
                if path.is_file():
                    relative = path.relative_to(output).as_posix()
                    content_type = (
                        "application/vnd.apple.mpegurl"
                        if path.suffix == ".m3u8"
                        else "video/mp2t"
                        if path.suffix == ".ts"
                        else mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                    )
                    client.upload_file(
                        str(path),
                        cfg.source_bucket,
                        f"processed/{asset_id}/{relative}",
                        ExtraArgs={"ContentType": content_type, "CacheControl": "private,no-store"},
                    )
            return ProcessedVideo(
                f"{cfg.media_public_url}/{asset_id}/master.m3u8",
                f"{cfg.media_public_url}/{asset_id}/poster.jpg",
                duration,
                perceptual_hash(output / "poster.jpg"),
                has_audio,
            )

    def publish(self, asset_id: str) -> None:
        """Copy reviewed derivatives from private quarantine to the playback origin."""
        cfg, client = settings(), storage()
        prefix = f"processed/{asset_id}/"
        for page in client.get_paginator("list_objects_v2").paginate(
            Bucket=cfg.source_bucket, Prefix=prefix
        ):
            for item in page.get("Contents", []):
                key = item["Key"]
                client.copy_object(
                    Bucket=cfg.playback_bucket,
                    Key=f"{asset_id}/{key.removeprefix(prefix)}",
                    CopySource={"Bucket": cfg.source_bucket, "Key": key},
                    MetadataDirective="REPLACE",
                    ContentType="application/vnd.apple.mpegurl"
                    if key.endswith(".m3u8")
                    else "video/mp2t"
                    if key.endswith(".ts")
                    else "image/jpeg",
                    CacheControl="public,max-age=300",
                )
