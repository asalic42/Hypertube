import boto3
from botocore.client import Config
import os


def create_bucket(bucket_name):
    s3 = boto3.client(
        's3',
        endpoint_url='http://file-storage:9000',
        aws_access_key_id=os.environ["RUSTFS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["RUSTFS_SECRET_KEY"],
        region_name='eu-west-1',
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'},
        ),
    )
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f'Bucket {bucket_name} created.')
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f'Bucket {bucket_name} already exists.')


create_bucket('profil-pics')
create_bucket('movies')