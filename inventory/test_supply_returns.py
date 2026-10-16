import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone
from . import tests as fixtures
from . import supply_returns as service
from .models import SupplyReturn, ConsumableItem, StockMovement
from .services import record_stock_movement


class SupplyReturnTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ConsumableStockWorkflowTests.setUpTestData.__func__(cls)
        cls.reviewer = get_user_model().objects.create_superuser(username="return-reviewer", email="r@example.test", password="test")
        cls.item = ConsumableItem.objects.create(department_id=cls.gso.pk, name="Return paper", unit="ream", use_fifo=True)
        for cost in ("10", "30"):
            record_stock_movement(actor=cls.actor, item=cls.item, kind="receipt", quantity="3", unit_cost=cost)
        cls.issue = record_stock_movement(actor=cls.actor, item=cls.item, kind="issue", quantity="6",
            department_id=cls.finance.pk, recipient="Original recipient", reference="ISSUE-1")

    def setUp(self):
        files = tempfile.TemporaryDirectory()
        self.addCleanup(files.cleanup)
        self.root = Path(files.name)
        storage = patch.object(SupplyReturn._meta.get_field("file"), "storage", FileSystemStorage(location=files.name))
        storage.start()
        self.addCleanup(storage.stop)

    def record(self, **kwargs):
        args = dict(actor=self.actor, issue=self.issue, request_id=uuid4(), expected_source=service.source_basis(self.issue),
            source_allocation_id=None, quantity="2", reference="RETURN-1", returned_by="Returning clerk",
            observed_on=timezone.localdate(), condition_note="Unused and dry", cost_basis_note="Lot identity unavailable",
            upload=SimpleUploadedFile("return.pdf", b"%PDF-observed return evidence"))
        args.update(kwargs)
        return service.record_return(**args)

    def accept(self, case, **kwargs):
        args = dict(actor=self.reviewer, case=case, expected_version=case.state_version, action="accept",
            note="Counted and inspected", suitable_for_stock=True)
        args.update(kwargs)
        return service.decide_return(**args)

    def test_known_original_lot_cost_and_quantity_are_preserved_without_rewriting_issue(self):
        allocation = self.issue.lot_allocations.order_by("pk").first()
        case = self.record(source_allocation_id=allocation.pk, cost_basis_note="Package matches documented original lot")
        self.assertEqual(self.item.on_hand, 0)
        with self.assertRaises(PermissionDenied):
            self.accept(case, actor=self.actor)
        with self.assertRaises(ValidationError):
            self.accept(case, suitable_for_stock=False)
        case = self.accept(case)
        self.assertEqual(self.item.on_hand, 2)
        self.assertEqual(case.movement.unit_cost, 10)
        self.assertEqual(case.movement.created_lot.unit_cost, 10)
        self.assertEqual(case.movement.created_lot.quantity, 2)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.quantity, 6)
        self.assertEqual(self.issue.lot_allocations.count(), 2)
        service.verify_history(case)
        with self.assertRaises(ValidationError):
            self.accept(case)
        with self.assertRaises(ValidationError):
            self.record(source_allocation_id=allocation.pk, quantity="2")
        other = self.issue.lot_allocations.order_by("pk").last()
        self.accept(self.record(source_allocation_id=other.pk, quantity="3", cost_basis_note="Other package confirmed"))
        with self.assertRaises(ValidationError):
            self.record(quantity="2")

    def test_unknown_return_cost_remains_unknown_on_lot_and_reissue(self):
        case = self.accept(self.record())
        self.assertIsNone(case.source_allocation_id)
        self.assertIsNone(case.movement.unit_cost)
        self.assertIsNone(case.movement.created_lot.unit_cost)
        reissue = record_stock_movement(actor=self.actor, item=self.item, kind="issue", quantity="1",
            department_id=self.finance.pk, recipient="Later recipient")
        self.assertEqual(reissue.lot_allocations.get().lot_id, case.movement.created_lot.pk)
        self.assertIsNone(reissue.lot_allocations.get().lot.unit_cost)
        self.assertEqual(self.item.on_hand, 1)

    def test_quantity_only_return_and_decline_and_cancel_have_explicit_effects(self):
        item = ConsumableItem.objects.create(department_id=self.gso.pk, name="Uncosted", unit="piece")
        record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="5")
        issue = record_stock_movement(actor=self.actor, item=item, kind="issue", quantity="5", department_id=self.finance.pk, recipient="Clerk")
        case = self.record(issue=issue, expected_source=service.source_basis(issue))
        self.accept(case, action="decline", note="Damaged; retained separately pending disposition")
        self.assertEqual(item.on_hand, 0)
        case = self.record(issue=issue, expected_source=service.source_basis(issue))
        self.accept(case, actor=self.actor, action="cancel", note="Wrong observation")
        self.assertEqual(item.on_hand, 0)
        case = self.accept(self.record(issue=issue, expected_source=service.source_basis(issue)))
        self.assertEqual(item.on_hand, 2)
        self.assertEqual(item.lots.count(), 0)
        service.verify_history(case)

    def test_retries_exact_decimals_rollback_and_legacy_lineage_guard(self):
        key = uuid4()
        case = self.record(request_id=key)
        self.assertEqual(self.record(request_id=key).pk, case.pk)
        with self.assertRaises(ValidationError):
            self.record(request_id=key, quantity="1")
        for value in ("0", "-1", "0.0001", "NaN", "Infinity"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.record(quantity=value)
        with patch("inventory.supply_returns._event", side_effect=RuntimeError("failed history write")):
            with self.assertRaises(RuntimeError):
                self.accept(case)
        self.assertEqual(self.item.on_hand, 0)
        case.refresh_from_db()
        self.assertEqual(case.status, "pending")
        record_stock_movement(actor=self.actor, item=self.item, kind="return", quantity="1")
        with self.assertRaisesMessage(ValidationError, "unlinked legacy returns"):
            self.accept(case)
        self.assertEqual(self.item.on_hand, 1)

    def test_missing_changed_evidence_and_source_and_history_block_acceptance(self):
        case = self.record()
        path = Path(case.file.path)
        original = path.read_bytes()
        path.write_bytes(b"changed")
        with self.assertRaises(ValidationError):
            self.accept(case)
        path.unlink()
        for _ in range(2):
            with self.assertRaises(ValidationError):
                service.verify_source(case)
        path.write_bytes(original)
        SupplyReturn.objects.filter(pk=case.pk).update(returned_by="Tampered")
        case.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.accept(case)

        SupplyReturn.objects.filter(pk=case.pk).update(returned_by="Returning clerk")
        case.refresh_from_db()
        StockMovement.objects.filter(pk=self.issue.pk).update(recipient="Changed source recipient")
        with self.assertRaisesMessage(ValidationError, "original issue or lot basis changed"):
            self.accept(case)

    def test_http_signed_start_independent_review_and_duplicate_acceptance(self):
        self.client.force_login(self.actor)
        url = reverse("inventory:supply-return-start", args=(self.issue.pk,))
        response = self.client.get(url)
        token = response.context["form"].initial["source_token"]
        data = dict(source_token=token, source_allocation_id="", quantity="2", reference="RETURN-HTTP", returned_by="Clerk",
            observed_on=str(timezone.localdate()), condition_note="Unused", cost_basis_note="Original lot unknown")
        invalid = self.client.post(url, {**data, "source_token": "bad", "upload": SimpleUploadedFile("a.pdf", b"%PDF-http")})
        self.assertContains(invalid, "expired or changed")
        for _ in range(2):
            self.assertEqual(self.client.post(url, {**data, "upload": SimpleUploadedFile("a.pdf", b"%PDF-http")}).status_code, 302)
        case = SupplyReturn.objects.get(reference="RETURN-HTTP")
        detail = reverse("inventory:supply-return-detail", args=(case.pk,))
        self.assertNotContains(self.client.get(detail), "Accept into usable stock</button>")
        self.client.force_login(self.reviewer)
        post = {"operation": "accept", "expected_version": 1, "accept-note": "Observed serviceable goods", "accept-suitable_for_stock": "on"}
        self.assertEqual(self.client.post(detail, post).status_code, 302)
        self.assertContains(self.client.post(detail, post), "already decided")
        self.assertEqual(self.item.on_hand, 2)
        response = self.client.get(reverse("inventory:supply-return-evidence", args=(case.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        b"".join(response.streaming_content)


@skipUnlessDBFeature("has_select_for_update")
class SupplyReturnRaceTests(TransactionTestCase):
    def test_competing_cases_cannot_return_more_than_original_issue(self):
        fixtures.ConsumableStockWorkflowTests.setUpTestData.__func__(type(self))
        reviewer = get_user_model().objects.create_superuser(username="race-return-reviewer", email="r@example.test", password="test")
        item = ConsumableItem.objects.create(department_id=self.gso.pk, name="Return race", unit="ream", use_fifo=True)
        record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="5", unit_cost="10")
        issue = record_stock_movement(actor=self.actor, item=item, kind="issue", quantity="5", department_id=self.finance.pk, recipient="Clerk")
        with tempfile.TemporaryDirectory() as root, patch.object(SupplyReturn._meta.get_field("file"), "storage", FileSystemStorage(location=root)):
            cases = [service.record_return(actor=self.actor, issue=issue, request_id=uuid4(), expected_source=service.source_basis(issue),
                source_allocation_id=issue.lot_allocations.get().pk, quantity="4", reference=f"RACE-{index}", returned_by="Clerk",
                observed_on=timezone.localdate(), condition_note="Unused", cost_basis_note="Original package",
                upload=SimpleUploadedFile("a.pdf", b"%PDF-race")) for index in range(2)]
            barrier = Barrier(2)
            def worker(pk):
                close_old_connections()
                try:
                    actor = get_user_model().objects.get(pk=reviewer.pk)
                    case = SupplyReturn.objects.select_related("issue__item").get(pk=pk)
                    barrier.wait(timeout=10)
                    try:
                        service.decide_return(actor=actor, case=case, expected_version=1, action="accept", note="Observed", suitable_for_stock=True)
                        return "accepted"
                    except ValidationError:
                        return "capacity"
                finally:
                    close_old_connections()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(worker, [case.pk for case in cases]))
            self.assertCountEqual(results, ["accepted", "capacity"])
            self.assertEqual(item.on_hand, 4)
            self.assertEqual(SupplyReturn.objects.filter(status="accepted").count(), 1)
            self.assertEqual(item.movements.filter(kind="return").count(), 1)
