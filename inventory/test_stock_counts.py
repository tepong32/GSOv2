from datetime import timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils import timezone

from user.models import User
from . import tests as stock_tests
from .models import StockCount, StockCountEvidence, StockLotAllocation
from .services import record_stock_movement
from .stock_counts import record_count, attach_count_evidence, decide_count, stock_basis


class StockCountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        stock_tests.ConsumableStockWorkflowTests.setUpTestData.__func__(cls)
        cls.reviewer = User.objects.create_user(username="count-reviewer", department=cls.gso)
        cls.reviewer.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventory",
            codename__in=("view_consumableitem", "record_stock_count", "review_stock_count", "adjust_stock")))

    create_item = stock_tests.ConsumableStockWorkflowTests.create_item

    def setUp(self):
        self.files = TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        storage = patch.object(StockCountEvidence._meta.get_field("file"), "storage", FileSystemStorage(location=self.files.name))
        storage.start()
        self.addCleanup(storage.stop)
        self.item = self.create_item(fifo=True)
        record_stock_movement(actor=self.actor, item=self.item, kind="receipt", quantity="10", unit_cost="25.00")

    def record(self, quantity="8", request_id=None, **kwargs):
        data = dict(actor=self.actor, item=self.item, request_id=request_id or uuid4(),
            expected_basis=stock_basis(self.item), counted_on=timezone.localdate(), quantity=quantity,
            reference="COUNT-SHEET-1", note="Physical count and investigated variance")
        data.update(kwargs)
        return record_count(**data)

    def evidence(self, count, actor=None):
        evidence = attach_count_evidence(actor=actor or self.actor, count=count, expected_version=count.state_version,
            upload=SimpleUploadedFile("count.pdf", b"%PDF-1.4\nSynthetic count\n%%EOF", content_type="application/pdf"),
            note="Signed count sheet")
        count.refresh_from_db()
        return evidence

    def approve(self, count, actor=None):
        return decide_count(actor=actor or self.reviewer, count=count, expected_version=count.state_version,
                            action="approve", note="Independently reconciled count sheet and variance")

    def test_shortage_creates_one_traceable_fifo_adjustment_and_keeps_history(self):
        count = self.record()
        self.assertEqual(count.basis["last_movement_uuid"], str(self.item.movements.get().public_id))
        self.evidence(count)
        approved = self.approve(count)
        self.assertEqual(self.item.on_hand, Decimal("8.000"))
        self.assertEqual(approved.adjustment.kind, "adjustment_out")
        self.assertEqual(StockLotAllocation.objects.get().quantity, Decimal("2.000"))
        self.assertEqual(approved.adjustment.physical_count.pk, count.pk)
        self.assertEqual(list(count.events.values_list("action", flat=True)), ["recorded", "evidence_added", "approved"])
        with self.assertRaises(ValidationError):
            self.approve(count)
        self.assertEqual(self.item.movements.count(), 2)

    def test_equal_count_has_no_fake_movement_and_surplus_cost_stays_unknown(self):
        equal = self.record("10")
        self.evidence(equal)
        equal = self.approve(equal)
        self.assertIsNone(equal.adjustment_id)
        self.assertEqual(self.item.movements.count(), 1)
        surplus = self.record("10.125")
        self.evidence(surplus)
        surplus = self.approve(surplus)
        self.assertIsNone(surplus.adjustment.unit_cost)
        self.assertIsNone(surplus.adjustment.created_lot.unit_cost)
        self.assertEqual(self.item.on_hand, Decimal("10.125"))

    def test_offsetting_movements_invalidate_basis_and_cancel_preserves_observation(self):
        count = self.record()
        self.evidence(count)
        record_stock_movement(actor=self.actor, item=self.item, kind="adjustment_in", quantity="1", reason="Other correction")
        record_stock_movement(actor=self.actor, item=self.item, kind="adjustment_out", quantity="1", reason="Reversal")
        with self.assertRaisesMessage(ValidationError, "ledger changed"):
            self.approve(count)
        result = decide_count(actor=self.actor, count=count, expected_version=count.state_version, action="cancel", note="Recount required")
        self.assertEqual(result.quantity, Decimal("8"))
        self.assertEqual(result.status, StockCount.CANCELLED)
        self.assertEqual(self.item.on_hand, Decimal("10"))
        self.assertEqual(count.evidence.count(), 1)

    def test_independent_actor_evidence_integrity_and_version_are_required(self):
        count = self.record()
        with self.assertRaises(ValidationError):
            self.approve(count)
        evidence = self.evidence(count)
        with self.assertRaises(PermissionDenied):
            self.approve(count, actor=self.actor)
        with self.assertRaises(ValidationError):
            decide_count(actor=self.reviewer, count=count, expected_version=1, action="approve", note="Stale")
        original = Path(evidence.file.path).read_bytes()
        Path(evidence.file.path).write_bytes(b"changed")
        with self.assertRaises(ValidationError):
            self.approve(count)
        with self.assertRaises(CommandError):
            call_command("check_stock_count_evidence", stdout=StringIO())
        Path(evidence.file.path).write_bytes(original)
        call_command("check_stock_count_evidence", stdout=StringIO())
        self.evidence(count, actor=self.reviewer)
        with self.assertRaises(PermissionDenied):
            self.approve(count)
        self.assertEqual(self.item.movements.count(), 1)

    def test_request_identity_is_idempotent_after_closure_and_different_content_rejected(self):
        request_id = uuid4()
        basis = stock_basis(self.item)
        count = self.record(request_id=request_id)
        self.assertEqual(self.record(request_id=request_id).pk, count.pk)
        self.evidence(count)
        self.approve(count)
        self.assertEqual(self.record(request_id=request_id, expected_basis=basis).pk, count.pk)
        with self.assertRaises(ValidationError):
            self.record("9", request_id=request_id, expected_basis=basis)

    def test_invalid_dates_numbers_and_stale_source_do_not_create_counts(self):
        for quantity in ("NaN", "-1", "0.0001"):
            with self.subTest(quantity=quantity), self.assertRaises(ValidationError):
                self.record(quantity)
        for offset in (-1, 1):
            with self.subTest(offset=offset), self.assertRaises(ValidationError):
                self.record(counted_on=timezone.localdate()+timedelta(days=offset))
        basis = stock_basis(self.item)
        record_stock_movement(actor=self.actor, item=self.item, kind="receipt", quantity="1")
        with self.assertRaises(ValidationError):
            self.record(expected_basis=basis)
        self.assertEqual(StockCount.objects.count(), 0)

    def test_audit_failure_rolls_back_adjustment_allocations_and_decision(self):
        count = self.record()
        self.evidence(count)
        with patch("inventory.stock_counts._event", side_effect=RuntimeError("injected audit failure")):
            with self.assertRaises(RuntimeError):
                self.approve(count)
        count.refresh_from_db()
        self.assertEqual(count.status, StockCount.PENDING)
        self.assertIsNone(count.adjustment_id)
        self.assertEqual(self.item.on_hand, Decimal("10"))
        self.assertEqual(StockLotAllocation.objects.count(), 0)
        self.approve(count)

    def test_reviewer_can_decline_without_permission_to_record_or_upload(self):
        self.reviewer.user_permissions.remove(Permission.objects.get(content_type__app_label="inventory", codename="record_stock_count"))
        count = self.record()
        with self.assertRaises(PermissionDenied):
            self.evidence(count, actor=self.reviewer)
        cancelled = decide_count(actor=self.reviewer, count=count, expected_version=1, action="cancel", note="Count evidence needs correction")
        self.assertEqual(cancelled.status, StockCount.CANCELLED)
        self.assertEqual(self.item.movements.count(), 1)
