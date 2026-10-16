from decimal import Decimal
from io import StringIO
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.urls import reverse

from . import test_receiving
from .models import ReceiptCostAmendment, ReceivingReceipt, StockMovement
from .receiving import accept_receipt
from .receipt_amendments import record_amendment, decide_amendment, amendment_basis, effective_cost


class ReceiptAmendmentTests(TestCase):
    make_user = classmethod(test_receiving.ReceivingPreparationTests.make_user.__func__)
    receipt = test_receiving.ReceivingPreparationTests.receipt
    line_data = test_receiving.ReceivingPreparationTests.line_data
    add_line = test_receiving.ReceivingPreparationTests.add_line
    attach = test_receiving.ReceivingPreparationTests.attach
    submit = test_receiving.ReceivingPreparationTests.submit

    @classmethod
    def setUpTestData(cls):
        test_receiving.ReceivingPreparationTests.setUpTestData.__func__(cls)
        permissions = Permission.objects.filter(content_type__app_label="inventory", codename__in=(
            "record_receiptcostamendment", "review_receiptcostamendment"))
        for actor in (cls.clerk, cls.reviewer, cls.outsider):
            actor.user_permissions.add(*permissions)

    def setUp(self):
        test_receiving.ReceivingPreparationTests.setUp(self)
        storage = patch.object(ReceiptCostAmendment._meta.get_field("file"), "storage", FileSystemStorage(location=self.storage.name))
        storage.start()
        self.addCleanup(storage.stop)
        receipt = self.receipt()
        self.line = self.add_line(receipt, unit_cost=Decimal("10.00"))
        receipt = self.submit(receipt)
        accept_receipt(actor=self.reviewer, receipt=receipt, expected_version=receipt.state_version, note="Accepted source")
        self.line.refresh_from_db()

    def upload(self):
        return SimpleUploadedFile("correction.pdf", b"%PDF-1.4\nCorrecting source\n%%EOF", content_type="application/pdf")

    def record(self, **overrides):
        self.line.refresh_from_db()
        data = dict(actor=self.clerk, line=self.line, request_id=uuid4(), expected_basis=amendment_basis(self.line),
            unit_cost="12.00", reference="Corrected invoice", reason="Supplier documentary correction", upload=self.upload())
        data.update(overrides)
        return record_amendment(**data)

    def approve(self, row):
        return decide_amendment(actor=self.reviewer, amendment=row, expected_version=row.state_version,
            action="approve", note="Independently compared correcting document")

    def test_approved_chain_preserves_original_stock_and_receipt(self):
        movement = self.line.stock_movement
        original = list(StockMovement.objects.values())
        row = self.approve(self.record())
        self.line.refresh_from_db()
        self.assertEqual(effective_cost(self.line), Decimal("12.00"))
        self.assertEqual(self.line.unit_cost, Decimal("10.00"))
        self.assertEqual(list(StockMovement.objects.values()), original)
        next_row = self.approve(self.record(unit_cost="9.00"))
        self.assertEqual(next_row.predecessor_id, row.pk)
        self.assertEqual(next_row.basis["effective_unit_cost"], "12.00")
        self.assertEqual(row.events.count(), 2)
        self.assertEqual(next_row.events.count(), 2)
        self.assertEqual(list(StockMovement.objects.values()), original)

    def test_duplicate_and_pending_requests_do_not_duplicate_history(self):
        request_id = uuid4()
        row = self.record(request_id=request_id)
        self.assertEqual(self.record(request_id=request_id).pk, row.pk)
        with self.assertRaises(ValidationError):
            self.record()
        with self.assertRaises(ValidationError):
            self.record(request_id=request_id, unit_cost="20.00")
        self.assertEqual(row.events.count(), 1)

    def test_unknown_zero_exact_cost_and_authority(self):
        for bad in (True, 1.2, "NaN", "Infinity", "-1", "1.001"):
            with self.subTest(cost=bad), self.assertRaises(ValidationError):
                self.record(unit_cost=bad)
        row = self.record(unit_cost=None)
        with self.assertRaises(PermissionDenied):
            decide_amendment(actor=self.clerk, amendment=row, expected_version=1, action="approve", note="Self")
        with self.assertRaises(PermissionDenied):
            decide_amendment(actor=self.outsider, amendment=row, expected_version=1, action="approve", note="Other office")
        self.approve(row)
        self.line.refresh_from_db()
        self.assertIsNone(effective_cost(self.line))
        self.approve(self.record(unit_cost="0.00"))
        self.line.refresh_from_db()
        self.assertEqual(effective_cost(self.line), 0)

    def test_stale_basis_and_corrupt_evidence_cannot_be_approved(self):
        row = self.record()
        path = Path(row.file.path)
        path.write_bytes(b"changed evidence")
        with self.assertRaises(ValidationError):
            self.approve(row)
        with self.assertRaises(CommandError):
            call_command("check_receipt_amendment_evidence", stdout=StringIO())
        decide_amendment(actor=self.reviewer, amendment=row, expected_version=1, action="reject", note="Investigate corrupt evidence")
        row = self.record()
        ReceivingReceipt.objects.filter(pk=self.line.receipt_id).update(delivery_reference="Out-of-band change")
        with self.assertRaises(ValidationError):
            self.approve(row)
        row.refresh_from_db()
        self.assertEqual(row.status, row.PENDING)

    def test_signed_http_review_and_scoped_private_download(self):
        self.client.force_login(self.clerk)
        start = reverse("inventory:receipt-amendments", args=[self.line.pk])
        page = self.client.get(start)
        token = page.context["form"].initial["source_token"]
        response = self.client.post(start, {"source_token": token, "unit_cost": "15.00", "reference": "Correcting invoice", "reason": "Documentary correction", "upload": self.upload()})
        self.assertEqual(response.status_code, 302)
        row = ReceiptCostAmendment.objects.get()
        detail = reverse("inventory:receipt-amendment-detail", args=[row.pk])
        self.assertEqual(self.client.post(detail, {"expected_version": 1, "action": "approve", "note": "Self"}).status_code, 403)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post(detail, {"expected_version": 1, "action": "approve", "note": "Verified original and correction"}).status_code, 302)
        response = self.client.get(reverse("inventory:receipt-amendment-evidence", args=[row.pk]))
        body = b"".join(response.streaming_content)
        self.assertTrue(body.startswith(b"%PDF"))
        self.assertIn("no-store", response["Cache-Control"])
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.get(reverse("inventory:receipt-amendment-evidence", args=[row.pk])).status_code, 404)
