from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class PropertyMigrationTests(TransactionTestCase):
    def test_populated_assets_survive_and_pending_constraint_is_enforced(self):
        before = [("inventory", "0023_supplyreturn_supplyreturnevent_and_more")]
        after = [("inventory", "0024_property_determinations")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            actor = apps.get_model("user", "User").objects.create(username="property-migration")
            asset = apps.get_model("inventory", "Asset").objects.create(department_id=1,
                asset_name="Legacy grouped property", quantity=3, fund_code="Historical label", unit_cost=None)
            original = list(apps.get_model("inventory", "Asset").objects.values())
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            self.assertEqual(list(current.get_model("inventory", "Asset").objects.values()), original)
            Record = current.get_model("inventory", "PropertyDetermination")
            self.assertEqual(Record.objects.count(), 0)
            data = dict(asset_id=asset.pk, recorded_by_id=actor.pk, source_snapshot={"fixture": True},
                treatment="ppe", reference="Fixture", source_date=timezone.localdate(), source_authority="Synthetic",
                reason="Constraint test", size=1)
            row = Record.objects.create(**data)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Record.objects.create(**data)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Record.objects.filter(pk=row.pk).update(useful_life=-1)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Record.objects.filter(pk=row.pk).update(status="verified", decided_by_id=actor.pk, decided_at=timezone.now())
            Record.objects.filter(pk=row.pk).update(status="cancelled")
            Record.objects.create(**data)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
