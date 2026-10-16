"""Real connections exercise locking; SQLite deliberately skips these tests."""
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from user.models import Department, User
from .models import Asset, ConsumableItem, ReceivingEvidence, ReceivingReceipt, StockMovement
from .receiving import create_receipt, save_receipt_line, attach_receipt_evidence, submit_receipt, accept_receipt
from .services import create_asset
from . import test_receiving


@skipUnlessDBFeature("has_select_for_update")
class ReceivingConcurrencyTests(TransactionTestCase):
    def setUp(self):
        storage = TemporaryDirectory()
        self.addCleanup(storage.cleanup)
        replacement = patch.object(ReceivingEvidence._meta.get_field("file"), "storage",
                                   FileSystemStorage(location=storage.name))
        replacement.start()
        self.addCleanup(replacement.stop)
        self.office = Department.objects.create(name="General Services")
        self.clerk = test_receiving.ReceivingPreparationTests.make_user("race-clerk", self.office)
        self.reviewer = test_receiving.ReceivingPreparationTests.make_user("race-reviewer", self.office)
        self.supply = ConsumableItem.objects.create(department_id=self.office.pk, name="Paper", unit="ream")

    def receipt(self, asset=False):
        receipt = create_receipt(actor=self.clerk, data=dict(supplier="Synthetic race vendor",
            delivery_reference="RACE", delivery_date=timezone.localdate(), inspection_date=timezone.localdate(),
            inspection_reference="IAR-RACE", inspector_label="Inspector", evidence_reference="Synthetic race evidence"))
        line = dict(kind="asset" if asset else "supply", description="Synthetic item", unit="piece" if asset else "ream",
                    delivered_quantity=1, accepted_quantity=1, rejected_quantity=0)
        line.update(property_tag="RACE-TAG") if asset else line.update(supply_item=self.supply)
        save_receipt_line(actor=self.clerk, receipt=receipt, data=line, expected_version=1)
        for kind in ("delivery", "inspection"):
            receipt.refresh_from_db()
            attach_receipt_evidence(actor=self.clerk, receipt=receipt, expected_version=receipt.state_version,
                kind=kind, upload=SimpleUploadedFile("race.pdf", b"%PDF-1.4\nSynthetic race\n%%EOF"), note="Synthetic")
        receipt.refresh_from_db()
        return submit_receipt(actor=self.clerk, receipt=receipt, expected_version=receipt.state_version)

    def race(self, operations):
        barrier = Barrier(len(operations))
        reviewer_id = self.reviewer.pk
        def run(operation):
            connections.close_all()
            try:
                actor = User.objects.get(pk=reviewer_id)
                barrier.wait(timeout=10)
                operation(actor)
                return "accepted"
            except ValidationError:
                return "conflict"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            futures = [pool.submit(run, operation) for operation in operations]
            results = [future.result(timeout=30) for future in futures]
        self.assertCountEqual(results, ["accepted", "conflict"])

    def acceptance(self, receipt):
        return lambda actor: accept_receipt(actor=actor,
            receipt=ReceivingReceipt.objects.get(pk=receipt.pk), expected_version=receipt.state_version, note="Race review")

    def test_two_reviewers_cannot_duplicate_one_receipts_stock(self):
        receipt = self.receipt()
        self.race([self.acceptance(receipt), self.acceptance(receipt)])
        self.assertEqual(StockMovement.objects.count(), 1)
        self.assertEqual(self.supply.on_hand, 1)
        self.assertEqual(receipt.events.filter(action="accepted").count(), 1)

    def test_competing_receipts_cannot_register_duplicate_asset_identifiers(self):
        first, second = self.receipt(asset=True), self.receipt(asset=True)
        self.race([self.acceptance(first), self.acceptance(second)])
        self.assertEqual(Asset.objects.count(), 1)
        self.assertEqual(ReceivingReceipt.objects.filter(status="accepted").count(), 1)
        self.assertEqual(ReceivingReceipt.objects.filter(status="submitted").count(), 1)

    def test_ordinary_asset_creation_competes_safely_with_receipt(self):
        receipt = self.receipt(asset=True)
        self.race([self.acceptance(receipt), lambda actor: create_asset(actor=actor,
            data={"asset_name": "Ordinary entry", "property_tag": " race-tag "})])
        self.assertEqual(Asset.objects.count(), 1)
