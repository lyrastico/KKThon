import hashlib
import mimetypes
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from app.core.config import settings


def _s3_client():
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def guess_extension(filename: str | None, content_type: str | None) -> str:
    if filename:
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext and len(ext) <= 16:
            return ext
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""
        return ext.lstrip(".") or "bin"
    return "bin"


def build_raw_key(content: bytes, original_name: str | None, content_type: str | None) -> str:
    h = sha256_hex(content)
    ext = guess_extension(original_name, content_type)
    return f"raw/{h}.{ext}"


def upload_raw_file(
    content: bytes,
    *,
    original_filename: str | None,
    content_type: str | None,
    bucket: str | None = None,
) -> str:
    """Upload to S3; returns object key (e.g. raw/<sha256>.pdf)."""
    b = bucket or settings.aws_s3_bucket
    if not b:
        raise ValueError("AWS_S3_BUCKET is not configured")
    key = build_raw_key(content, original_filename, content_type)
    client = _s3_client()
    extra = {}
    if content_type:
        extra["ContentType"] = content_type.split(";")[0].strip()
    try:
        client.put_object(Bucket=b, Key=key, Body=content, **extra)
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}") from e
    return key


