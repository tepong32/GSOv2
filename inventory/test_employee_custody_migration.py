from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class EmployeeCustodyMigrationTests(TransactionTestCase):
    def test_legacy_custodians_stay_unlinked_and_each_handoff_gets_a_distinct_uuid(self):
        before = [("inventory", "0016_asset_maintenance_history")]
        after = [("inventory", "0017_employee_custody_links")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            asset = apps.get_model("inventory", "Asset").objects.create(asset_name="Legacy asset",
                department_id=1, assigned_department_id=2, assigned_office="Do not infer an employee")
            Transfer = apps.get_model("inventory", "AssetTransfer")
            for status in ("pending", "accepted", "cancelled"):
                Transfer.objects.create(asset=asset, source_department_id=2, source_custodian="Original source",
                    destination_department_id=3, destination_department_label="Destination",
                    destination_custodian="Same display name", transfer_date=timezone.localdate(),
                    reason="Original evidence", status=status)
            original = list(Transfer.objects.order_by("pk").values())
            asset_original = apps.get_model("inventory", "Asset").objects.values().get(pk=asset.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            transferred = current.get_model("inventory", "AssetTransfer").objects.order_by("pk")
            self.assertEqual(list(transferred.values(*original[0].keys())), original)
            ids = list(transferred.values_list("public_id", flat=True))
            self.assertEqual(len(set(ids)), 3)
            self.assertNotIn(None, ids)
            self.assertFalse(transferred.filter(destination_custodian_user__isnull=False).exists())
            self.assertFalse(transferred.filter(source_custodian_user__isnull=False).exists())
            Asset = current.get_model("inventory", "Asset")
            self.assertEqual(Asset.objects.values(*asset_original.keys()).get(pk=asset.pk), asset_original)
            self.assertIsNone(Asset.objects.get(pk=asset.pk).custodian_user_id)
            self.assertEqual(Asset.objects.get(pk=asset.pk).custodian_snapshot, {})
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())
