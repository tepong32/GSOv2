from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .access import asset_in_scope, can, department_model, gso_department_for_user
from .models import (
    Asset, AssetAuditEvent, ConsumableAuditEvent, ConsumableItem, StockLot, StockLotAllocation, StockMovement,
)


SNAPSHOT_FIELDS = (
    "asset_kind", "asset_name", "category", "property_tag", "brand", "model_number", "serial_number",
    "plate_number", "engine_number", "chassis_number", "registration_due", "obr_reference",
    "purchase_order_reference", "voucher_reference", "journal_reference", "fund_code",
    "coa_account_code", "coa_account_title", "coa_basis", "purchase_date", "supplier", "unit_cost",
    "quantity", "assigned_office", "status",
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


def _stock_permission(actor, action):
    from .access import can_stock

    if not can_stock(actor, action):
        raise PermissionDenied


@transaction.atomic
def create_consumable(*, actor, data):
    _stock_permission(actor, "add")
    department = gso_department_for_user(actor)
    if department is None:
        raise PermissionDenied
    item = ConsumableItem.objects.create(
        **data, department_id=department.pk, department_label=department.name, created_by=actor,
    )
    ConsumableAuditEvent.objects.create(
        item=item, actor=actor, action=ConsumableAuditEvent.CREATED, snapshot=consumable_snapshot(item),
    )
    return item


def consumable_snapshot(item):
    return {
        "name": item.name, "category": item.category, "unit": item.unit,
        "use_fifo": item.use_fifo, "minimum_stock": str(item.minimum_stock),
        "is_active": item.is_active, "notes": item.notes,
        "department_id": item.department_id, "department_label": item.department_label,
    }


@transaction.atomic
def update_consumable(*, actor, item, data):
    _stock_permission(actor, "change")
    item = ConsumableItem.objects.select_for_update().get(pk=item.pk)
    if item.use_fifo != data.get("use_fifo") and item.movements.exists():
        raise ValidationError("FIFO tracking cannot be changed after stock movements exist.")
    for field, value in data.items():
        setattr(item, field, value)
    item.updated_by = actor
    item.save()
    ConsumableAuditEvent.objects.create(
        item=item, actor=actor, action=ConsumableAuditEvent.UPDATED, snapshot=consumable_snapshot(item),
    )
    return item


def _stock_signed_total(item):
    return item.movements.aggregate(total=Sum("signed_quantity"))["total"] or Decimal("0")


def _create_stock_lot(item, movement):
    return StockLot.objects.create(
        item=item, receipt=movement, received_at=movement.occurred_at,
        quantity=movement.quantity, unit_cost=movement.unit_cost,
    )


def _allocate_fifo(item, issue, quantity):
    remaining = quantity
    for lot in item.lots.select_for_update().order_by("received_at", "pk"):
        allocated = lot.allocations.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        available = lot.quantity - allocated
        if available <= 0:
            continue
        take = min(available, remaining)
        StockLotAllocation.objects.create(issue=issue, lot=lot, quantity=take)
        remaining -= take
        if remaining <= 0:
            break
    if remaining > 0:
        raise ValidationError("FIFO lot balances do not cover the requested quantity. Review stock history first.")


@transaction.atomic
def record_stock_movement(*, actor, item, kind, quantity, reference="", reason="", unit_cost=None,
                          department_id=None, department_label="", recipient=""):
    permission = {
        StockMovement.RECEIPT: "receive",
        StockMovement.ISSUE: "issue",
        StockMovement.ADJUSTMENT_IN: "adjust",
        StockMovement.ADJUSTMENT_OUT: "adjust",
        StockMovement.RETURN: "receive",
    }.get(kind)
    if permission is None:
        raise ValidationError("Unknown stock movement type.")
    _stock_permission(actor, permission)
    item = ConsumableItem.objects.select_for_update().get(pk=item.pk)
    if not item.is_active:
        raise ValidationError("Inactive supply items cannot receive new movements.")
    quantity = Decimal(quantity)
    if quantity <= 0:
        raise ValidationError("Enter a quantity greater than zero.")
    inbound = kind in (StockMovement.RECEIPT, StockMovement.RETURN, StockMovement.ADJUSTMENT_IN)
    if not inbound and _stock_signed_total(item) < quantity:
        raise ValidationError(f"Only {_stock_signed_total(item):g} {item.unit} are available.")
    signed = quantity if inbound else -quantity
    movement = StockMovement.objects.create(
        item=item, kind=kind, quantity=quantity, signed_quantity=signed,
        department_id=department_id, department_label=department_label,
        recipient=recipient, reference=reference, reason=reason, unit_cost=unit_cost, actor=actor,
    )
    if item.use_fifo:
        if inbound:
            _create_stock_lot(item, movement)
        else:
            _allocate_fifo(item, movement, quantity)
    return movement
