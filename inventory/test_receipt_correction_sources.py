from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from . import test_receiving as fixtures
from .models import Asset, AssetAuditEvent, StockMovement
from .receiving import accept_receipt
from .receiving_followups import create_followup, source_basis
from .receipt_correction_sources import lock_unused_source
from .services import record_stock_movement


class ReceiptCorrectionSourceTests(TestCase):
    setUpTestData = classmethod(fixtures.ReceivingPreparationTests.setUpTestData.__func__)
    make_user = classmethod(fixtures.ReceivingPreparationTests.make_user.__func__)
    receipt = fixtures.ReceivingPreparationTests.receipt
    line_data = fixtures.ReceivingPreparationTests.line_data
    add_line = fixtures.ReceivingPreparationTests.add_line
    submit = fixtures.ReceivingPreparationTests.submit
    attach = fixtures.ReceivingPreparationTests.attach

    def setUp(self):
        fixtures.ReceivingPreparationTests.setUp(self)
        self.clerk.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="inventory", codename__in=("issue_stock", "adjust_stock")))

    def accepted(self, **overrides):
        receipt = self.receipt()
        line = self.add_line(receipt, **overrides)
        receipt = self.submit(receipt)
        accept_receipt(actor=self.reviewer, receipt=receipt,
                       expected_version=receipt.state_version, note="Independent inspection")
        line.refresh_from_db()
        return line

    def inspect(self, line, actor=None):
        return lock_unused_source(actor=actor or self.clerk, line_id=line.pk)

    def issue(self, quantity):
        return record_stock_movement(actor=self.clerk, item=self.supply, kind="issue",
            quantity=Decimal(quantity), department_id=self.office.pk, recipient="Synthetic recipient")

    def test_pristine_supply_inspection_is_read_only_and_retains_unknown_cost(self):
        line = self.accepted()
        with CaptureQueriesContext(connection) as queries:
            fresh, source = self.inspect(line)
        self.assertEqual(fresh.pk, line.pk)
        self.assertEqual(source.pk, line.stock_movement_id)
        self.assertIsNone(source.unit_cost)
        self.assertEqual(self.supply.on_hand, 6)
        self.assertFalse(any(query["sql"].lstrip().upper().startswith(
            ("INSERT", "UPDATE", "DELETE")) for query in queries))

    def test_foreign_office_and_draft_are_not_eligible(self):
        line = self.add_line(self.receipt())
        with self.assertRaises(PermissionDenied):
            self.inspect(line, self.outsider)
        with self.assertRaisesMessage(ValidationError, "accepted"):
            self.inspect(line)

    def test_receipt_changed_outside_workflow_is_not_a_fresh_source(self):
        line = self.accepted()
        type(line).objects.filter(pk=line.pk).update(description="Changed after acceptance")
        with self.assertRaisesMessage(ValidationError, "original acceptance"):
            self.inspect(line)

    def test_missing_original_packet_prevents_eligibility(self):
        line = self.accepted()
        Path(line.receipt.evidence.first().file.path).unlink()
        with self.assertRaises(ValidationError):
            self.inspect(line)

    def test_malformed_acceptance_is_a_controlled_reconciliation_error(self):
        line = self.accepted()
        line.receipt.events.filter(action="accepted").update(snapshot={"lines": [None]})
        with self.assertRaisesMessage(ValidationError, "malformed"):
            self.inspect(line)

    def test_source_movement_drift_cannot_be_hidden_by_a_matching_balance(self):
        line = self.accepted(unit_cost=Decimal("20"))
        StockMovement.objects.filter(pk=line.stock_movement_id).update(unit_cost=Decimal("25"))
        with self.assertRaisesMessage(ValidationError, "materialized"):
            self.inspect(line)

    def test_non_fifo_issue_and_return_do_not_restore_before_use_eligibility(self):
        line = self.accepted()
        self.issue("1")
        with self.assertRaisesMessage(ValidationError, "Non-FIFO"):
            self.inspect(line)
        record_stock_movement(actor=self.clerk, item=self.supply, kind="return", quantity=Decimal("1"))
        self.assertEqual(self.supply.on_hand, 6)
        with self.assertRaisesMessage(ValidationError, "unlinked returns"):
            self.inspect(line)

    def test_fifo_usage_of_older_lot_does_not_consume_source_lot(self):
        self.supply.use_fifo = True
        self.supply.save()
        older = self.accepted()
        source = self.accepted()
        self.issue("1")
        self.assertEqual(self.inspect(source)[1].pk, source.stock_movement_id)
        with self.assertRaisesMessage(ValidationError, "already been used"):
            self.inspect(older)
        self.assertFalse(source.stock_movement.created_lot.allocations.exists())

    def test_prior_adjustment_requires_reconciliation_even_if_balance_positive(self):
        line = self.accepted()
        record_stock_movement(actor=self.clerk, item=self.supply, kind="adjustment_out",
            quantity=Decimal("1"), reason="Earlier reconciliation")
        with self.assertRaisesMessage(ValidationError, "adjustments"):
            self.inspect(line)

    def test_draft_followup_is_already_dependent_history(self):
        line = self.accepted()
        create_followup(actor=self.clerk, source_line_id=line.pk, request_id=uuid4(),
            expected_basis=source_basis(line), inspection={
                "inspection_reference": "IAR-2", "inspection_date": line.receipt.inspection_date,
                "inspector_label": "Inspector", "evidence_reference": "Later inspection"},
            quantities={"accepted_quantity": Decimal("1"), "rejected_quantity": Decimal("0"),
                        "unit_cost": None})
        with self.assertRaisesMessage(ValidationError, "Follow-up"):
            self.inspect(line)

    def test_pristine_asset_is_retained_but_downstream_audit_prevents_shortcut(self):
        line = self.accepted(kind="asset", supply_item=None, description="Desk", unit="unit",
            delivered_quantity=Decimal("1"), accepted_quantity=Decimal("1"),
            rejected_quantity=Decimal("0"), rejection_reason="", property_tag="DESK-1")
        fresh, asset = self.inspect(line)
        self.assertEqual(asset.pk, fresh.registered_asset_id)
        self.assertEqual(asset.status, Asset.ACTIVE)
        AssetAuditEvent.objects.create(asset=asset, department_id=self.office.pk, actor=self.clerk,
            action="updated", snapshot={"notes": "Subsequent recorded change"})
        with self.assertRaisesMessage(ValidationError, "downstream"):
            self.inspect(line)
        asset.refresh_from_db()
        self.assertEqual(asset.status, Asset.ACTIVE)
