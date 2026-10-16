from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from . import test_stock_counts as service_tests
from .models import StockCount
from .services import record_stock_movement
from .stock_counts import record_count, stock_basis, decide_count


@skipUnlessDBFeature("has_select_for_update")
class StockCountRaceTests(TransactionTestCase):
    create_item = service_tests.StockCountTests.create_item

    def setUp(self):
        service_tests.StockCountTests.setUpTestData.__func__(self)
        service_tests.StockCountTests.setUp(self)

    def fresh(self, actor):
        return get_user_model().objects.get(pk=actor.pk)

    def race(self, *operations):
        barrier = Barrier(len(operations))
        def run(operation):
            connections.close_all()
            try:
                barrier.wait(timeout=15)
                return operation()
            except ValidationError:
                return "conflict"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            jobs = [pool.submit(run, operation) for operation in operations]
            return [job.result(timeout=45) for job in jobs]

    def record(self, request_id):
        return record_count(actor=self.fresh(self.actor), item=self.item, request_id=request_id,
            expected_basis=stock_basis(self.item), counted_on=timezone.localdate(), quantity="8",
            reference="COUNT-RACE", note="Counted and checked")

    def ready(self):
        count = self.record(uuid4())
        service_tests.StockCountTests.evidence(self, count)
        return count

    def approve(self, count):
        return decide_count(actor=self.fresh(self.reviewer), count=count, expected_version=2,
            action="approve", note="Checked").status

    def test_duplicate_count_requests_keep_one_case(self):
        request_id = uuid4()
        self.assertEqual(self.race(lambda: str(self.record(request_id).public_id),
            lambda: str(self.record(request_id).public_id)), [str(request_id)]*2)
        self.assertEqual(StockCount.objects.count(), 1)
        self.assertEqual(StockCount.objects.get().events.count(), 1)

    def test_duplicate_approval_creates_one_adjustment(self):
        count = self.ready()
        results = self.race(lambda: self.approve(count), lambda: self.approve(count))
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(self.item.on_hand, 8)
        self.assertEqual(self.item.movements.filter(kind="adjustment_out").count(), 1)

    def test_receipt_and_review_never_overwrite_an_intervening_movement(self):
        count = self.ready()
        results = self.race(lambda: self.approve(count), lambda: record_stock_movement(
            actor=self.fresh(self.actor), item=self.item, kind="receipt", quantity="1").kind)
        count.refresh_from_db()
        if count.status == StockCount.APPROVED:
            self.assertEqual(self.item.on_hand, 9)
            self.assertNotIn("conflict", results)
        else:
            self.assertEqual(self.item.on_hand, 11)
            self.assertIsNone(count.adjustment_id)
            self.assertEqual(results.count("conflict"), 1)
