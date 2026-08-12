import logging
import uuid
import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.files.storage import default_storage
from users_app.models import PublicUser
from django.shortcuts import get_object_or_404


logger = logging.getLogger(__name__)


class PresignedUrlError(Exception):
    pass


def get_boto3_client():
    s3_public = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_PUBLIC_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )
    return s3_public


def get_presigned_url(bucket_name, object_key, expiration=3600):
    """
    Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_key: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    try:
        s3_client = get_boto3_client()
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expiration,
        )
    except (ClientError, BotoCoreError) as e:
        raise PresignedUrlError("Error generating presigned URL.") from e
    return response


def create_avatar_key(instance, filename):
    """ creates a key string for the profile avatar"""
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'png'
    return f"avatars/{uuid.uuid4().hex}-avatar.{extension}"


def get_bucket_file_key(username):
    """ returns the s3 bucket file key for a given username """
    user = get_object_or_404(PublicUser, username=username)
    return user.avatar


def save_avatar(user, file):
    """ saves the profile avatar to the storage and updates the user model 
        :param user: PublicUser instance
        :param file: file object to be saved
        :return: the storage key of the saved file
    """
    key = create_avatar_key(user, file.name)
    default_storage.save(key, file)
    try:
        user.avatar = key
        raise Exception("Simulated error")  # Simulate an error for testing purposes
        user.save(update_fields=["avatar"])
    except Exception:
        default_storage.delete(key)
        raise Exception("Failed to save avatar and update user model.")
    return key


def delete_avatar(user):
    """ deletes the profile avatar from the storage and updates the user model 
        :param user: PublicUser instance
        :return: None
    """
    if user.avatar:
        default_storage.delete(user.avatar)
        user.avatar = ""
        user.save(update_fields=["avatar"])
