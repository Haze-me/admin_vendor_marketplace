"""
S3 Presigned URL service.

Flow:
1. Vendor requests a presigned URL for a specific filename.
2. This service generates the URL using boto3.
3. Vendor uploads the file DIRECTLY to S3 from their browser/client.
4. Vendor sends the final S3 URL back to the products API to save it.

Why presigned URLs?
- Server never handles binary file data.
- Reduces server load and egress costs.
- Uploads go directly from client to S3.
- Each URL expires after AWS_PRESIGNED_URL_EXPIRY seconds (default 1 hour).
"""
import uuid
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _get_s3_client():
    """Create and return a boto3 S3 client."""
    return boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


class S3PresignedUrlService:

    @staticmethod
    def generate_presigned_upload_url(
        content_type: str,
        product_id: str,
        vendor_id: str,
    ) -> dict:
        """
        Generate a presigned PUT URL for uploading a product image to S3.

        Returns:
        {
            "upload_url": "https://bucket.s3.amazonaws.com/...",
            "image_url":  "https://bucket.s3.amazonaws.com/products/vendor-id/product-id/uuid.jpg",
            "expires_in": 3600,
            "fields": {}
        }

        The client must PUT the file to upload_url with the correct Content-Type header.
        After upload, the client saves image_url via POST /api/v1/products/<id>/images/.
        """
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(
                f"Unsupported file type '{content_type}'. "
                f"Allowed types: {', '.join(ALLOWED_IMAGE_TYPES.keys())}."
            )

        extension = ALLOWED_IMAGE_TYPES[content_type]
        # Organised S3 key: products/<vendor_id>/<product_id>/<uuid>.<ext>
        object_key = (
            f"products/{vendor_id}/{product_id}/{uuid.uuid4()}.{extension}"
        )
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        expiry = settings.AWS_PRESIGNED_URL_EXPIRY

        try:
            s3_client = _get_s3_client()
            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expiry,
            )

            # The public URL the image will be accessible at after upload
            image_url = (
                f"https://{bucket_name}.s3."
                f"{settings.AWS_S3_REGION_NAME}.amazonaws.com/{object_key}"
            )

            logger.info(
                "Presigned URL generated for product=%s vendor=%s key=%s",
                product_id, vendor_id, object_key,
            )

            return {
                "upload_url": presigned_url,
                "image_url": image_url,
                "object_key": object_key,
                "expires_in": expiry,
            }

        except NoCredentialsError:
            logger.error("AWS credentials not configured.")
            raise RuntimeError(
                "Image upload service is not configured. "
                "Contact support."
            )
        except ClientError as e:
            logger.error("S3 ClientError generating presigned URL: %s", e)
            raise RuntimeError(
                "Failed to generate upload URL. Please try again."
            )

    @staticmethod
    def delete_object(object_key: str) -> bool:
        """
        Delete an object from S3 by its key.
        Called when a product image is removed.
        Returns True on success, False on failure.
        """
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        try:
            s3_client = _get_s3_client()
            s3_client.delete_object(Bucket=bucket_name, Key=object_key)
            logger.info("S3 object deleted: %s", object_key)
            return True
        except ClientError as e:
            logger.error("Failed to delete S3 object %s: %s", object_key, e)
            return False