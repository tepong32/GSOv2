"""Replay the additive maintenance migration over populated operational history."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class MaintenanceMigrationTests(TransactionTestCase):
    def test_existing_register_and_receiving_history_survive_upgrade(self):
        before = [("inventory", "0015_portable_lifecycle_uniqueness")]
        after = [("inventory", "0016_asset_maintenance_history")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            user = apps.get_model("user", "User").objects.create(username="migration-repair", email="migration@example.test")
            Asset = apps.get_model("inventory", "Asset")
            asset = Asset.objects.create(asset_name="Existing repair flag", department_id=1,
                                          status="maintenance", assigned_office="Original", unit_cost="50000.00")
            apps.get_model("inventory", "AssetAuditEvent").objects.create(asset=asset, department_id=1,
                actor=user, action="created", snapshot={"original": "retained"})
            apps.get_model("inventory", "AssetTransfer").objects.create(asset=asset, status="accepted",
                destination_department_id=2, destination_department_label="Destination", destination_custodian="Staff",
                transfer_date=timezone.localdate(), reason="Original transfer")
            receipt = apps.get_model("inventory", "ReceivingReceipt").objects.create(department_id=1,
                department_label="GSO", supplier="Supplier", delivery_reference="Original delivery",
                delivery_date=timezone.localdate(), inspection_date=timezone.localdate(), created_by=user)
            apps.get_model("inventory", "ReceivingEvent").objects.create(receipt=receipt, actor=user,
                action="created", snapshot={"original": "receipt history"})
            snapshots = {model.__name__: list(model.objects.order_by("pk").values())
                         for model in apps.get_app_config("inventory").get_models()}
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            upgraded = executor.loader.project_state(after).apps
            for name, rows in snapshots.items():
                model = upgraded.get_model("inventory", name)
                self.assertEqual(list(model.objects.order_by("pk").values()), rows, name)
            self.assertEqual(upgraded.get_model("inventory", "AssetMaintenanceCase").objects.count(), 0)
            self.assertEqual(upgraded.get_model("inventory", "Asset").objects.get(pk=asset.pk).status, "maintenance")
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())
