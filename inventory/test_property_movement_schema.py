from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from .models import PropertyDetermination, PropertyMovementRecord
from .test_disposal_locking import DisposalFixture


class PropertyMovementSchemaTests(DisposalFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.determination = PropertyDetermination.objects.create(asset=self.asset,
            treatment="semi_expendable", reference="Synthetic property packet",
            source_date=timezone.localdate(), source_authority="Synthetic",
            reason="Test source relation", source_snapshot={}, file="unused.pdf", size=0,
            recorded_by=self.actor)

    def opening(self, **overrides):
        data = dict(asset=self.asset, determination=self.determination,
            source_kind="opening", source_key="opening", movement_date=timezone.localdate(),
            within_day_order=0, reference="Synthetic opening", opening_quantity=1,
            stock_delta=0, remarks="Documented end-of-day stock", source_snapshot={},
            file="unused-opening.pdf", size=0, recorded_by=self.actor)
        data.update(overrides)
        return PropertyMovementRecord.objects.create(**data)

    def test_pending_uniqueness_and_immutable_source(self):
        row = self.opening()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.opening()
        row.reference = "Overwritten source"
        with self.assertRaises(ValidationError):
            row.save()
        with self.assertRaises(ValidationError):
            row.delete()

    def test_opening_must_have_known_zero_or_one_without_physical_source(self):
        for overrides in ({"opening_quantity": None}, {"opening_quantity": 2},
                          {"stock_delta": 1}, {"within_day_order": 1}, {"disposal": self.case}):
            with self.subTest(overrides=overrides), self.assertRaises(IntegrityError), transaction.atomic():
                self.opening(**overrides)

    def test_decision_cannot_assert_same_person_review(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.opening(status="verified", decided_by=self.actor, decided_at=timezone.now())


class PropertyMovementMigrationTests(TransactionTestCase):
    def test_populated_upgrade_preserves_disposal_history_and_assigns_distinct_uuids(self):
        before = [("inventory", "0026_disposal_evidence_hash")]
        after = [("inventory", "0027_property_movement_records")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            asset = apps.get_model("inventory", "Asset").objects.create(
                department_id=1, asset_name="Historical asset")
            Case = apps.get_model("inventory", "AssetDisposalCase")
            for status in ("rejected", "disposed"):
                case = Case.objects.create(asset=asset, status=status,
                    reason="Historical", condition_details="Preserve evidence")
                apps.get_model("inventory", "AssetDisposalEvent").objects.create(
                    disposal_case=case, action=status, snapshot={"historical": status})
            cases = list(Case.objects.order_by("pk").values())
            events = list(apps.get_model("inventory", "AssetDisposalEvent").objects.values())
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            rows = list(current.get_model("inventory", "AssetDisposalCase").objects.order_by("pk").values())
            uuids = [row.pop("public_id") for row in rows]
            self.assertTrue(all(uuids))
            self.assertEqual(len(set(uuids)), 2)
            self.assertEqual(rows, cases)
            self.assertEqual(list(current.get_model("inventory", "AssetDisposalEvent").objects.values()), events)
            self.assertFalse(current.get_model("inventory", "PropertyMovementRecord").objects.exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
