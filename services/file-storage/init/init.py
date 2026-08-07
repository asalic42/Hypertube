import boto3
from botocore.client import Config
import os


def create_bucket(bucket_name):
    s3 = boto3.client(
        's3',
        endpoint_url=os.environ["AWS_S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name='eu-west-1',
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'},
        ),
    )
    try:
        buckets = s3.list_buckets()
        if any(bucket['Name'] == bucket_name for bucket in buckets['Buckets']):
            print(f'🟰  Bucket {bucket_name} already exists.')
            return
        s3.create_bucket(Bucket=bucket_name)
        print(f'✅ Bucket {bucket_name} created.')
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        print(f"Error creating bucket {bucket_name}: {error_code}")

        if error_code in [
            "BucketAlreadyExists",
            "BucketAlreadyOwnedByYou"
        ]:
            print(f"🟰  Bucket {bucket_name} already exists.")
        else:
            raise


if __name__ == "__main__":
    try:
        with open("/init/buckets.txt", "r") as f:
            buckets = [line.strip() for line in f.readlines() if line.strip()]
        for bucket in buckets:
            create_bucket(bucket)
    except FileNotFoundError:
        print("⚠️  buckets.txt file not found. No buckets to create. ⚠️")