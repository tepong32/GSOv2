from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .access import (
    _is_gso_department, asset_access_required, can, can_view_audit,
    department_for_user, gso_department_for_user,
)
from .forms import AssetForm
from .models import Asset
from .services import create_asset, retire_asset, update_asset


def _scoped_assets(user):
    if user.is_superuser:
        return Asset.objects.all()
    department = department_for_user(user)
    if not department:
        raise PermissionDenied
    if _is_gso_department(department):
        return Asset.objects.filter(department_id=department.pk)
    return Asset.objects.filter(assigned_department_id=department.pk)


@asset_access_required("view")
def dashboard(request):
    assets = _scoped_assets(request.user)
    return render(request, "inventory/dashboard.html", {
        "department": department_for_user(request.user) or gso_department_for_user(request.user),
        "is_gso": request.user.is_superuser or _is_gso_department(department_for_user(request.user)),
        "total_assets": assets.count(),
        "in_service_count": assets.filter(status=Asset.ACTIVE).count(),
        "maintenance_count": assets.filter(status=Asset.MAINTENANCE).count(),
        "retired_count": assets.filter(status=Asset.RETIRED).count(),
        "can_add": can(request.user, "add"),
    })


@asset_access_required("view")
def asset_list(request):
    assets = _scoped_assets(request.user)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        assets = assets.filter(
            Q(asset_name__icontains=query) | Q(category__icontains=query)
            | Q(property_tag__icontains=query)
            | Q(brand__icontains=query) | Q(serial_number__icontains=query)
            | Q(obr_reference__icontains=query) | Q(assigned_office__icontains=query)
        )
    if status in dict(Asset.STATUS_CHOICES):
        assets = assets.filter(status=status)
    page = Paginator(assets, 25).get_page(request.GET.get("page"))
    return render(request, "inventory/asset_list.html", {
        "page": page, "query": query, "selected_status": status,
        "statuses": Asset.STATUS_CHOICES,
        "can_add": can(request.user, "add"),
        "can_change": can(request.user, "change"),
        "can_retire": can(request.user, "delete"),
    })


@asset_access_required("view")
def asset_detail(request, pk):
    asset = get_object_or_404(_scoped_assets(request.user), pk=pk)
    return render(request, "inventory/asset_detail.html", {
        "asset": asset,
        "events": asset.audit_events.all() if can_view_audit(request.user) else (),
        "can_change": can(request.user, "change"),
        "can_retire": can(request.user, "delete"),
        "can_view_audit": can_view_audit(request.user),
    })


@asset_access_required("add")
def asset_create(request):
    form = AssetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        asset = create_asset(actor=request.user, data=form.cleaned_data)
        messages.success(request, "Asset added to the register.")
        return redirect("inventory:asset-detail", pk=asset.pk)
    return render(request, "inventory/asset_form.html", {"form": form, "heading": "Add an asset"})


@asset_access_required("change")
def asset_edit(request, pk):
    asset = get_object_or_404(_scoped_assets(request.user), pk=pk)
    if asset.status == Asset.RETIRED:
        raise PermissionDenied("Retired asset records are read-only.")
    form = AssetForm(request.POST or None, instance=asset)
    if request.method == "POST" and form.is_valid():
        asset = update_asset(actor=request.user, asset=asset, data=form.cleaned_data)
        messages.success(request, "Asset record updated.")
        return redirect("inventory:asset-detail", pk=asset.pk)
    return render(request, "inventory/asset_form.html", {"form": form, "asset": asset, "heading": "Edit asset"})


@asset_access_required("delete")
@require_POST
def asset_retire(request, pk):
    asset = get_object_or_404(_scoped_assets(request.user), pk=pk)
    retire_asset(actor=request.user, asset=asset)
    messages.success(request, "Asset retired. The record and its history were retained.")
    return redirect("inventory:asset-detail", pk=asset.pk)
