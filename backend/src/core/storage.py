from functools import lru_cache

import boto3
from botocore.client import BaseClient, Config

from src.core.config import settings


@lru_cache
def get_s3_client() -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=settings.aws_endpoint_url_s3,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> None:
    extra = {"ContentType": content_type} if content_type else {}
    get_s3_client().put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=data,
        **extra,
    )


def delete_object(key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.s3_bucket_name, Key=key)


PRESIGN_EXPIRE_SECONDS = 3600


def generate_presigned_url(
    key: str, expires_in: int = PRESIGN_EXPIRE_SECONDS
) -> str:
    return get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )
