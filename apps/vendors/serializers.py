"""
Serializers for vendors app.

Covers:
- Vendor profile creation (by vendor after registration)
- Vendor profile update (by vendor)
- Vendor detail (read)
- Vendor list (read, admin)
- Admin status change (approve / suspend)
"""
from rest_framework import serializers
from apps.vendors.models import Vendor, VendorStatus


class VendorCreateSerializer(serializers.ModelSerializer):
    """
    Vendor creates their own profile after registering an account.
    Status defaults to PENDING — admin must approve before they can list products.
    """
    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "business_email",
            "phone",
            "address",
            "description",
        ]
        read_only_fields = ["id"]

    def validate_business_email(self, value):
        if Vendor.objects.filter(business_email__iexact=value).exists():
            raise serializers.ValidationError(
                "A vendor with this business email already exists."
            )
        return value.lower()

    def validate(self, attrs):
        user = self.context["request"].user
        if Vendor.objects.filter(user=user).exists():
            raise serializers.ValidationError(
                {"non_field_errors": "You already have a vendor profile."}
            )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return Vendor.objects.create(user=user, **validated_data)


class VendorUpdateSerializer(serializers.ModelSerializer):
    """Vendor updates their own profile. Status and slug are not editable by vendor."""
    class Meta:
        model = Vendor
        fields = [
            "business_name",
            "business_email",
            "phone",
            "address",
            "description",
        ]

    def validate_business_email(self, value):
        qs = Vendor.objects.filter(business_email__iexact=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A vendor with this business email already exists."
            )
        return value.lower()


class VendorDetailSerializer(serializers.ModelSerializer):
    """Full vendor detail — returned to admins and the vendor themselves."""
    owner_email = serializers.EmailField(source="user.email", read_only=True)
    owner_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "business_email",
            "phone",
            "address",
            "description",
            "slug",
            "status",
            "owner_email",
            "owner_name",
            "approved_at",
            "suspended_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class VendorListSerializer(serializers.ModelSerializer):
    """Compact vendor representation for list views."""
    owner_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "business_email",
            "slug",
            "status",
            "owner_email",
            "created_at",
        ]
        read_only_fields = fields


class VendorStatusSerializer(serializers.Serializer):
    """
    Admin changes vendor status.
    Allowed transitions:
      PENDING   -> APPROVED
      PENDING   -> SUSPENDED
      APPROVED  -> SUSPENDED
      SUSPENDED -> APPROVED
    """
    status = serializers.ChoiceField(choices=[
        VendorStatus.APPROVED,
        VendorStatus.SUSPENDED,
    ])
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional reason for status change (stored in audit log).",
    )

    def validate_status(self, value):
        current = self.instance.status
        # APPROVED -> APPROVED or SUSPENDED -> SUSPENDED are no-ops, reject them
        if value == current:
            raise serializers.ValidationError(
                f"Vendor is already {current}."
            )
        return value