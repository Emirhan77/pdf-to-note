from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from uuid import uuid4


def upload_pdf(pdf_path: Path) -> str:
    """Upload a PDF to configured cloud storage and return an access URL.

    When cloud storage is not configured, the application keeps its existing
    local-only behavior and returns an empty URL.
    """
    provider = os.getenv("CLOUD_STORAGE_PROVIDER", "local").strip().lower()
    if provider in {"", "local", "none"}:
        return ""
    if provider != "aws_s3":
        raise RuntimeError(f"Desteklenmeyen CLOUD_STORAGE_PROVIDER: {provider}")
    return _upload_pdf_to_s3(pdf_path)


def _upload_pdf_to_s3(pdf_path: Path) -> str:
    bucket = os.getenv("AWS_S3_BUCKET", "").strip()
    region = os.getenv("AWS_REGION", "").strip() or os.getenv("AWS_DEFAULT_REGION", "").strip()
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET ayari bulunamadi.")
    if not region:
        raise RuntimeError("AWS_REGION ayari bulunamadi.")

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise RuntimeError("boto3 kurulu degil. `pip install -r requirements.txt` calistirin.") from exc

    key_prefix = os.getenv("AWS_S3_KEY_PREFIX", "uploads").strip().strip("/") or "uploads"
    object_key = f"{key_prefix}/{uuid4().hex}_{pdf_path.name}"
    content_type = mimetypes.guess_type(str(pdf_path))[0] or "application/pdf"

    client = boto3.client("s3", region_name=region)
    try:
        client.upload_file(
            str(pdf_path),
            bucket,
            object_key,
            ExtraArgs={
                "ContentType": content_type,
                "ServerSideEncryption": "AES256",
            },
        )
        expires_in = int(os.getenv("AWS_PRESIGNED_URL_EXPIRES", "604800"))
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"AWS S3 yukleme basarisiz: {exc}") from exc
