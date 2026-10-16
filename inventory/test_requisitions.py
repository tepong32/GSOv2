import tempfile
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from . import tests as fixtures
from .models import SupplyRequisition, SupplyFulfillment, ConsumableItem
from . import requisitions as service
from .services import record_stock_movement


class RequisitionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ConsumableStockWorkflowTests.setUpTestData.__func__(cls)
        cls.reviewer = get_user_model().objects.create_superuser(username="request-reviewer", email="review@example.test", password="test")
        cls.item = ConsumableItem.objects.create(department_id=cls.gso.pk, name="Paper", unit="ream", use_fifo=True)
        cls.second = ConsumableItem.objects.create(department_id=cls.gso.pk, name="Pens", unit="piece")
        record_stock_movement(actor=cls.actor, item=cls.item, kind="receipt", quantity="10", unit_cost="12.00")

    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.setting = override_settings(DISPOSAL_PRIVATE_ROOT=self.storage.name)
        self.setting.enable()
        self.addCleanup(self.setting.disable)
        storage_patch = patch.object(SupplyRequisition._meta.get_field("file"), "storage", FileSystemStorage(location=self.storage.name))
        storage_patch.start()
        self.addCleanup(storage_patch.stop)

    def create(self, **kwargs):
        args = dict(actor=self.actor, request_id=uuid4(), requesting_department_id=self.finance.pk,
            reference="RIS-TEST", requested_on=timezone.localdate(), purpose="Office use",
            upload=SimpleUploadedFile("approved.pdf", b"%PDF-synthetic supplied approval"),
            lines=[{"item_id": self.item.pk, "quantity": "6"}, {"item_id": self.second.pk, "quantity": "2"}])
        args.update(kwargs)
        return service.create_request(**args)

    def approve(self, request):
        return service.decide_request(actor=self.reviewer, request=request, expected_version=request.state_version,
            action="approve", note="Checked supplied approval and quantities")

    def issue(self, request, **kwargs):
        args = dict(actor=self.actor, request=request, expected_version=request.state_version,
            line_id=request.lines.get(item=self.item).pk, outcome="issued", quantity="3", recipient="Receiving clerk", note="Handed over")
        args.update(kwargs)
        return service.fulfill(**args)

    def test_partial_issue_unavailable_and_close_preserve_stock_and_lineage(self):
        request = self.create()
        self.assertEqual(self.item.on_hand, 10)
        with self.assertRaises(PermissionDenied):
            service.decide_request(actor=self.actor, request=request, expected_version=1, action="approve", note="Self review")
        with self.assertRaises(ValidationError):
            self.issue(request)
        request = self.approve(request)
        issue = self.issue(request)
        self.assertEqual(issue.movement.quantity, 3)
        self.assertEqual(issue.movement.department_id, self.finance.pk)
        self.assertEqual(issue.movement.lot_allocations.count(), 1)
        self.assertEqual(self.item.on_hand, 7)
        with self.assertRaises(ValidationError):
            self.issue(request)  # original version cannot repeat deduction
        request.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.issue(request, quantity="4")
        unavailable = self.issue(request, line_id=request.lines.get(item=self.second).pk,
            outcome="unavailable", quantity="0", recipient="", note="No pens available at check")
        self.assertIsNone(unavailable.movement_id)
        request.refresh_from_db()
        request = service.decide_request(actor=self.actor, request=request, expected_version=request.state_version,
            action="close", note="Requesting office withdrew remainder")
        self.assertEqual(request.status, "closed")
        self.assertEqual(service.issued(request.lines.get(item=self.item)), 3)
        self.assertEqual(self.item.on_hand, 7)
        service.verify_history(request)
        with self.assertRaises(ValidationError):
            self.issue(request)

    def test_completion_retry_and_transaction_rollback(self):
        identity = uuid4()
        request = self.create(request_id=identity, lines=[{"item_id": self.item.pk, "quantity": "6"}])
        self.assertEqual(self.create(request_id=identity, lines=[{"item_id": self.item.pk, "quantity": "6"}]).pk, request.pk)
        with self.assertRaises(ValidationError):
            self.create(request_id=identity, purpose="Changed", lines=[{"item_id": self.item.pk, "quantity": "6"}])
        request = self.approve(request)
        with patch("inventory.requisitions._event", side_effect=RuntimeError("simulate failed history write")):
            with self.assertRaises(RuntimeError):
                self.issue(request, quantity="6")
        self.assertEqual(self.item.on_hand, 10)
        self.assertEqual(SupplyFulfillment.objects.count(), 0)
        self.issue(request, quantity="6")
        request.refresh_from_db()
        self.assertEqual(request.status, "fulfilled")
        self.assertEqual(self.item.on_hand, 4)
        service.verify_history(request)

    def test_exact_quantity_scope_and_evidence_integrity(self):
        for quantity in ("0", "-1", "0.0001", "NaN", "Infinity"):
            with self.subTest(quantity=quantity), self.assertRaises(ValidationError):
                self.create(lines=[{"item_id": self.item.pk, "quantity": quantity}])
        with self.assertRaises(ValidationError):
            self.create(lines=[{"item_id": self.item.pk, "quantity": "1"}] * 2)
        alien = ConsumableItem.objects.create(department_id=self.finance.pk, name="Other", unit="box")
        with self.assertRaises(PermissionDenied):
            self.create(lines=[{"item_id": alien.pk, "quantity": "1"}])
        request = self.create()
        path = Path(request.file.path)
        original = path.read_bytes()
        path.write_bytes(b"changed")
        with self.assertRaises(ValidationError):
            self.approve(request)
        path.unlink()
        for _ in range(2):
            with self.assertRaises(ValidationError):
                service.verify_source(request)
        path.write_bytes(original)
        request = self.approve(request)
        SupplyRequisition.objects.filter(pk=request.pk).update(purpose="altered")
        request.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.issue(request)

    def test_http_signed_creation_review_and_issue(self):
        self.client.force_login(self.actor)
        create_url = reverse("inventory:requisition-create")
        response = self.client.get(create_url)
        self.assertContains(response, "Requested supplies")
        token = response.context["form"].initial["request_token"]
        data = {"request_token": token, "requesting_department_id": self.finance.pk, "reference": "HTTP-RIS",
            "requested_on": str(timezone.localdate()), "purpose": "Office use", "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
            "lines-0-item_id": self.item.pk, "lines-0-quantity": "6"}
        bad = self.client.post(create_url, {**data, "request_token": "tampered", "upload": SimpleUploadedFile("a.pdf", b"%PDF-http")})
        self.assertEqual(bad.status_code, 200)
        self.assertEqual(SupplyRequisition.objects.count(), 0)
        for _ in range(2):
            response = self.client.post(create_url, {**data, "upload": SimpleUploadedFile("a.pdf", b"%PDF-http")})
            self.assertEqual(response.status_code, 302)
        request = SupplyRequisition.objects.get(reference="HTTP-RIS")
        detail = reverse("inventory:requisition-detail", args=(request.pk,))
        self.assertNotContains(self.client.get(detail), "Record document review</button>")
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post(detail, {"operation": "approve", "expected_version": 1, "approve-note": "Verified supplied approval"}).status_code, 302)
        self.client.force_login(self.actor)
        post = {"operation": "issue", "expected_version": 2, "issue-line_id": request.lines.get().pk,
            "issue-outcome": "issued", "issue-quantity": "6", "issue-recipient": "Office clerk", "issue-note": "Physically handed over"}
        self.assertEqual(self.client.post(detail, post).status_code, 302)
        self.assertContains(self.client.post(detail, post), "changed")
        self.assertEqual(self.item.on_hand, 4)
        response = self.client.get(reverse("inventory:requisition-evidence", args=(request.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        b"".join(response.streaming_content)


@skipUnlessDBFeature("has_select_for_update")
class RequisitionRaceTests(TransactionTestCase):
    def test_two_issues_against_same_version_deduct_once(self):
        fixtures.ConsumableStockWorkflowTests.setUpTestData.__func__(type(self))
        reviewer = get_user_model().objects.create_superuser(username="race-reviewer", email="r@example.test", password="test")
        item = ConsumableItem.objects.create(department_id=self.gso.pk, name="Race paper", unit="ream", use_fifo=True)
        record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="10", unit_cost="1")
        with tempfile.TemporaryDirectory() as root, patch.object(SupplyRequisition._meta.get_field("file"), "storage", FileSystemStorage(location=root)):
            request = service.create_request(actor=self.actor, request_id=uuid4(), requesting_department_id=self.finance.pk,
                reference="RACE", requested_on=timezone.localdate(), purpose="Office", upload=SimpleUploadedFile("a.pdf", b"%PDF-race"),
                lines=[{"item_id": item.pk, "quantity": "6"}])
            request = service.decide_request(actor=reviewer, request=request, expected_version=1, action="approve", note="Verified")
            line = request.lines.get()
            barrier = Barrier(2)
            def worker():
                close_old_connections()
                try:
                    actor = get_user_model().objects.get(pk=self.actor.pk)
                    case = SupplyRequisition.objects.get(pk=request.pk)
                    barrier.wait(timeout=10)
                    try:
                        service.fulfill(actor=actor, request=case, expected_version=2, line_id=line.pk,
                            outcome="issued", quantity="6", recipient="Recipient", note="Physical issue")
                        return "issued"
                    except ValidationError:
                        return "stale"
                finally:
                    close_old_connections()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: worker(), range(2)))
            self.assertCountEqual(results, ["issued", "stale"])
            self.assertEqual(item.on_hand, 4)
            self.assertEqual(SupplyFulfillment.objects.count(), 1)
            request.refresh_from_db()
            service.verify_history(request)
