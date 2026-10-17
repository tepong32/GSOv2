from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import Permission
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, skipUnlessDBFeature

from . import test_receiving_concurrency as fixtures
from .models import ReceiptQuantityCorrection as Correction, StockMovement
from .receiving import accept_receipt
from .receipt_quantity_corrections import record, decide, source_basis
from .services import record_stock_movement


@skipUnlessDBFeature("has_select_for_update")
class QuantityCorrectionConcurrencyTests(TransactionTestCase):
    receipt = fixtures.ReceivingConcurrencyTests.receipt
    race = fixtures.ReceivingConcurrencyTests.race

    def setUp(self):
        fixtures.ReceivingConcurrencyTests.setUp(self)
        files = TemporaryDirectory()
        self.addCleanup(files.cleanup)
        storage = patch.object(Correction._meta.get_field("file"), "storage", FileSystemStorage(location=files.name))
        storage.start()
        self.addCleanup(storage.stop)
        for actor in (self.clerk, self.reviewer):
            actor.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventory", codename__in=(
                "record_receipt_quantity_correction", "review_receipt_quantity_correction", "adjust_stock", "issue_stock")))
        self.supply.use_fifo = True
        self.supply.save()
        receipt = self.receipt()
        receipt = accept_receipt(actor=self.reviewer, receipt=receipt, expected_version=receipt.state_version, note="Original")
        self.line = receipt.lines.get()
        self.basis = source_basis(self.line)

    def proposal(self, actor):
        return record(actor=actor, line_id=self.line.pk, request_id=uuid4(), expected_basis=self.basis,
            quantity=Decimal("0.5"), reference="Race correction", reason="Clerical overstatement before use",
            upload=SimpleUploadedFile("race.pdf", b"%PDF-1.4\nCorrection race\n%%EOF"))

    def test_two_approvals_cannot_double_adjust_the_source_lot(self):
        row = self.proposal(self.clerk)
        approve = lambda actor: decide(actor=actor, correction_id=row.pk, expected_version=1,
                                       action="approve", note="Independent correction review")
        self.race([approve, approve])
        self.assertEqual(self.supply.on_hand, Decimal("0.5"))
        self.assertEqual(StockMovement.objects.filter(kind="adjustment_out").count(), 1)
        self.assertEqual(row.events.count(), 2)
        self.assertEqual(self.line.stock_movement.created_lot.allocations.count(), 1)

    def test_issue_and_proposal_cannot_both_pass_before_use_checks(self):
        self.race([self.proposal, lambda actor: record_stock_movement(actor=actor, item=self.supply,
            kind="issue", quantity=Decimal("1"), department_id=self.office.pk, recipient="Synthetic recipient")])
        proposals = Correction.objects.count()
        issues = StockMovement.objects.filter(kind="issue").count()
        self.assertEqual(proposals + issues, 1)
        self.assertEqual(self.supply.on_hand, 1 - issues)
