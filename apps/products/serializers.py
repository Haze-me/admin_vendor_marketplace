"""
Serializers for products app.
"""
from rest_framework import serializers
from apps.products.models import Product, ProductImage, ProductStatus
from apps.vendors.models import VendorStatus


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "is_primary", "display_order"]
        read_only_fields = ["id"]


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Vendor creates a new product.
    Vendor is set from the request — vendors cannot create
    products on behalf of other vendors.
    Status defaults to DRAFT.
    """
    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "name",
            "description",
            "brand",
            "sku",
            "price",
            "status",
        ]
        read_only_fields = ["id"]

    def validate_status(self, value):
        # Vendors can only create DRAFT or ACTIVE products
        allowed = [ProductStatus.DRAFT, ProductStatus.ACTIVE]
        if value not in allowed:
            raise serializers.ValidationError(
                "You can only set status to DRAFT or ACTIVE."
            )
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        vendor = getattr(user, "vendor_profile", None)
        if vendor is None:
            raise serializers.ValidationError(
                {"non_field_errors": "You do not have a vendor profile."}
            )
        if not vendor.is_approved:
            raise serializers.ValidationError(
                {"non_field_errors": "Your vendor account must be approved before listing products."}
            )
        return attrs

    def create(self, validated_data):
        vendor = self.context["request"].user.vendor_profile
        return Product.objects.create(vendor=vendor, **validated_data)


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Vendor updates their own product.
    Vendor and SKU cannot be changed after creation.
    """
    class Meta:
        model = Product
        fields = [
            "category",
            "name",
            "description",
            "brand",
            "price",
            "status",
        ]

    def validate_status(self, value):
        # Vendors cannot set SUSPENDED — only admins can
        if value == ProductStatus.SUSPENDED:
            raise serializers.ValidationError(
                "Products can only be suspended by an administrator."
            )
        return value


class ProductAdminUpdateSerializer(serializers.ModelSerializer):
    """Admin can update any field including status."""
    class Meta:
        model = Product
        fields = [
            "category",
            "name",
            "description",
            "brand",
            "price",
            "status",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product detail including images and vendor info."""
    images = ProductImageSerializer(source="product_images", many=True, read_only=True)
    vendor_name = serializers.CharField(source="vendor.business_name", read_only=True)
    vendor_id = serializers.UUIDField(source="vendor.id", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "vendor_id",
            "vendor_name",
            "category",
            "category_name",
            "name",
            "description",
            "brand",
            "sku",
            "price",
            "slug",
            "status",
            "primary_image_url",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_primary_image_url(self, obj):
        image = obj.primary_image
        return image.image_url if image else None


class ProductListSerializer(serializers.ModelSerializer):
    """Compact product for list views."""
    vendor_name = serializers.CharField(source="vendor.business_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "brand",
            "sku",
            "price",
            "slug",
            "status",
            "vendor_name",
            "category_name",
            "primary_image_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_primary_image_url(self, obj):
        image = obj.primary_image
        return image.image_url if image else None


class ProductImageAddSerializer(serializers.ModelSerializer):
    """Add an image URL to a product after S3 upload."""
    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "is_primary", "display_order"]
        read_only_fields = ["id"]