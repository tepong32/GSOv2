from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from . import test_receipt_correction_sources as fixtures
from .models import Asset, ReceiptQuantityCorrection as Correction, StockMovement
from .receipt_quantity_corrections import record, decide, source_basis, effective_quantities, verify_evidence
from .services import record_stock_movement, update_asset


class ReceiptQuantityCorrectionTests(TestCase):
    setUpTestData = classmethod(fixtures.ReceiptCorrectionSourceTests.setUpTestData.__func__)
    make_user = classmethod(fixtures.ReceiptCorrectionSourceTests.make_user.__func__)
    receipt = fixtures.ReceiptCorrectionSourceTests.receipt
    line_data = fixtures.ReceiptCorrectionSourceTests.line_data
    add_line = fixtures.ReceiptCorrectionSourceTests.add_line
    submit = fixtures.ReceiptCorrectionSourceTests.submit
    attach = fixtures.ReceiptCorrectionSourceTests.attach
    accepted = fixtures.ReceiptCorrectionSourceTests.accepted

    def setUp(self):
        fixtures.ReceiptCorrectionSourceTests.setUp(self)
        storage = patch.object(Correction._meta.get_field("file"), "storage",
                               FileSystemStorage(location=self.storage.name))
        storage.start()
        self.addCleanup(storage.stop)
        for user in (self.clerk, self.reviewer):
            user.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventory",
                codename__in=("record_receipt_quantity_correction", "review_receipt_quantity_correction",
                              "change_asset", "view_asset", "adjust_stock")))

    def args(self, line, quantity="2"):
        return dict(actor=self.clerk, line_id=line.pk, request_id=uuid4(), expected_basis=source_basis(line),
            quantity=Decimal(quantity), reference="Clerical correction 1", reason="Count entered twice before use",
            upload=SimpleUploadedFile("correction.pdf", b"%PDF-1.4\nCorrection packet\n%%EOF"))

    def approve(self, row, actor=None):
        return decide(actor=actor or self.reviewer, correction_id=row.pk, expected_version=row.state_version,
                      action="approve", note="Independently checked clerical overstatement before use")

    def test_fifo_adjusts_original_lot_and_retains_original_receipt(self):
        self.supply.use_fifo = True
        self.supply.save()
        older = self.accepted(unit_cost=Decimal("10"))
        line = self.accepted(unit_cost=Decimal("20"))
        args = self.args(line)
        row = record(**args)
        with self.assertRaises(PermissionDenied):
            self.approve(row, self.clerk)
        row = self.approve(row)
        self.assertEqual(row.adjustment.lot_allocations.get().lot.receipt_id, line.stock_movement_id)
        self.assertFalse(older.stock_movement.created_lot.allocations.exists())
        self.assertEqual(self.supply.on_hand, 10)
        line.refresh_from_db()
        self.assertEqual((line.delivered_quantity, line.accepted_quantity), (10, 6))
        self.assertEqual(effective_quantities(line), {"delivered": 8, "accepted": 4, "corrected": 2})
        self.assertEqual(record(**args).pk, row.pk)
        self.assertEqual(StockMovement.objects.count(), 3)
        verify_evidence(row)

    def test_second_correction_uses_verified_predecessor_and_cumulative_capacity(self):
        self.supply.use_fifo = True
        self.supply.save()
        line = self.accepted()
        first = self.approve(record(**self.args(line)))
        line.refresh_from_db()
        second = self.approve(record(**self.args(line, "1")))
        self.assertEqual(second.predecessor_id, first.pk)
        self.assertEqual(self.supply.on_hand, 3)
        line.refresh_from_db()
        with self.assertRaisesMessage(ValidationError, "exceeds"):
            record(**self.args(line, "4"))

    def test_pending_hold_blocks_stock_and_cancel_survives_missing_packet(self):
        line = self.accepted()
        row = record(**self.args(line))
        with self.assertRaisesMessage(ValidationError, "awaiting review"):
            record_stock_movement(actor=self.clerk, item=self.supply, kind="adjustment_out",
                                  quantity=Decimal("1"), reason="Unrelated adjustment")
        Path(row.file.path).unlink()
        with self.assertRaisesMessage(ValidationError, "missing or changed"):
            self.approve(row)
        decide(actor=self.clerk, correction_id=row.pk, expected_version=1,
               action="cancel", note="Restore packet before recording a new proposal")
        record_stock_movement(actor=self.clerk, item=self.supply, kind="adjustment_out",
                              quantity=Decimal("1"), reason="Subsequent independently documented adjustment")
        self.assertEqual(self.supply.on_hand, 5)

    def test_asset_becomes_retained_erroneous_entry_not_disposal(self):
        line = self.accepted(kind="asset", supply_item=None, description="Desk", unit="unit",
            delivered_quantity=Decimal("1"), accepted_quantity=Decimal("1"),
            rejected_quantity=Decimal("0"), rejection_reason="", property_tag="DESK-1")
        row = record(**self.args(line, "1"))
        with self.assertRaisesMessage(ValidationError, "awaiting review"):
            update_asset(actor=self.clerk, asset=line.registered_asset, data={"notes": "Change"})
        row = self.approve(row)
        asset = Asset.objects.get(pk=line.registered_asset_id)
        self.assertEqual(asset.status, Asset.ENTRY_VOID)
        self.assertFalse(asset.disposal_cases.exists())
        self.assertEqual(row.asset_event.asset_id, asset.pk)
        self.assertEqual(effective_quantities(line)["accepted"], 0)
        with self.assertRaisesMessage(ValidationError, "erroneous entry"):
            update_asset(actor=self.clerk, asset=asset, data={"status": Asset.ACTIVE})
        self.client.force_login(self.clerk)
        response = self.client.get(reverse("inventory:asset-detail", args=[asset.pk]))
        self.assertContains(response, "Original recorded quantity")
        self.assertContains(response, "Receipt quantity correction and retained evidence")

    def test_later_followup_retains_correction_without_reopening_capacity(self):
        from .receiving_followups import create_followup, source_basis as followup_basis, remaining_quantity
        from .receiving import accept_receipt
        line = self.accepted()
        self.approve(record(**self.args(line)))
        line.refresh_from_db()
        basis = followup_basis(line)
        self.assertIn("quantity_correction", basis)
        child = create_followup(actor=self.clerk, source_line_id=line.pk, request_id=uuid4(),
            expected_basis=basis, inspection=dict(inspection_reference="LATER-INSPECTION",
                inspection_date=line.receipt.inspection_date, inspector_label="Inspector", evidence_reference="Later packet"),
            quantities=dict(accepted_quantity=Decimal("1"), rejected_quantity=Decimal("0")))
        child = self.submit(child)
        accept_receipt(actor=self.reviewer, receipt=child, expected_version=child.state_version,
                       note="Independent later inspection")
        self.assertEqual(remaining_quantity(line), 1)
        self.assertEqual(self.supply.on_hand, 5)
        with self.assertRaisesMessage(ValidationError, "Follow-up"):
            record(**self.args(line, "1"))

    def test_tampered_result_and_changed_request_are_rejected(self):
        line = self.accepted()
        args = self.args(line)
        row = self.approve(record(**args))
        with self.assertRaisesMessage(ValidationError, "different content"):
            record(**dict(args, quantity=Decimal("3")))
        StockMovement.objects.filter(pk=row.adjustment_id).update(quantity=Decimal("3"))
        with self.assertRaisesMessage(ValidationError, "does not match"):
            effective_quantities(line)

    def test_signed_http_record_independent_review_and_private_evidence(self):
        line = self.accepted()
        url = reverse("inventory:receipt-quantity-corrections", args=[line.pk])
        self.client.force_login(self.clerk)
        preview = self.client.get(url)
        self.assertEqual(preview.status_code, 200)
        token = preview.context["form"].initial["source_token"]
        response = self.client.post(url, {"source_token": token, "quantity": "2",
            "reference": "Correction source", "reason": "Clerical count entered too high",
            "clerical_case": "on", "upload": self.args(line)["upload"]})
        row = Correction.objects.get()
        detail_url = reverse("inventory:receipt-quantity-detail", args=[row.pk])
        self.assertRedirects(response, detail_url)
        self.assertEqual(self.client.post(detail_url, {"expected_version": 1,
            "action": "approve", "note": "Self review"}).status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.status, row.PENDING)
        self.client.force_login(self.reviewer)
        self.assertRedirects(self.client.post(detail_url, {"expected_version": 1,
            "action": "approve", "note": "Independently verified before-use clerical case"}), detail_url)
        row.refresh_from_db()
        self.assertEqual(row.status, row.APPROVED)
        evidence_url = reverse("inventory:receipt-quantity-evidence", args=[row.pk])
        response = self.client.get(evidence_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(evidence_url).status_code, 404)
        self.client.force_login(self.reviewer)
        Path(row.file.path).write_bytes(b"changed")
        self.assertEqual(self.client.get(evidence_url).status_code, 404)
