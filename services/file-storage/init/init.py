import boto3
from botocore.client import Config

def create_bucket(bucket_name):
    s3 = boto3.client('s3')
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f'Bucket {bucket_name} created.')
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f'Bucket {bucket_name} already exists.')