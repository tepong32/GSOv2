"""Portable identity and safe deployment checks; no operator database is used."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import ImproperlyConfigured, PermissionDenied, ValidationError
from django.contrib.auth.models import Permission
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse

from user.models import Department, User
from .models import Asset, ConsumableItem, StockMovement
from .services import create_asset, create_consumable, update_asset, update_consumable, record_stock_movement


class PortableIdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Department.objects.create(name="General Services")
        cls.actor = User.objects.create_superuser(
            username="identity-admin", password="synthetic-test-password",
            email="identity@example.test", first_name="Test", last_name="Admin",
        )

    def test_assets_and_supplies_keep_identity_across_edits(self):
        asset = create_asset(actor=self.actor, data={"asset_name": "Laptop"})
        item = create_consumable(actor=self.actor, data={"name": "Paper"})
        original_asset, original_item = asset.public_id, item.public_id
        update_asset(actor=self.actor, asset=asset, data={"asset_name": "Laptop corrected"})
        update_consumable(actor=self.actor, item=item, data={"name": "Paper corrected", "use_fifo": False})
        asset.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(asset.public_id, original_asset)
        self.assertEqual(item.public_id, original_item)
        self.assertNotEqual(original_asset, original_item)

    def test_exports_retain_identity_and_distinguish_zero_from_unknown_cost(self):
        import csv
        import io
        from decimal import Decimal
        asset = create_asset(actor=self.actor, data={"asset_name": "Donated item", "unit_cost": Decimal("0")})
        create_asset(actor=self.actor, data={"asset_name": "Unknown cost"})
        item = create_consumable(actor=self.actor, data={"name": "Paper"})
        movement = record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity=1, unit_cost=Decimal("0"))
        self.client.force_login(self.actor)
        response = self.client.get(reverse("inventory:asset-export"))
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(rows[0]["Asset UUID"], str(asset.public_id))
        self.assertEqual(rows[0]["Acquisition cost"], "0.00")
        self.assertEqual(rows[1]["Acquisition cost"], "")
        response = self.client.get(reverse("inventory:stock-export"))
        row = next(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(row["Supply UUID"], str(item.public_id))
        self.assertEqual(row["Movement UUID"], str(movement.public_id))
        self.assertEqual(row["Unit cost"], "0.00")

    def test_service_inputs_cannot_replace_identity_or_scope(self):
        asset = create_asset(actor=self.actor, data={"asset_name": "Laptop"})
        item = create_consumable(actor=self.actor, data={"name": "Paper"})
        for key, value in (("public_id", uuid4()), ("department_id", 999), ("created_by", None)):
            with self.subTest(field=key):
                for operation in (
                    lambda: create_asset(actor=self.actor, data={"asset_name": "X", key: value}),
                    lambda: update_asset(actor=self.actor, asset=asset, data={key: value}),
                    lambda: create_consumable(actor=self.actor, data={"name": "X", key: value}),
                    lambda: update_consumable(actor=self.actor, item=item, data={key: value}),
                ):
                    with self.assertRaises(ValidationError):
                        operation()
        self.assertEqual(Asset.objects.count(), 1)
        self.assertEqual(ConsumableItem.objects.count(), 1)
        self.assertEqual(asset.audit_events.count(), 1)
        self.assertEqual(item.audit_events.count(), 1)


class PopulatedIdentityMigrationTests(TransactionTestCase):
    def test_existing_rows_and_links_survive_backfill(self):
        old_target = [("inventory", "0011_assetaccountingimport_source_file")]
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(old_target)
            old = executor.loader.project_state(old_target).apps
            asset_ids = [old.get_model("inventory", "Asset").objects.create(
                department_id=7, asset_name=f"Historical asset {index}", property_tag="LEGACY-DUPLICATE",
            ).pk for index in range(2)]
            supply = old.get_model("inventory", "ConsumableItem").objects.create(department_id=7, name="Paper")
            movement_ids = [old.get_model("inventory", "StockMovement").objects.create(
                item_id=supply.pk, kind="receipt", quantity=2, signed_quantity=2,
            ).pk for _ in range(2)]
            MigrationExecutor(connection).migrate(latest)
            from .models import StockMovement
            self.assertEqual(list(Asset.objects.order_by("pk").values_list("pk", flat=True)), asset_ids)
            self.assertEqual(Asset.objects.filter(property_tag="LEGACY-DUPLICATE").count(), 2)
            self.assertEqual(StockMovement.objects.filter(item_id=supply.pk).count(), 2)
            self.assertEqual(list(StockMovement.objects.order_by("pk").values_list("pk", flat=True)), movement_ids)
            ids = list(Asset.objects.values_list("public_id", flat=True))
            ids += list(ConsumableItem.objects.values_list("public_id", flat=True))
            ids += list(StockMovement.objects.values_list("public_id", flat=True))
            self.assertEqual(len(ids), len(set(ids)))
            self.assertNotIn(None, ids)
            self.assertEqual(ConsumableItem.objects.get(pk=supply.pk).on_hand, 4)
        finally:
            MigrationExecutor(connection).migrate(latest)


class StockOwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gso = Department.objects.create(name="General Services")
        cls.other = Department.objects.create(name="General Services Office")
        cls.actor = User.objects.create_user(
            username="stock-clerk", password="synthetic-test-password",
            email="stock@example.test", first_name="Stock", last_name="Clerk", department=cls.gso,
        )
        cls.actor.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="inventory", codename__in=(
                "view_consumableitem", "change_consumableitem", "receive_stock", "export_stock_register", "issue_stock", "adjust_stock",
            ),
        ))
        cls.own = ConsumableItem.objects.create(department_id=cls.gso.pk, name="Own paper")
        cls.foreign = ConsumableItem.objects.create(department_id=cls.other.pk, name="Private paper")
        for item in (cls.own, cls.foreign):
            StockMovement.objects.create(item=item, kind="receipt", quantity=3, signed_quantity=3)

    def test_list_export_and_detail_enforce_owner(self):
        self.client.force_login(self.actor)
        for route in ("consumable-list", "stock-export"):
            response = self.client.get(reverse(f"inventory:{route}"))
            self.assertContains(response, "Own paper")
            self.assertNotContains(response, "Private paper")
        self.assertEqual(self.client.get(reverse("inventory:consumable-detail", args=[self.foreign.pk])).status_code, 404)
        for route in ("consumable-edit", "stock-receive", "stock-issue", "stock-adjust"):
            url = reverse(f"inventory:{route}", args=[self.foreign.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {}).status_code, 404)

    def test_services_reject_foreign_supply_even_with_action_permission(self):
        with self.assertRaises(PermissionDenied):
            update_consumable(actor=self.actor, item=self.foreign, data={"name": "Overwrite", "use_fifo": False})
        with self.assertRaises(PermissionDenied):
            record_stock_movement(actor=self.actor, item=self.foreign, kind="receipt", quantity=1)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.name, "Private paper")
        self.assertEqual(self.foreign.on_hand, 3)


class DeploymentSettingsTests(SimpleTestCase):
    def load_settings(self, **overrides):
        env = {
            "DEBUG": "0", "SKEY": "synthetic-only-production-settings-test-key-with-50-characters-123456",
            "ALLOWED_HOSTS": "inventory.example.test", "DISPOSAL_PRIVATE_ROOT": str(Path.cwd().anchor + "private-gso-test"),
        }
        env.update(overrides)
        spec = importlib.util.spec_from_file_location("isolated_gso_settings", Path(__file__).resolve().parents[1] / "src" / "settings.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"):
            spec.loader.exec_module(module)
        return module

    def test_production_requires_secret_hosts_and_private_storage(self):
        for overrides in ({"SKEY": ""}, {"SKEY": "a" * 60}, {"ALLOWED_HOSTS": "*"},
                          {"ALLOWED_HOSTS": ""}, {"DISPOSAL_PRIVATE_ROOT": ""},
                          {"DISPOSAL_PRIVATE_ROOT": str(Path(__file__).resolve().parents[1] / "media" / "private")}):
            with self.subTest(overrides=overrides), self.assertRaises(ImproperlyConfigured):
                self.load_settings(**overrides)

    def test_production_enforces_https_and_secure_cookies(self):
        settings = self.load_settings()
        self.assertTrue(settings.SECURE_SSL_REDIRECT)
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertGreater(settings.SECURE_HSTS_SECONDS, 0)
        self.assertEqual(settings.X_FRAME_OPTIONS, "DENY")

    def test_development_and_disposable_database_override(self):
        settings = self.load_settings(DEBUG="1", SKEY="", GSO_DATABASE_PATH="disposable.sqlite3")
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
        self.assertEqual(settings.DATABASES["default"]["NAME"], "disposable.sqlite3")
