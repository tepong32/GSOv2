from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from .models import Asset, AssetTransfer, AssetDisposalCase


class LifecycleConstraintTests(TestCase):
    def setUp(self):
        self.asset = Asset.objects.create(asset_name="Synthetic lifecycle asset", department_id=1)

    def transfer(self, status="pending"):
        return AssetTransfer.objects.create(asset=self.asset, status=status,
            destination_department_id=2, destination_department_label="Synthetic destination",
            destination_custodian="Synthetic custodian", transfer_date=timezone.localdate(), reason="Synthetic")

    def disposal(self, status="submitted"):
        return AssetDisposalCase.objects.create(asset=self.asset, status=status,
            reason="Synthetic", condition_details="Synthetic condition")

    def test_pending_transfer_uniqueness_survives_direct_writes_and_releases_on_close(self):
        first = self.transfer()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.transfer()
        first.status = "cancelled"
        first.save(update_fields=("status",))
        second = self.transfer()
        historical = self.transfer("accepted")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssetTransfer.objects.filter(pk=historical.pk).update(status="pending")
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNone(first.pending_identity_marker)
        self.assertEqual(second.pending_identity_marker, 1)
        self.assertEqual(AssetTransfer.objects.count(), 3)

    def test_all_open_disposal_states_share_one_slot_and_closed_history_is_retained(self):
        first = self.disposal()
        for status in ("submitted", "under_review", "needs_information", "authorized"):
            with self.subTest(status=status):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.disposal(status)
        first.status = "rejected"
        first.save(update_fields=("status",))
        second = self.disposal("authorized")
        historical = self.disposal("disposed")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssetDisposalCase.objects.filter(pk=historical.pk).update(status="under_review")
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNone(first.open_identity_marker)
        self.assertEqual(second.open_identity_marker, 1)
        self.assertEqual(AssetDisposalCase.objects.count(), 3)


@skipUnlessDBFeature("has_select_for_update")
class LifecycleConstraintConcurrencyTests(TransactionTestCase):
    def competing_inserts(self, model, fields):
        asset = Asset.objects.create(asset_name="Concurrent lifecycle asset", department_id=1)
        start = Barrier(2)
        def insert():
            connections.close_all()
            try:
                start.wait(timeout=10)
                model.objects.create(asset_id=asset.pk, **fields)
                return "created"
            except IntegrityError:
                return "conflict"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(insert) for _ in range(2)]
            results = [job.result(timeout=30) for job in jobs]
        self.assertCountEqual(results, ["created", "conflict"])
        self.assertEqual(model.objects.filter(asset=asset).count(), 1)

    def test_database_rejects_concurrent_pending_transfer_inserts(self):
        self.competing_inserts(AssetTransfer, dict(status="pending", destination_department_id=2,
            destination_department_label="Synthetic", destination_custodian="Synthetic",
            transfer_date=timezone.localdate(), reason="Synthetic"))

    def test_database_rejects_concurrent_open_disposal_inserts(self):
        self.competing_inserts(AssetDisposalCase, dict(status="submitted", reason="Synthetic",
                                                    condition_details="Synthetic"))


class LifecycleMigrationTests(TransactionTestCase):
    before = [("inventory", "0014_receiving_evidence")]
    after = [("inventory", "0015_portable_lifecycle_uniqueness")]

    def test_populated_upgrade_preserves_active_and_closed_history(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        try:
            apps = executor.loader.project_state(self.before).apps
            asset = apps.get_model("inventory", "Asset").objects.create(asset_name="Migration asset", department_id=1)
            transfer = apps.get_model("inventory", "AssetTransfer")
            disposal = apps.get_model("inventory", "AssetDisposalCase")
            for status in ("pending", "accepted", "cancelled"):
                transfer.objects.create(asset=asset, status=status, destination_department_id=2,
                    destination_department_label="Synthetic", destination_custodian="Synthetic",
                    transfer_date=timezone.localdate(), reason="Retain me")
            for status in ("submitted", "rejected", "disposed"):
                disposal.objects.create(asset=asset, status=status, reason="Retain me", condition_details="Original")
            snapshots = {model.__name__: list(model.objects.order_by("pk").values()) for model in (transfer, disposal)}
            executor = MigrationExecutor(connection)
            executor.migrate(self.after)
            apps = executor.loader.project_state(self.after).apps
            for name, rows in snapshots.items():
                model = apps.get_model("inventory", name)
                self.assertEqual(list(model.objects.order_by("pk").values(*rows[0].keys())), rows)
        finally:
            MigrationExecutor(connection).migrate(self.after)

    def test_native_duplicate_preflight_stops_before_schema_changes(self):
        if connection.vendor != "mysql":
            self.skipTest("Only MySQL lacked the old conditional constraint.")
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        duplicates = None
        try:
            apps = executor.loader.project_state(self.before).apps
            asset = apps.get_model("inventory", "Asset").objects.create(asset_name="Duplicate preflight", department_id=1)
            model = apps.get_model("inventory", "AssetDisposalCase")
            first = model.objects.create(asset=asset, reason="First", condition_details="Original")
            duplicates = model.objects.create(asset=asset, reason="Second", condition_details="Original")
            with self.assertRaisesMessage(RuntimeError, "Duplicate open AssetDisposalCase"):
                MigrationExecutor(connection).migrate(self.after)
            self.assertEqual(model.objects.filter(asset=asset).count(), 2)
            with connection.cursor() as cursor:
                columns = connection.introspection.get_table_description(cursor, model._meta.db_table)
            self.assertNotIn("open_identity_marker", [column.name for column in columns])
        finally:
            # Synthetic fixture cleanup only; migration itself must never deduplicate.
            if duplicates is not None:
                duplicates.delete()
            MigrationExecutor(connection).migrate(self.after)
