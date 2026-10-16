from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .access import asset_in_scope, can, department_model, gso_department_for_user
from .models import Asset, AssetAuditEvent


SNAPSHOT_FIELDS = (
    "asset_name", "category", "property_tag", "brand", "model_number", "serial_number", "obr_reference",
    "purchase_date", "supplier", "unit_cost", "quantity", "assigned_office", "status",
    "assigned_department_id", "assigned_department_label", "returned_date", "notes",
)


def asset_snapshot(asset):
    result = {}
    for name in SNAPSHOT_FIELDS:
        value = getattr(asset, name)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        result[name] = value
    return result


def _require(user, permission, asset=None):
    if not can(user, permission):
        raise PermissionDenied
    if asset is not None and not asset_in_scope(user, asset):
        raise PermissionDenied


@transaction.atomic
def create_asset(*, actor, data):
    _require(actor, "add")
    department = gso_department_for_user(actor)
    if department is None:
        raise PermissionDenied
    data = dict(data)
    assigned_department_pk = data.pop("assigned_department", None)
    assigned_department = _resolve_assigned_department(assigned_department_pk)
    asset = Asset.objects.create(
        **data,
        assigned_department_id=assigned_department.pk if assigned_department else None,
        assigned_department_label=assigned_department.name if assigned_department else "",
        department_id=department.pk,
        department_label=department.name, created_by=actor, updated_by=actor,
    )
    AssetAuditEvent.objects.create(
        asset=asset, department_id=asset.department_id, actor=actor,
        action=AssetAuditEvent.CREATED, snapshot=asset_snapshot(asset),
    )
    return asset


@transaction.atomic
def update_asset(*, actor, asset, data):
    _require(actor, "change", asset)
    if asset.status == Asset.RETIRED:
        raise PermissionDenied("Retired asset records are read-only.")
    data = dict(data)
    assigned_department_pk = data.pop("assigned_department", None)
    assigned_department = _resolve_assigned_department(assigned_department_pk)
    for field, value in data.items():
        setattr(asset, field, value)
    asset.assigned_department_id = assigned_department.pk if assigned_department else None
    asset.assigned_department_label = assigned_department.name if assigned_department else ""
    asset.updated_by = actor
    asset.save()
    AssetAuditEvent.objects.create(
        asset=asset, department_id=asset.department_id, actor=actor,
        action=AssetAuditEvent.UPDATED, snapshot=asset_snapshot(asset),
    )
    return asset


@transaction.atomic
def retire_asset(*, actor, asset):
    _require(actor, "delete", asset)
    if asset.status == Asset.RETIRED:
        raise PermissionDenied("This asset has already been retired.")
    asset.status = Asset.RETIRED
    asset.returned_date = asset.returned_date or timezone.localdate()
    asset.updated_by = actor
    asset.save(update_fields=("status", "returned_date", "updated_by", "updated_at"))
    AssetAuditEvent.objects.create(
        asset=asset, department_id=asset.department_id, actor=actor,
        action=AssetAuditEvent.RETIRED, snapshot=asset_snapshot(asset),
    )
    return asset


def _resolve_assigned_department(pk):
    if not pk:
        return None
    model = department_model()
    department = model.objects.filter(pk=pk).first() if model else None
    if department is None:
        raise PermissionDenied("The selected department is no longer available.")
    return department
