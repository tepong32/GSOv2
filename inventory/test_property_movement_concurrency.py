from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Barrier, Event
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import connection, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from user.models import User

from . import property_movements as service
from .models import Asset, PropertyMovementRecord
from .test_property_movements import PropertyMovementFixture


@skipUnlessDBFeature("has_select_for_update")
class PropertyMovementConcurrencyTests(PropertyMovementFixture, TransactionTestCase):
    def competing(self, operation):
        barrier = Barrier(2)
        def run():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                operation()
                return "saved"
            except ValidationError:
                return "conflict"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(run) for _ in range(2)]
            self.assertCountEqual([job.result(timeout=30) for job in jobs], ["saved", "conflict"])

    def test_competing_records_retain_one_pending_packet_and_event(self):
        self.competing(lambda: self.record(actor=User.objects.get(pk=self.actor.pk), request_id=uuid4()))
        self.assertEqual(PropertyMovementRecord.objects.count(), 1)
        self.assertEqual(PropertyMovementRecord.objects.get().events.count(), 1)

    def test_competing_decisions_retain_one_decision(self):
        row = self.record()
        self.competing(lambda: self.decide(row, actor=User.objects.get(pk=self.reviewer.pk)))
        row.refresh_from_db()
        self.assertEqual(row.status, "verified")
        self.assertEqual(row.events.count(), 2)
        self.assertEqual(row.state_version, 2)

    def test_review_waits_for_asset_before_annotation_lock(self):
        row = self.record()
        entered = Event()
        def run():
            connections.close_all()
            try:
                def observe(execute, sql, params, many, context):
                    if "inventory_asset" in sql.lower() and "for update" in sql.lower():
                        entered.set()
                    return execute(sql, params, many, context)
                with connection.execute_wrapper(observe):
                    self.decide(row, actor=User.objects.get(pk=self.reviewer.pk))
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                Asset.objects.select_for_update().get(pk=self.asset.pk)
                job = pool.submit(run)
                self.assertTrue(entered.wait(timeout=10))
                with self.assertRaises(TimeoutError):
                    job.result(timeout=0.25)
                PropertyMovementRecord.objects.select_for_update(nowait=True).get(pk=row.pk)
            job.result(timeout=20)
        row.refresh_from_db()
        self.assertEqual(row.events.count(), 2)
