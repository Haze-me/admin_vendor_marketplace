"""
Serializers for categories app.
"""
from rest_framework import serializers
from apps.categories.models import Category


class CategoryCreateSerializer(serializers.ModelSerializer):
    """Admin creates a category."""
    class Meta:
        model = Category
        fields = ["id", "name", "description", "parent"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        qs = Category.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A category with this name already exists."
            )
        return value

    def validate_parent(self, value):
        if value is None:
            return value
        # Prevent nesting deeper than one level
        if value.parent is not None:
            raise serializers.ValidationError(
                "Cannot nest a category under a child category. "
                "Only one level of nesting is allowed."
            )
        return value


class CategoryUpdateSerializer(serializers.ModelSerializer):
    """Admin updates a category."""
    class Meta:
        model = Category
        fields = ["name", "description", "parent", "is_active"]

    def validate_name(self, value):
        qs = Category.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A category with this name already exists."
            )
        return value

    def validate_parent(self, value):
        if value is None:
            return value
        if value.parent is not None:
            raise serializers.ValidationError(
                "Cannot nest a category under a child category."
            )
        # Prevent a category from being its own parent
        if self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError(
                "A category cannot be its own parent."
            )
        return value


class ChildCategorySerializer(serializers.ModelSerializer):
    """Compact child category representation nested inside parent."""
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_active"]
        read_only_fields = fields


class CategoryDetailSerializer(serializers.ModelSerializer):
    """Full category detail including children."""
    children = ChildCategorySerializer(many=True, read_only=True)
    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "slug",
            "is_active",
            "parent",
            "parent_name",
            "children",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CategoryListSerializer(serializers.ModelSerializer):
    """Compact category for list views."""
    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_active", "parent", "parent_name"]
        read_only_fields = fields