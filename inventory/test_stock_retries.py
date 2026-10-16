from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse

from . import tests as fixtures
from .models import ConsumableItem, StockMovement, StockLotAllocation
from .services import record_stock_movement


class StockRetryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ConsumableStockWorkflowTests.setUpTestData.__func__(cls)

    def test_repeated_stock_posts_change_balance_only_once(self):
        self.client.force_login(self.actor)
        for action, expected, data in (
            ("receive", Decimal("13"), {"quantity": "3", "reference": "DR-RETRY"}),
            ("issue", Decimal("7"), {"quantity": "3", "department": self.finance.pk,
                "recipient": "Receiving clerk", "reference": "RIS-RETRY"}),
            ("adjust", Decimal("8"), {"direction": "out", "quantity": "2", "reason": "Reviewed correction"}),
        ):
            with self.subTest(action=action):
                item = ConsumableItem.objects.create(department_id=self.gso.pk, name=f"Retry {action}", use_fifo=True)
                record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="10", unit_cost="2")
                url = reverse(f"inventory:stock-{action}", args=(item.pk,))
                response = self.client.get(url)
                data["request_token"] = response.context["form"].initial.get("request_token", "")
                self.assertEqual(self.client.post(url, data).status_code, 302)
                self.assertEqual(self.client.post(url, data).status_code, 302)
                self.assertEqual(item.on_hand, expected)
                self.assertEqual(item.movements.count(), 2)

    def test_tokens_are_required_actor_item_action_bound_and_expire(self):
        from django.contrib.auth import get_user_model
        from django.core import signing
        from .views import STOCK_REQUEST_SALT
        self.client.force_login(self.actor)
        item = ConsumableItem.objects.create(department_id=self.gso.pk, name="Token item")
        other = ConsumableItem.objects.create(department_id=self.gso.pk, name="Other token item")
        url = reverse("inventory:stock-receive", args=(item.pk,))
        response = self.client.get(url)
        self.assertIn("no-store", response["Cache-Control"])
        token = response.context["form"].initial["request_token"]
        self.assertEqual(self.client.post(url, {"quantity": "2"}).status_code, 200)
        self.assertContains(self.client.post(url, {"quantity": "2", "request_token": token + "x"}), "expired or changed")
        self.assertEqual(self.client.post(reverse("inventory:stock-receive", args=(other.pk,)),
            {"quantity": "2", "request_token": token}).status_code, 403)
        self.assertEqual(self.client.post(reverse("inventory:stock-adjust", args=(item.pk,)),
            {"quantity": "2", "direction": "in", "reason": "Changed action", "request_token": token}).status_code, 403)
        payload = signing.loads(token, salt=STOCK_REQUEST_SALT)
        with patch("django.core.signing.time.time", return_value=1):
            expired = signing.dumps(payload, salt=STOCK_REQUEST_SALT)
        self.assertContains(self.client.post(url, {"quantity": "2", "request_token": expired}), "expired or changed")
        different = get_user_model().objects.create_superuser(username="other-retry-admin", password="test-pass",
            email="other@example.test")
        self.client.force_login(different)
        self.assertEqual(self.client.post(url, {"quantity": "2", "request_token": token}).status_code, 403)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_replay_requires_identical_content_and_current_authority(self):
        item = ConsumableItem.objects.create(department_id=self.gso.pk, name="Replay content", use_fifo=True)
        identity = uuid4()
        row = record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="2", unit_cost="3",
            reference="DR-RETRY", request_id=identity)
        for changed in ({"quantity": "3"}, {"unit_cost": "4"}, {"reference": "Another request"}, {"kind": "return"}):
            data = {"kind": "receipt", "quantity": "2", "unit_cost": "3", "reference": "DR-RETRY"}
            data.update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValidationError):
                record_stock_movement(actor=self.actor, item=item, request_id=identity, **data)
        item.is_active = False
        item.save(update_fields=("is_active",))
        self.assertEqual(record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="2", unit_cost="3",
            reference="DR-RETRY", request_id=identity).pk, row.pk)
        self.assertEqual(item.lots.count(), 1)
        self.assertEqual(item.movements.count(), 1)
        with self.assertRaises(ValidationError):
            record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="1", request_id=uuid4())

    def test_failed_fifo_allocation_rolls_back_request_and_can_retry(self):
        item = ConsumableItem.objects.create(department_id=self.gso.pk, name="Rollback issue", use_fifo=True)
        record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="5", unit_cost="3")
        identity = uuid4()
        def issue():
            return record_stock_movement(actor=self.actor, item=item, kind="issue", quantity="2",
                department_id=self.finance.pk, recipient="Clerk", request_id=identity)
        with patch("inventory.services._allocate_fifo", side_effect=ValidationError("Synthetic allocation failure")):
            with self.assertRaises(ValidationError):
                issue()
        self.assertFalse(StockMovement.objects.filter(public_id=identity).exists())
        self.assertEqual(item.on_hand, 5)
        self.assertEqual(issue().pk, issue().pk)
        self.assertEqual(StockLotAllocation.objects.count(), 1)
        self.assertEqual(item.on_hand, 3)


from django.test import TransactionTestCase, skipUnlessDBFeature


@skipUnlessDBFeature("has_select_for_update")
class StockRetryRaceTests(TransactionTestCase):
    def setUp(self):
        fixtures.ConsumableStockWorkflowTests.setUpTestData.__func__(self)

    def test_duplicate_receipt_and_issue_allocate_exactly_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.contrib.auth import get_user_model
        from django.db import connections
        item = ConsumableItem.objects.create(department_id=self.gso.pk, name="Concurrent retry", use_fifo=True)
        for kind, expected in (("receipt", 5), ("issue", 0)):
            identity, barrier = uuid4(), Barrier(2)
            def run():
                connections.close_all()
                try:
                    actor = get_user_model().objects.get(pk=self.actor.pk)
                    barrier.wait(timeout=10)
                    return record_stock_movement(actor=actor, item=item, kind=kind, quantity="5",
                        department_id=self.finance.pk, recipient="Clerk", request_id=identity).pk
                finally:
                    connections.close_all()
            with ThreadPoolExecutor(max_workers=2) as executor:
                jobs = [executor.submit(run) for _ in range(2)]
                results = [job.result(timeout=30) for job in jobs]
            self.assertEqual(results[0], results[1])
            self.assertEqual(item.on_hand, expected)
        self.assertEqual(item.lots.count(), 1)
        self.assertEqual(item.movements.count(), 2)
        self.assertEqual(StockLotAllocation.objects.count(), 1)
