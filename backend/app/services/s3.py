import boto3

from app.core.config import settings


def get_s3_client():
    if (
        not settings.aws_access_key_id
        or not settings.aws_secret_access_key
        or not settings.aws_default_region
    ):
        raise ValueError(
            "S3 settings are missing. Configure AWS_ACCESS_KEY_ID, "
            "AWS_SECRET_ACCESS_KEY and AWS_DEFAULT_REGION."
        )

    client_kwargs = {
        "service_name": "s3",
        "region_name": settings.aws_default_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
    }

    if settings.s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url

    return boto3.client(**client_kwargs)


def upload_bytes_to_s3(
    content: bytes,
    bucket_name: str,
    object_key: str,
    content_type: str | None = None,
) -> str:
    client = get_s3_client()

    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=content,
        **extra_args,
    )

    return f"s3://{bucket_name}/{object_key}"