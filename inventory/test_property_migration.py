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

    def test_acquisition_migration_preserves_existing_event_checksums(self):
        from inventory import property_determinations as service
        from inventory.models import PropertyDetermination
        before = [("inventory", "0024_property_determinations")]
        after = [("inventory", "0025_property_acquisition_facts")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            User = apps.get_model("user", "User")
            recorder = User.objects.create(username="acquisition-migration-recorder")
            reviewer = User.objects.create(username="acquisition-migration-reviewer")
            asset = apps.get_model("inventory", "Asset").objects.create(department_id=1,
                asset_name="Historical property", quantity=1, unit_cost=None)
            Record = apps.get_model("inventory", "PropertyDetermination")
            Event = apps.get_model("inventory", "PropertyDeterminationEvent")
            row = Record.objects.create(asset=asset, recorded_by=recorder, source_snapshot={"historical": True},
                treatment="semi_expendable", reference="OLD-DOC", source_date=timezone.localdate(),
                source_authority="Synthetic historical authority", reason="Preserve history", size=1,
                file="inventory/property-determinations/historical.pdf")
            for name, default in service.ACQUISITION_DEFAULTS.items():
                setattr(row, name, default)
            pending = service.snapshot(row)
            self.assertTrue(set(service.ACQUISITION_DEFAULTS).isdisjoint(pending))
            Event.objects.create(determination=row, actor=recorder, action="recorded", snapshot=pending,
                checksum=service.checksum({"actor": recorder.pk, "action": "recorded", "snapshot": pending}))
            row.status, row.state_version = "verified", 2
            row.decided_by, row.decided_at, row.decision_note = reviewer, timezone.now(), "Checked historical source"
            row.save()
            verified = service.snapshot(row)
            Event.objects.create(determination=row, actor=reviewer, action="verified", snapshot=verified,
                checksum=service.checksum({"actor": reviewer.pk, "action": "verified", "snapshot": verified}))
            retained_events = list(Event.objects.values())
            retained_assets = list(apps.get_model("inventory", "Asset").objects.values())
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            self.assertEqual(list(current.get_model("inventory", "PropertyDeterminationEvent").objects.values()), retained_events)
            self.assertEqual(list(current.get_model("inventory", "Asset").objects.values()), retained_assets)
            migrated = PropertyDetermination.objects.get(pk=row.pk)
            service.verify_history(migrated)
            self.assertEqual(service.snapshot(migrated), verified)
            self.assertIsNone(migrated.acquisition_date)
            self.assertEqual(migrated.receipt_item_number, "")
            with self.assertRaises(IntegrityError), transaction.atomic():
                PropertyDetermination.objects.filter(pk=row.pk).update(receipt_item_number="No source")
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
