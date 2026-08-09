"""MinIO S3 client. Every asset flows: upload → temp bucket → ClamAV → assets bucket."""

from __future__ import annotations
import logging
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.config import settings

log = logging.getLogger("minio")


def _client() -> Minio:
    return Minio(
        f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,
    )


async def ensure_buckets() -> None:
    c = _client()
    for bucket in (settings.MINIO_BUCKET_TEMP, settings.MINIO_BUCKET_ASSETS):
        try:
            if not c.bucket_exists(bucket):
                c.make_bucket(bucket)
                log.info("Created MinIO bucket %s", bucket)
        except S3Error as e:
            log.error("MinIO bucket ensure failed for %s: %s", bucket, e)


def put_temp(object_name: str, data: BinaryIO, size: int, content_type: str) -> str:
    _client().put_object(
        settings.MINIO_BUCKET_TEMP,
        object_name,
        data,
        length=size,
        content_type=content_type,
    )
    return f"s3://{settings.MINIO_BUCKET_TEMP}/{object_name}"


def promote_to_assets(temp_object_name: str, target_object_name: str) -> str:
    from minio.commonconfig import CopySource

    c = _client()
    c.copy_object(
        settings.MINIO_BUCKET_ASSETS,
        target_object_name,
        CopySource(settings.MINIO_BUCKET_TEMP, temp_object_name),
    )
    c.remove_object(settings.MINIO_BUCKET_TEMP, temp_object_name)
    return f"s3://{settings.MINIO_BUCKET_ASSETS}/{target_object_name}"


def get_object_bytes(bucket: str, object_name: str) -> bytes:
    resp = _client().get_object(bucket, object_name)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def presigned_get(bucket: str, object_name: str, expiry_seconds: int = 3600) -> str:
    from datetime import timedelta

    return _client().presigned_get_object(
        bucket, object_name, expires=timedelta(seconds=expiry_seconds)
    )
