from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class QuantityCorrectionMigrationTests(TransactionTestCase):
    def test_populated_source_rows_are_preserved_without_invented_corrections(self):
        before = [("inventory", "0028_receiving_followup_source")]
        after = [("inventory", "0029_receipt_quantity_corrections")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            user = apps.get_model("user", "User").objects.create(username="legacy-correction", password="!")
            item = apps.get_model("inventory", "ConsumableItem").objects.create(
                department_id=1, name="Legacy paper", unit="ream", use_fifo=True)
            movement = apps.get_model("inventory", "StockMovement").objects.create(item=item,
                kind="receipt", quantity=6, signed_quantity=6, unit_cost=Decimal("20"), actor=user)
            apps.get_model("inventory", "StockLot").objects.create(item=item, receipt=movement,
                received_at=movement.occurred_at, quantity=6, unit_cost=Decimal("20"))
            receipt = apps.get_model("inventory", "ReceivingReceipt").objects.create(
                department_id=1, department_label="Retained office", supplier="Retained supplier",
                delivery_reference="Retained delivery", delivery_date=date(2026, 1, 1),
                inspection_reference="Retained inspection", inspection_date=date(2026, 1, 1),
                inspector_label="Inspector", evidence_reference="Retained evidence", status="accepted", created_by=user)
            apps.get_model("inventory", "ReceivingLine").objects.create(receipt=receipt, sequence=1,
                kind="supply", description="Paper", unit="ream", delivered_quantity=6, accepted_quantity=6,
                supply_item=item, stock_movement=movement)
            apps.get_model("inventory", "Asset").objects.create(department_id=1, asset_name="Retired historical asset", status="retired")
            names = ("ConsumableItem", "StockMovement", "StockLot", "ReceivingReceipt", "ReceivingLine", "Asset")
            original = {name: list(apps.get_model("inventory", name).objects.order_by("pk").values()) for name in names}
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            for name in names:
                self.assertEqual(list(current.get_model("inventory", name).objects.order_by("pk").values()), original[name])
            self.assertEqual(current.get_model("inventory", "ReceiptQuantityCorrection").objects.count(), 0)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
