from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from user.models import Department, User

from .models import Asset, ConsumableItem, StockLot, StockLotAllocation, StockMovement
from .services import create_consumable, record_stock_movement


class ConsumableStockWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gso = Department.objects.create(name="General Services")
        cls.finance = Department.objects.create(name="Accounting")
        cls.actor = User.objects.create_superuser(
            username="inventory-admin", password="test-pass", email="inventory@example.test",
            first_name="GSO", last_name="Staff",
        )

    def create_item(self, *, fifo):
        return create_consumable(actor=self.actor, data={
            "name": "Bond paper",
            "category": "Office supplies",
            "unit": "ream",
            "use_fifo": fifo,
            "minimum_stock": Decimal("2.000"),
            "notes": "",
        })

    def receive(self, item, quantity, *, unit_cost=None):
        return record_stock_movement(
            actor=self.actor, item=item, kind=StockMovement.RECEIPT,
            quantity=Decimal(quantity), unit_cost=unit_cost, reference="DR-01",
        )

    def test_quantity_only_is_default_and_tracks_department_issues(self):
        item = self.create_item(fifo=False)
        self.receive(item, "10.000")
        issue = record_stock_movement(
            actor=self.actor, item=item, kind=StockMovement.ISSUE,
            quantity=Decimal("3.000"), department_id=self.finance.pk,
            department_label=self.finance.name, recipient="Receiving clerk", reference="RIS-1",
        )

        self.assertEqual(item.on_hand, Decimal("7.000"))
        self.assertEqual(issue.department_label, "Accounting")
        self.assertEqual(StockLot.objects.filter(item=item).count(), 0)
        self.assertEqual(StockLotAllocation.objects.count(), 0)

    def test_fifo_issue_allocates_oldest_lots_first(self):
        item = self.create_item(fifo=True)
        first = self.receive(item, "5.000", unit_cost=Decimal("50.00"))
        second = self.receive(item, "4.000", unit_cost=Decimal("55.00"))
        issue = record_stock_movement(
            actor=self.actor, item=item, kind=StockMovement.ISSUE,
            quantity=Decimal("6.000"), department_id=self.finance.pk,
            department_label=self.finance.name, recipient="Receiving clerk",
        )

        allocations = list(issue.lot_allocations.order_by("lot_id").values_list("lot__receipt_id", "quantity"))
        self.assertEqual(allocations, [(first.pk, Decimal("5.000")), (second.pk, Decimal("1.000"))])
        self.assertEqual(item.on_hand, Decimal("3.000"))

    def test_issue_cannot_make_balance_negative(self):
        item = self.create_item(fifo=True)
        self.receive(item, "2.000")

        with self.assertRaises(ValidationError):
            record_stock_movement(
                actor=self.actor, item=item, kind=StockMovement.ISSUE,
                quantity=Decimal("3.000"), department_id=self.finance.pk,
                department_label=self.finance.name, recipient="Receiving clerk",
            )

        self.assertEqual(item.movements.count(), 1)
        self.assertEqual(item.on_hand, Decimal("2.000"))

    def test_fifo_setting_cannot_be_changed_after_first_movement(self):
        item = self.create_item(fifo=False)
        self.receive(item, "2.000")

        with self.assertRaises(ValidationError):
            from .services import update_consumable
            update_consumable(actor=self.actor, item=item, data={
                "name": item.name, "category": item.category, "unit": item.unit,
                "use_fifo": True, "minimum_stock": item.minimum_stock, "notes": item.notes,
            })

    def test_consumable_register_and_export_render_for_gso(self):
        item = self.create_item(fifo=False)
        self.receive(item, "2.000")
        self.client.force_login(self.actor)

        detail = self.client.get(reverse("inventory:consumable-detail", args=(item.pk,)))
        export = self.client.get(reverse("inventory:stock-export"))

        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Bond paper")
        self.assertEqual(export.status_code, 200)
        self.assertIn("gso-consumable-movements.csv", export["Content-Disposition"])
        self.assertEqual(self.client.get(reverse("inventory:consumable-create")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:asset-create")).status_code, 200)

    def test_asset_register_export_contains_accounting_references(self):
        Asset.objects.create(
            department_id=self.gso.pk, department_label=self.gso.name, asset_name="Office printer",
            property_tag="GSO-001", coa_account_code="1-07-05-030", coa_account_title="ICT Equipment",
            voucher_reference="DV-2026-01", journal_reference="JEV-2026-04",
        )
        self.client.force_login(self.actor)

        response = self.client.get(reverse("inventory:asset-export"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1-07-05-030")
        self.assertContains(response, "JEV-2026-04")

    def test_department_user_sees_only_their_own_supply_issues(self):
        own_item = self.create_item(fifo=False)
        other_item = create_consumable(actor=self.actor, data={
            "name": "Hand soap", "category": "Toiletries", "unit": "bottle",
            "use_fifo": False, "minimum_stock": Decimal("0"), "notes": "",
        })
        for item in (own_item, other_item):
            self.receive(item, "4.000")
        record_stock_movement(
            actor=self.actor, item=own_item, kind=StockMovement.ISSUE,
            quantity=Decimal("1"), department_id=self.finance.pk,
            department_label=self.finance.name, recipient="Accounting clerk",
        )
        other_department = Department.objects.create(name="Mayor's Office")
        record_stock_movement(
            actor=self.actor, item=other_item, kind=StockMovement.ISSUE,
            quantity=Decimal("1"), department_id=other_department.pk,
            department_label=other_department.name, recipient="Office clerk",
        )
        employee = User.objects.create_user(
            username="accounting-viewer", password="test-pass", email="viewer@example.test",
            first_name="Accounting", last_name="Viewer", department=self.finance,
        )
        permission = Permission.objects.get(content_type__app_label="inventory", codename="view_consumableitem")
        employee.user_permissions.add(permission)
        self.client.force_login(employee)

        response = self.client.get(reverse("inventory:consumable-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bond paper")
        self.assertNotContains(response, "Hand soap")
