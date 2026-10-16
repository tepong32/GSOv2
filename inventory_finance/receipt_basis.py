"""Retained physical receipt facts supporting a claim; never financial valuation."""
from decimal import Decimal

from inventory.receiving import HEADER_FIELDS


def receipt_basis(line):
    receipt = line.receipt

    def value(raw):
        if raw is None:
            return None
        if isinstance(raw, Decimal):
            return format(raw, "f")
        return raw.isoformat() if hasattr(raw, "isoformat") else raw

    return {
        "schema": 1,
        "receipt_uuid": str(receipt.public_id), "receipt_version": receipt.state_version,
        "status": receipt.status, "department_local_id": receipt.department_id,
        "department_label": receipt.department_label,
        "header": {key: value(getattr(receipt, key)) for key in sorted(HEADER_FIELDS)},
        "reviewed_by_local_id": receipt.reviewed_by_id, "reviewed_at": value(receipt.reviewed_at),
        "line": {key: value(getattr(line, key)) for key in (
            "sequence", "kind", "description", "unit", "delivered_quantity", "accepted_quantity",
            "rejected_quantity", "rejection_reason", "unit_cost", "is_void", "asset_kind",
            "property_tag", "serial_number", "chassis_number")},
        "supply_uuid": str(line.supply_item.public_id) if line.supply_item_id else None,
        "asset_uuid": str(line.registered_asset.public_id) if line.registered_asset_id else None,
        "movement_uuid": str(line.stock_movement.public_id) if line.stock_movement_id else None,
        "evidence": list(receipt.evidence.order_by("pk").values(
            "kind", "sha256", "size", "original_filename", "note")),
    }


def receipt_basis_current(row, line=None):
    # NULL is an explicit pre-migration unknown, never a fabricated approval basis.
    return bool(row.receipt_snapshot and row.receipt_snapshot == receipt_basis(line or row.receipt_line))
