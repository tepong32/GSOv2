from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class FollowupMigrationTests(TransactionTestCase):
    def test_populated_receipts_and_events_are_not_rewritten(self):
        before = [("inventory", "0027_property_movement_records")]
        after = [("inventory", "0028_receiving_followup_source")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            user = apps.get_model("user", "User").objects.create(username="legacy-receiving", password="!")
            receipt = apps.get_model("inventory", "ReceivingReceipt").objects.create(
                department_id=1, department_label="Retained office", supplier="Retained supplier",
                delivery_reference="Retained delivery", delivery_date=date(2026, 1, 1),
                inspection_reference="Retained inspection", inspection_date=date(2026, 1, 1),
                inspector_label="Retained inspector", evidence_reference="Retained reference",
                status="accepted", state_version=6, created_by=user)
            apps.get_model("inventory", "ReceivingEvent").objects.create(receipt=receipt,
                actor=user, action="accepted", snapshot={"version": 6, "legacy": "unchanged"})
            original = apps.get_model("inventory", "ReceivingReceipt").objects.values().get(pk=receipt.pk)
            history = list(apps.get_model("inventory", "ReceivingEvent").objects.values())
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            retained = current.get_model("inventory", "ReceivingReceipt").objects.values().get(pk=receipt.pk)
            self.assertIsNone(retained.pop("followup_source_id"))
            self.assertEqual(retained.pop("followup_basis"), {})
            self.assertEqual(retained, original)
            self.assertEqual(list(current.get_model("inventory", "ReceivingEvent").objects.values()), history)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
