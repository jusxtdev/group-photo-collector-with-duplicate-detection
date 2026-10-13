from src.core.config import settings

import boto3

s3 = boto3.client(
    "s3",
    endpoint_url=settings.aws_endpoint_url_s3,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)

def test_connectivity():
    # Check if the S3 bucket exists
    try:
        s3.head_bucket(Bucket=settings.s3_bucket_name)
        print("Successfully connected to S3 bucket.")
    except Exception as e:
        raise AssertionError(f"Failed to connect to S3 bucket: {e}")
    
def test_upload():
    bucket = settings.s3_bucket_name
    key = "test_upload.txt"
    # Upload
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=b"Hello from FastAPI!",
        ContentType="text/plain",
    )

    # Read back
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read()
    assert content == b"Hello from FastAPI!"

    print("Upload and download successful!")

    # Delete
    s3.delete_object(Bucket=bucket, Key=key)
    print("Delete successful!")
    
if __name__ == "__main__":
    test_connectivity()
    test_upload()
    