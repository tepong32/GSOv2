from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from .models import StockMovement, StockLot, StockLotAllocation
from .services import record_stock_movement, update_consumable
from . import tests as stock_tests


class StockServiceValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        stock_tests.ConsumableStockWorkflowTests.setUpTestData.__func__(cls)

    create_item = stock_tests.ConsumableStockWorkflowTests.create_item

    def test_excess_precision_is_rejected_before_any_fifo_or_ledger_write(self):
        item = self.create_item(fifo=True)
        with self.assertRaises(ValidationError):
            record_stock_movement(actor=self.actor, item=item, kind=StockMovement.RECEIPT, quantity="0.0004")
        self.assertEqual(item.movements.count(), 0)
        self.assertEqual(StockLot.objects.count(), 0)

    def test_invalid_numbers_fail_as_validation_without_partial_writes(self):
        item = self.create_item(fifo=True)
        for quantity in ("NaN", "Infinity", "not a number", None, "0", "-1", "1000000000"):
            with self.subTest(quantity=quantity), self.assertRaises(ValidationError):
                record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity=quantity)
        for cost in ("NaN", "Infinity", "bad", "-0.01", "1.001", "100000000000"):
            with self.subTest(cost=cost), self.assertRaises(ValidationError):
                record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="1", unit_cost=cost)
        self.assertEqual(item.movements.count(), 0)
        self.assertEqual(StockLot.objects.count(), 0)

    def test_adjustment_requires_reason_and_preserves_exact_fractional_quantity(self):
        item = self.create_item(fifo=True)
        for kind in ("adjustment_in", "adjustment_out"):
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                record_stock_movement(actor=self.actor, item=item, kind=kind, quantity="0.125", reason="  ")
        record_stock_movement(actor=self.actor, item=item, kind="adjustment_in", quantity="0.125", reason="Reviewed count")
        record_stock_movement(actor=self.actor, item=item, kind="adjustment_out", quantity="0.025", reason="Correction")
        self.assertEqual(item.on_hand, Decimal("0.100"))
        self.assertEqual(StockLotAllocation.objects.get().quantity, Decimal("0.025"))

    def test_partial_catalog_edit_preserves_fifo_and_validates_minimum(self):
        item = self.create_item(fifo=True)
        record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="1")
        updated = update_consumable(actor=self.actor, item=item, data={"notes": "Reviewed"})
        self.assertTrue(updated.use_fifo)
        for minimum in ("-1", "0.0001", "NaN"):
            with self.subTest(minimum=minimum), self.assertRaises(ValidationError):
                update_consumable(actor=self.actor, item=item, data={"minimum_stock": minimum})
        item.refresh_from_db()
        self.assertEqual(item.minimum_stock, Decimal("2.000"))
        self.assertEqual(item.audit_events.count(), 2)

    def test_issue_resolves_real_department_and_does_not_store_forged_label(self):
        item = self.create_item(fifo=False)
        record_stock_movement(actor=self.actor, item=item, kind="receipt", quantity="3")
        with self.assertRaises(PermissionDenied):
            record_stock_movement(actor=self.actor, item=item, kind="issue", quantity="1",
                department_id=999999, recipient="Employee")
        for department, recipient in ((None, "Employee"), (self.finance.pk, " ")):
            with self.subTest(department=department, recipient=recipient), self.assertRaises(ValidationError):
                record_stock_movement(actor=self.actor, item=item, kind="issue", quantity="1",
                    department_id=department, recipient=recipient)
        movement = record_stock_movement(actor=self.actor, item=item, kind="issue", quantity="1",
            department_id=self.finance.pk, department_label="Forged office", recipient="Receiving clerk")
        self.assertEqual(movement.department_label, self.finance.name)
        self.assertEqual(item.on_hand, Decimal("2"))
