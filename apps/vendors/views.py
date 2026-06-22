"""
Vendor views.

Endpoints:
  POST   /api/v1/vendors/profile/              -> vendor creates their profile
  GET    /api/v1/vendors/profile/              -> vendor views their own profile
  PUT    /api/v1/vendors/profile/              -> vendor updates their own profile
  GET    /api/v1/vendors/                      -> admin lists all vendors
  GET    /api/v1/vendors/<id>/                 -> admin views a vendor
  PATCH  /api/v1/vendors/<id>/status/          -> admin approves or suspends vendor
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.vendors.models import Vendor, VendorStatus
from apps.vendors.serializers import (
    VendorCreateSerializer,
    VendorUpdateSerializer,
    VendorDetailSerializer,
    VendorListSerializer,
    VendorStatusSerializer,
)
from apps.vendors.services import VendorService
from apps.accounts.permissions import IsAdminUser, IsVendorUser
from common.responses import success_response, created_response, no_content_response
from common.pagination import StandardResultsPagination
from apps.audit.services import AuditService

logger = logging.getLogger(__name__)


class VendorProfileView(APIView):
    """
    Vendor manages their own profile.
    GET  -> view own profile
    POST -> create profile (only once)
    PUT  -> update profile
    """
    permission_classes = [IsVendorUser]

    def get(self, request):
        vendor = VendorService.get_vendor_by_user(request.user)
        serializer = VendorDetailSerializer(vendor)
        return success_response(data=serializer.data, request=request)

    def post(self, request):
        serializer = VendorCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        vendor = serializer.save()
        return created_response(
            data=VendorDetailSerializer(vendor).data,
            message="Vendor profile created. Awaiting admin approval.",
            request=request,
        )

    def put(self, request):
        vendor = VendorService.get_vendor_by_user(request.user)
        serializer = VendorUpdateSerializer(vendor, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=VendorDetailSerializer(vendor).data,
            message="Vendor profile updated.",
            request=request,
        )


class AdminVendorListView(APIView):
    """Admin lists all vendors with filtering and search."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = Vendor.objects.select_related("user").order_by("-created_at")

        # Filter by status
        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status.upper())

        # Search by business name or email
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                business_name__icontains=search
            ) | queryset.filter(
                business_email__icontains=search
            )

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = VendorListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminVendorDetailView(APIView):
    """Admin views a single vendor's full profile."""
    permission_classes = [IsAdminUser]

    def get(self, request, vendor_id):
        vendor = VendorService.get_vendor_or_404(vendor_id)
        serializer = VendorDetailSerializer(vendor)
        return success_response(data=serializer.data, request=request)


class AdminVendorStatusView(APIView):
    """
    Admin approves or suspends a vendor.
    PATCH /api/v1/vendors/<id>/status/
    Body: { "status": "APPROVED" | "SUSPENDED", "reason": "optional" }
    """
    permission_classes = [IsAdminUser]

    def patch(self, request, vendor_id):
        vendor = VendorService.get_vendor_or_404(vendor_id)
        serializer = VendorStatusSerializer(vendor, data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        reason = serializer.validated_data.get("reason", "")

        if new_status == VendorStatus.APPROVED:
            vendor = VendorService.approve_vendor(vendor)
            message = "Vendor approved successfully."
        else:
            vendor = VendorService.suspend_vendor(vendor, reason=reason)
            message = "Vendor suspended successfully."

        AuditService.log_vendor_status_change(
            request=request,
            vendor=vendor,
            new_status=new_status,
            reason=reason,
        )

        return success_response(
            data=VendorDetailSerializer(vendor).data,
            message=message,
            request=request,
        )