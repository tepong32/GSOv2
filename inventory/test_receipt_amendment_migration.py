from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class ReceiptAmendmentMigrationTests(TransactionTestCase):
    def test_populated_receipts_survive_without_inventing_amendments(self):
        before = [("inventory", "0019_reviewed_stock_counts")]
        after = [("inventory", "0020_receipt_cost_amendments")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            actor = apps.get_model("user", "User").objects.create(username="amendment-migration")
            receipt = apps.get_model("inventory", "ReceivingReceipt").objects.create(
                department_id=1, department_label="GSO", supplier="Historical vendor",
                delivery_reference="Historical receipt", delivery_date=timezone.localdate(),
                inspection_date=timezone.localdate(), created_by_id=actor.pk, status="accepted")
            line = apps.get_model("inventory", "ReceivingLine").objects.create(receipt=receipt,
                sequence=1, kind="asset", description="Historical unit", unit="unit",
                delivered_quantity=1, accepted_quantity=1, unit_cost="100.00")
            apps.get_model("inventory", "ReceivingEvent").objects.create(receipt=receipt,
                actor_id=actor.pk, action="accepted", snapshot={"original": "retained"})
            names = ("ReceivingReceipt", "ReceivingLine", "ReceivingEvent")
            snapshots = {name:list(apps.get_model("inventory", name).objects.values()) for name in names}
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            for name in names:
                self.assertEqual(list(current.get_model("inventory", name).objects.values()), snapshots[name])
            Amendment = current.get_model("inventory", "ReceiptCostAmendment")
            self.assertEqual(Amendment.objects.count(), 0)
            data = dict(line_id=line.pk, recorded_by_id=actor.pk, basis={"original": "100.00"},
                reference="Synthetic", reason="Fixture", size=1, unit_cost=50)
            Amendment.objects.create(**data)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Amendment.objects.create(**data)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Amendment.objects.filter(line_id=line.pk).update(unit_cost=-1)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
