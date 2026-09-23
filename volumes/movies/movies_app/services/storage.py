import logging
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

StorageError = (BotoCoreError, ClientError)


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def upload_file(path, key, content_type):
    _client().upload_file(
        str(path),
        settings.AWS_MOVIES_STORAGE_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def upload_bytes(data, key, content_type):
    _client().put_object(
        Bucket=settings.AWS_MOVIES_STORAGE_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def open_range(key, start, end):
    """Return a streaming body over the inclusive byte range [start, end]."""
    response = _client().get_object(
        Bucket=settings.AWS_MOVIES_STORAGE_BUCKET_NAME,
        Key=key,
        Range=f"bytes={start}-{end}",
    )
    return response["Body"]


def read(key):
    response = _client().get_object(Bucket=settings.AWS_MOVIES_STORAGE_BUCKET_NAME, Key=key)
    return response["Body"].read()


def delete(key):
    """Best effort: a leftover object is harmless, a failed cleanup must not break the caller."""
    if not key:
        return
    try:
        _client().delete_object(Bucket=settings.AWS_MOVIES_STORAGE_BUCKET_NAME, Key=key)
    except StorageError as error:
        logger.warning("could not delete %s from storage: %s", key, error)
