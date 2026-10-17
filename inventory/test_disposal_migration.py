from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class DisposalEvidenceMigrationTests(TransactionTestCase):
    def test_populated_upgrade_retains_unknown_hash_and_original_history(self):
        before = [("inventory", "0025_property_acquisition_facts")]
        after = [("inventory", "0026_disposal_evidence_hash")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            asset = apps.get_model("inventory", "Asset").objects.create(
                department_id=1, asset_name="Legacy disposal")
            case = apps.get_model("inventory", "AssetDisposalCase").objects.create(
                asset=asset, reason="Retained", condition_details="Historical")
            evidence = apps.get_model("inventory", "AssetDisposalAttachment").objects.create(
                disposal_case=case, kind="supporting", file="inventory/disposal/legacy.pdf",
                original_filename="legacy.pdf", content_type="application/pdf", size=12)
            apps.get_model("inventory", "AssetDisposalEvent").objects.create(
                disposal_case=case, action="submitted", snapshot={"attachments": ["legacy.pdf"]})
            original = dict(apps.get_model("inventory", "AssetDisposalAttachment").objects.values().get(pk=evidence.pk))
            events = list(apps.get_model("inventory", "AssetDisposalEvent").objects.values())
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            retained = dict(current.get_model("inventory", "AssetDisposalAttachment").objects.values().get(pk=evidence.pk))
            self.assertEqual(retained.pop("sha256"), "")
            self.assertEqual(retained, original)
            self.assertEqual(list(current.get_model("inventory", "AssetDisposalEvent").objects.values()), events)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
