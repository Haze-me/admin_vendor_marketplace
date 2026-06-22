"""
Serializers for images app.
"""
from rest_framework import serializers


ALLOWED_CONTENT_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
]


class PresignedUrlRequestSerializer(serializers.Serializer):
    """
    Request body for generating a presigned upload URL.

    The vendor provides:
    - content_type: MIME type of the image they want to upload.
    - product_id:   The product this image belongs to.
    """
    content_type = serializers.ChoiceField(
        choices=ALLOWED_CONTENT_TYPES,
        help_text="MIME type of the image file (e.g. image/jpeg).",
    )
    product_id = serializers.UUIDField(
        help_text="UUID of the product this image will belong to.",
    )


class PresignedUrlResponseSerializer(serializers.Serializer):
    """
    Response shape returned to the client after generating a presigned URL.

    The client flow:
    1. Receive upload_url and image_url from this response.
    2. PUT the image binary to upload_url with Content-Type header.
    3. After successful upload, POST image_url to /api/v1/products/<id>/images/.
    """
    upload_url = serializers.URLField(
        help_text="Presigned S3 URL to PUT the image to. Expires soon.",
    )
    image_url = serializers.URLField(
        help_text="Public S3 URL where the image will be accessible after upload.",
    )
    object_key = serializers.CharField(
        help_text="S3 object key — store this if you need to delete the image later.",
    )
    expires_in = serializers.IntegerField(
        help_text="Seconds until the upload_url expires.",
    )