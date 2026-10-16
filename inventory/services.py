from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .access import (
    asset_in_scope, can, can_acknowledge_asset_transfer, can_request_asset_disposal,
    can_review_asset_disposal, can_transfer_asset, can_manage_asset_verification,
    department_model, department_for_user, gso_department_for_user,
)
from .models import (
    Asset, AssetAuditEvent, AssetDisposalAttachment, AssetDisposalCase,
    AssetDisposalEvent, AssetTransfer, AssetVerificationEvent, AssetVerificationRecord,
    AssetVerificationRound, ConsumableAuditEvent, ConsumableItem,
    StockLot, StockLotAllocation, StockMovement,
)


SNAPSHOT_FIELDS = (
    "asset_kind", "inventory_class", "item_type", "asset_name", "category", "property_tag", "brand", "model_number", "serial_number",
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
    if asset.transfers.filter(status=AssetTransfer.PENDING).exists():
        raise PermissionDenied("This asset has a handoff waiting for acknowledgment.")
    if asset.disposal_cases.filter(status__in=(
        AssetDisposalCase.SUBMITTED, AssetDisposalCase.UNDER_REVIEW,
        AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.AUTHORIZED,
    )).exists():
        raise PermissionDenied("This asset has an open disposal case and cannot be edited.")
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
    raise PermissionDenied("Use the documented disposal case workflow to retire an asset.")


def _resolve_assigned_department(pk):
    if not pk:
        return None
    model = department_model()
    department = model.objects.filter(pk=pk).first() if model else None
    if department is None:
        raise PermissionDenied("The selected department is no longer available.")
    return department


@transaction.atomic
def create_asset_transfer(*, actor, asset, data):
    if not can_transfer_asset(actor) or not asset_in_scope(actor, asset):
        raise PermissionDenied
    asset = Asset.objects.select_for_update().get(pk=asset.pk)
    if asset.status == Asset.RETIRED:
        raise ValidationError("Retired assets cannot be handed off.")
    if asset.transfers.filter(status=AssetTransfer.PENDING).exists():
        raise ValidationError("This asset already has a handoff waiting for acknowledgment.")
    if asset.disposal_cases.filter(status__in=(
        AssetDisposalCase.SUBMITTED, AssetDisposalCase.UNDER_REVIEW,
        AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.AUTHORIZED,
    )).exists():
        raise ValidationError("This asset has an open disposal case and cannot be transferred.")
    destination = _resolve_assigned_department(data["destination_department"])
    if destination.pk == asset.assigned_department_id and data["destination_custodian"].strip() == asset.assigned_office.strip():
        raise ValidationError("Choose a different department or custodian.")
    return AssetTransfer.objects.create(
        asset=asset,
        source_department_id=asset.assigned_department_id,
        source_department_label=asset.assigned_department_label,
        source_custodian=asset.assigned_office,
        destination_department_id=destination.pk,
        destination_department_label=destination.name,
        destination_custodian=data["destination_custodian"].strip(),
        transfer_date=data["transfer_date"], reason=data["reason"].strip(),
        reference=data.get("reference", "").strip(), requested_by=actor,
    )


@transaction.atomic
def acknowledge_asset_transfer(*, actor, transfer):
    transfer = AssetTransfer.objects.select_for_update().select_related("asset").get(pk=transfer.pk)
    if not can_acknowledge_asset_transfer(actor, transfer):
        raise PermissionDenied
    if transfer.status != AssetTransfer.PENDING:
        raise ValidationError("This handoff has already been processed.")
    asset = Asset.objects.select_for_update().get(pk=transfer.asset_id)
    if (asset.assigned_department_id != transfer.source_department_id
            or asset.assigned_office != transfer.source_custodian):
        raise ValidationError("The asset assignment changed after this handoff was started. Ask GSO to review it.")
    asset.assigned_department_id = transfer.destination_department_id
    asset.assigned_department_label = transfer.destination_department_label
    asset.assigned_office = transfer.destination_custodian
    asset.updated_by = actor
    asset.save(update_fields=(
        "assigned_department_id", "assigned_department_label", "assigned_office", "updated_by", "updated_at",
    ))
    transfer.status = AssetTransfer.ACCEPTED
    transfer.acknowledged_by = actor
    transfer.acknowledged_at = timezone.now()
    transfer.save(update_fields=("status", "acknowledged_by", "acknowledged_at"))
    AssetAuditEvent.objects.create(
        asset=asset, department_id=asset.department_id, actor=actor,
        action=AssetAuditEvent.TRANSFERRED, snapshot=asset_snapshot(asset),
    )
    return transfer


@transaction.atomic
def cancel_asset_transfer(*, actor, transfer, reason):
    transfer = AssetTransfer.objects.select_for_update().select_related("asset").get(pk=transfer.pk)
    if not can_transfer_asset(actor) or not asset_in_scope(actor, transfer.asset):
        raise PermissionDenied
    if transfer.status != AssetTransfer.PENDING:
        raise ValidationError("Only a pending handoff can be cancelled.")
    transfer.status = AssetTransfer.CANCELLED
    transfer.cancelled_by = actor
    transfer.cancelled_at = timezone.now()
    transfer.cancellation_reason = reason.strip()
    transfer.save(update_fields=("status", "cancelled_by", "cancelled_at", "cancellation_reason"))
    return transfer


@transaction.atomic
def start_asset_verification_round(*, actor, title):
    if not can_manage_asset_verification(actor, "start"):
        raise PermissionDenied
    department = gso_department_for_user(actor)
    if department is None:
        raise PermissionDenied
    title = title.strip()
    if not title:
        raise ValidationError("Enter a name for this verification round.")
    verification_round = AssetVerificationRound.objects.create(
        title=title, department_id=department.pk, department_label=department.name, created_by=actor,
    )
    assets = Asset.objects.filter(department_id=department.pk).exclude(status=Asset.RETIRED).order_by("pk")
    AssetVerificationRecord.objects.bulk_create([
        AssetVerificationRecord(
            verification_round=verification_round, asset=asset,
            asset_name_snapshot=asset.asset_name, property_tag_snapshot=asset.property_tag,
            serial_number_snapshot=asset.serial_number,
            assigned_department_snapshot=asset.assigned_department_label,
            assigned_office_snapshot=asset.assigned_office,
        )
        for asset in assets
    ])
    return verification_round


@transaction.atomic
def record_asset_verification(*, actor, record, data):
    if not can_manage_asset_verification(actor, "record"):
        raise PermissionDenied
    record = AssetVerificationRecord.objects.select_for_update().select_related("verification_round").get(pk=record.pk)
    verification_round = AssetVerificationRound.objects.select_for_update().get(pk=record.verification_round_id)
    if verification_round.closed_at:
        raise ValidationError("This verification round is closed.")
    if not actor.is_superuser:
        department = gso_department_for_user(actor)
        if not department or verification_round.department_id != department.pk:
            raise PermissionDenied
    if data.get("result") not in {AssetVerificationRecord.MATCHED, AssetVerificationRecord.DISCREPANCY, AssetVerificationRecord.NOT_FOUND}:
        raise ValidationError("Choose a physical verification result.")
    if data["result"] in (AssetVerificationRecord.DISCREPANCY, AssetVerificationRecord.NOT_FOUND) and not data.get("notes", "").strip():
        raise ValidationError("Add a brief note for a discrepancy or missing asset.")
    record.result = data["result"]
    record.observed_department = data.get("observed_department", "").strip()
    record.observed_office = data.get("observed_office", "").strip()
    record.condition = data.get("condition", "")
    record.notes = data.get("notes", "").strip()
    record.verified_by = actor
    record.verified_at = timezone.now()
    record.save(update_fields=("result", "observed_department", "observed_office", "condition", "notes", "verified_by", "verified_at"))
    AssetVerificationEvent.objects.create(
        record=record, actor=actor,
        snapshot={
            "asset_name": record.asset_name_snapshot,
            "property_tag": record.property_tag_snapshot,
            "serial_number": record.serial_number_snapshot,
            "recorded_department": record.assigned_department_snapshot,
            "recorded_office": record.assigned_office_snapshot,
            "result": record.result,
            "observed_department": record.observed_department,
            "observed_office": record.observed_office,
            "condition": record.condition,
            "notes": record.notes,
        },
    )
    return record


@transaction.atomic
def close_asset_verification_round(*, actor, verification_round):
    if not can_manage_asset_verification(actor, "close"):
        raise PermissionDenied
    verification_round = AssetVerificationRound.objects.select_for_update().get(pk=verification_round.pk)
    if not actor.is_superuser:
        department = gso_department_for_user(actor)
        if not department or verification_round.department_id != department.pk:
            raise PermissionDenied
    if verification_round.closed_at:
        raise ValidationError("This verification round is already closed.")
    if verification_round.records.filter(result=AssetVerificationRecord.NOT_CHECKED).exists():
        raise ValidationError("Record a result for every listed asset before closing this round.")
    verification_round.closed_by = actor
    verification_round.closed_at = timezone.now()
    verification_round.save(update_fields=("closed_by", "closed_at"))
    return verification_round


def _disposal_snapshot(case, note=""):
    return {
        "asset_id": case.asset_id,
        "asset_tag": case.asset.property_tag,
        "asset_name": case.asset.asset_name,
        "status": case.status,
        "reason": case.reason,
        "condition_details": case.condition_details,
        "review_note": case.review_note,
        "authority_reference": case.authority_reference,
        "disposal_method": case.disposal_method,
        "disposal_date": case.disposal_date.isoformat() if case.disposal_date else None,
        "completion_reference": case.completion_reference,
        "note": note,
        "attachments": list(case.attachments.values_list("original_filename", flat=True)),
    }


def _record_disposal_event(case, actor, action, note=""):
    AssetDisposalEvent.objects.create(
        disposal_case=case, actor=actor, action=action,
        snapshot=_disposal_snapshot(case, note),
    )


def _save_disposal_attachments(*, case, actor, uploads, kind):
    attachments = []
    mime_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".pdf": "application/pdf",
    }
    for upload in uploads:
        extension = "." + upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
        attachment = AssetDisposalAttachment(
            disposal_case=case, kind=kind, original_filename=upload.name[:255],
            content_type=mime_types.get(extension, "application/octet-stream"),
            size=upload.size, uploaded_by=actor,
        )
        attachment.file.save(upload.name, upload, save=False)
        attachment.save()
        attachments.append(attachment)
    return attachments


@transaction.atomic
def submit_asset_disposal_request(*, actor, asset, data):
    if not can_request_asset_disposal(actor, asset):
        raise PermissionDenied
    if not data.get("photos") or not data.get("signed_request"):
        raise ValidationError("Attach at least one condition photo and the signed request form.")
    asset = Asset.objects.select_for_update().get(pk=asset.pk)
    if asset.status == Asset.RETIRED:
        raise ValidationError("This asset is already retired.")
    if asset.transfers.filter(status=AssetTransfer.PENDING).exists():
        raise ValidationError("Finish or cancel the pending handoff before requesting disposal review.")
    open_statuses = (
        AssetDisposalCase.SUBMITTED, AssetDisposalCase.UNDER_REVIEW,
        AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.AUTHORIZED,
    )
    if asset.disposal_cases.filter(status__in=open_statuses).exists():
        raise ValidationError("This asset already has an open disposal request.")
    case = AssetDisposalCase.objects.create(
        asset=asset, reason=data["reason"].strip(),
        condition_details=data["condition_details"].strip(), submitted_by=actor,
    )
    _save_disposal_attachments(case=case, actor=actor, uploads=data["photos"], kind=AssetDisposalAttachment.PHOTO)
    _save_disposal_attachments(case=case, actor=actor, uploads=[data["signed_request"]], kind=AssetDisposalAttachment.REQUEST_FORM)
    _save_disposal_attachments(case=case, actor=actor, uploads=data.get("supporting_documents", []), kind=AssetDisposalAttachment.SUPPORTING)
    _record_disposal_event(case, actor, "submitted")
    return case


@transaction.atomic
def review_asset_disposal_case(*, actor, case, data):
    if not can_review_asset_disposal(actor) or not asset_in_scope(actor, case.asset):
        raise PermissionDenied
    case = AssetDisposalCase.objects.select_for_update().select_related("asset").get(pk=case.pk)
    allowed = {
        AssetDisposalCase.SUBMITTED: {AssetDisposalCase.UNDER_REVIEW, AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.REJECTED},
        AssetDisposalCase.UNDER_REVIEW: {AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.AUTHORIZED, AssetDisposalCase.REJECTED},
        AssetDisposalCase.NEEDS_INFORMATION: {AssetDisposalCase.UNDER_REVIEW, AssetDisposalCase.REJECTED},
        AssetDisposalCase.AUTHORIZED: {AssetDisposalCase.DISPOSED},
    }
    action = data["action"]
    if action not in allowed.get(case.status, set()):
        raise ValidationError("This case cannot move to that status. Refresh the page and review its current status.")
    note = data.get("note", "").strip()
    if action in (AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.REJECTED) and not note:
        raise ValidationError("Add a note explaining the request for information or rejection.")
    authority_reference = data.get("authority_reference", "").strip()
    authority_document = data.get("authority_document")
    disposal_method = data.get("disposal_method")
    disposal_date = data.get("disposal_date")
    completion_reference = data.get("completion_reference", "").strip()
    completion_document = data.get("completion_document")
    if action == AssetDisposalCase.AUTHORIZED:
        if not authority_reference:
            raise ValidationError("Record the approval or authority reference before authorizing disposal.")
        if not authority_document and not case.attachments.filter(kind="authority").exists():
            raise ValidationError("Attach the approval or authority document before authorizing disposal.")
    if action == AssetDisposalCase.DISPOSED:
        if not disposal_method or not disposal_date or not completion_reference:
            raise ValidationError("Record the disposal method, completion date, and completion reference.")
        if not completion_document and not case.attachments.filter(kind="completion").exists():
            raise ValidationError("Attach evidence that the disposal was completed.")
        if case.asset.status == Asset.RETIRED:
            raise ValidationError("This asset is already retired; ask an administrator to review the record.")
    _save_disposal_attachments(
        case=case, actor=actor, uploads=data.get("supporting_documents", []),
        kind=AssetDisposalAttachment.SUPPORTING,
    )
    if authority_document:
        _save_disposal_attachments(case=case, actor=actor, uploads=[authority_document], kind="authority")
    if completion_document:
        _save_disposal_attachments(case=case, actor=actor, uploads=[completion_document], kind="completion")
    case.status = action
    case.review_note = note
    case.reviewed_by = actor
    case.reviewed_at = timezone.now()
    fields = ["status", "review_note", "reviewed_by", "reviewed_at"]
    if action == AssetDisposalCase.AUTHORIZED:
        case.authority_reference = authority_reference
        fields.append("authority_reference")
    if action == AssetDisposalCase.DISPOSED:
        case.disposal_method = disposal_method
        case.disposal_date = disposal_date
        case.completion_reference = completion_reference
        case.completed_by = actor
        case.completed_at = timezone.now()
        fields.extend(("disposal_method", "disposal_date", "completion_reference", "completed_by", "completed_at"))
    case.save(update_fields=fields)
    _record_disposal_event(case, actor, action, note)
    if action == AssetDisposalCase.DISPOSED:
        asset = Asset.objects.select_for_update().get(pk=case.asset_id)
        asset.status = Asset.RETIRED
        asset.updated_by = actor
        asset.save(update_fields=("status", "updated_by", "updated_at"))
        AssetAuditEvent.objects.create(
            asset=asset, department_id=asset.department_id, actor=actor,
            action=AssetAuditEvent.DISPOSED, snapshot=asset_snapshot(asset),
        )
    return case


@transaction.atomic
def respond_to_disposal_case(*, actor, case, data):
    case = AssetDisposalCase.objects.select_for_update().select_related("asset").get(pk=case.pk)
    if case.status != AssetDisposalCase.NEEDS_INFORMATION:
        raise ValidationError("This case is not waiting for more information.")
    if case.submitted_by_id != actor.pk or not can_request_asset_disposal(actor, case.asset):
        raise PermissionDenied
    note = data["response"].strip()
    if not note:
        raise ValidationError("Add a short response for GSO.")
    uploads = data.get("supporting_documents", [])
    _save_disposal_attachments(case=case, actor=actor, uploads=uploads, kind=AssetDisposalAttachment.SUPPORTING)
    case.status = AssetDisposalCase.SUBMITTED
    case.review_note = note
    case.submitted_at = timezone.now()
    case.save(update_fields=("status", "review_note", "submitted_at"))
    _record_disposal_event(case, actor, "resubmitted", note)
    return case


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
