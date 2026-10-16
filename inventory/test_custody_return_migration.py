from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class CustodyReturnMigrationTests(TransactionTestCase):
    def test_populated_custody_history_is_preserved_without_inventing_returns(self):
        before = [("inventory", "0017_employee_custody_links")]
        after = [("inventory", "0018_witnessed_custody_returns")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            user = apps.get_model("user", "User").objects.create(username="historical-custodian")
            asset = apps.get_model("inventory", "Asset").objects.create(asset_name="Recorded custody", department_id=1,
                assigned_department_id=2, assigned_office="Recorded employee", custodian_user_id=user.pk,
                custodian_snapshot={"user_local_id": user.pk, "username": user.username})
            Transfer = apps.get_model("inventory", "AssetTransfer")
            for status in ("pending", "accepted", "cancelled"):
                Transfer.objects.create(asset=asset, destination_custodian_user_id=user.pk,
                    destination_department_id=2, destination_custodian="Recorded employee", reason="Existing evidence",
                    transfer_date=timezone.localdate(), status=status)
            old_asset = apps.get_model("inventory", "Asset").objects.values().get(pk=asset.pk)
            old_transfers = list(Transfer.objects.order_by("pk").values())
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            Asset = current.get_model("inventory", "Asset")
            Transfer = current.get_model("inventory", "AssetTransfer")
            self.assertEqual(Asset.objects.values(*old_asset.keys()).get(pk=asset.pk), old_asset)
            self.assertIsNone(Asset.objects.get(pk=asset.pk).last_custody_return_id)
            self.assertEqual(list(Transfer.objects.order_by("pk").values(*old_transfers[0].keys())), old_transfers)
            self.assertEqual(Transfer.objects.filter(kind="handoff", state_version=1, return_condition="").count(), 3)
            self.assertEqual(current.get_model("inventory", "AssetReturnEvent").objects.count(), 0)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Transfer.objects.filter(status="accepted").update(kind="return")
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())
