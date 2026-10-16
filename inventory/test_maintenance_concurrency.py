from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from user.models import Department, User
from .models import Asset, AssetMaintenanceCase, AssetTransfer
from .maintenance import open_maintenance, close_maintenance, update_maintenance
from .services import create_asset_transfer


@skipUnlessDBFeature("has_select_for_update")
class MaintenanceConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.office = Department.objects.create(name="General Services")
        self.destination = Department.objects.create(name="Accounting")
        self.actor = User.objects.create_superuser(username="repair-race", password="synthetic-only",
            email="repair@example.test", first_name="Repair", last_name="Test")
        self.asset = Asset.objects.create(asset_name="Concurrent repair", department_id=self.office.pk)

    def start(self, actor):
        return open_maintenance(actor=actor, asset=self.asset,
            data={"reported_date": timezone.localdate(), "problem": "Inspect brakes"})

    def race(self, *operations):
        barrier = Barrier(len(operations))
        def run(operation):
            connections.close_all()
            try:
                actor = User.objects.get(pk=self.actor.pk)
                barrier.wait(timeout=10)
                operation(actor)
                return "written"
            except ValidationError:
                return "conflict"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            jobs = [pool.submit(run, operation) for operation in operations]
            results = [job.result(timeout=30) for job in jobs]
        self.assertCountEqual(results, ["written", "conflict"])

    def test_competing_repairs_create_one_open_case(self):
        self.race(self.start, self.start)
        self.assertEqual(AssetMaintenanceCase.objects.count(), 1)
        self.assertEqual(AssetMaintenanceCase.objects.get().events.count(), 1)

    def test_handoff_and_maintenance_cannot_both_open(self):
        def transfer(actor):
            return create_asset_transfer(actor=actor, asset=self.asset, data={
                "destination_department": self.destination.pk, "destination_custodian": "Clerk",
                "transfer_date": timezone.localdate(), "reason": "Assignment"})
        self.race(self.start, transfer)
        self.assertEqual(AssetMaintenanceCase.objects.count() + AssetTransfer.objects.count(), 1)

    def test_competing_closures_record_one_outcome(self):
        case = self.start(self.actor)
        case = update_maintenance(actor=self.actor, case=case, expected_version=1,
                                  data={"work_performed": "Inspected and tested"})
        def close(actor):
            return close_maintenance(actor=actor, case=case, expected_version=2, action="completed",
                finished_date=timezone.localdate(), note="Passed inspection", outcome="active")
        self.race(close, close)
        self.assertEqual(case.events.filter(action="completed").count(), 1)
        self.assertEqual(self.asset.audit_events.count(), 2)
