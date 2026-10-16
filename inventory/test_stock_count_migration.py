from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class StockCountMigrationTests(TransactionTestCase):
    def test_populated_ledger_and_fifo_survive_without_inventing_counts(self):
        before, after = [("inventory", "0018_witnessed_custody_returns")], [("inventory", "0019_reviewed_stock_counts")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            actor = apps.get_model("user", "User").objects.create(username="count-migration")
            item = apps.get_model("inventory", "ConsumableItem").objects.create(department_id=1, name="Historical paper", use_fifo=True)
            Movement = apps.get_model("inventory", "StockMovement")
            receipt = Movement.objects.create(item=item, kind="receipt", quantity=10, signed_quantity=10, actor=actor)
            issue = Movement.objects.create(item=item, kind="issue", quantity=3, signed_quantity=-3, actor=actor)
            lot = apps.get_model("inventory", "StockLot").objects.create(item=item, receipt=receipt, received_at=receipt.occurred_at, quantity=10)
            apps.get_model("inventory", "StockLotAllocation").objects.create(issue=issue, lot=lot, quantity=3)
            names = ("ConsumableItem", "StockMovement", "StockLot", "StockLotAllocation")
            snapshots = {name:list(apps.get_model("inventory", name).objects.order_by("pk").values()) for name in names}
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            for name in names:
                self.assertEqual(list(current.get_model("inventory", name).objects.order_by("pk").values()), snapshots[name])
            Count = current.get_model("inventory", "StockCount")
            self.assertEqual(Count.objects.count(), 0)
            data = dict(item_id=item.pk, recorded_by_id=actor.pk, counted_on=timezone.localdate(), quantity=7, basis={"balance":"7"})
            Count.objects.create(**data)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Count.objects.create(**data)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Count.objects.filter(item_id=item.pk).update(quantity=-1)
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())
