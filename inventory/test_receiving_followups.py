from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from . import test_receiving as fixtures
from .models import ReceivingReceipt, StockMovement
from .receiving import accept_receipt, save_receipt_line
from .receiving_followups import create_followup, remaining_quantity, source_basis
from .receipt_amendments import amendment_basis
from .property_movements import physical_date


class ReceivingFollowupTests(TestCase):
    setUp = fixtures.ReceivingPreparationTests.setUp
    setUpTestData = classmethod(fixtures.ReceivingPreparationTests.setUpTestData.__func__)
    make_user = classmethod(fixtures.ReceivingPreparationTests.make_user.__func__)
    receipt = fixtures.ReceivingPreparationTests.receipt
    line_data = fixtures.ReceivingPreparationTests.line_data
    add_line = fixtures.ReceivingPreparationTests.add_line
    submit = fixtures.ReceivingPreparationTests.submit
    attach = fixtures.ReceivingPreparationTests.attach

    def original(self):
        receipt = self.receipt()
        line = self.add_line(receipt, unit_cost=Decimal("50.00"))
        receipt = self.submit(receipt)
        accept_receipt(actor=self.reviewer, receipt=receipt,
            expected_version=receipt.state_version, note="Original inspection")
        line.refresh_from_db()
        return line

    def args(self, source, **quantities):
        return dict(actor=self.clerk, source_line_id=source.pk, request_id=uuid4(),
            expected_basis=source_basis(source), inspection={
                "inspection_reference": "FOLLOWUP-1", "inspection_date": source.receipt.inspection_date,
                "inspector_label": "Inspector", "evidence_reference": "Follow-up inspection packet"},
            quantities={"accepted_quantity": Decimal("1"), "rejected_quantity": Decimal("0"),
                        "unit_cost": Decimal("50.00"), **quantities})

    def accept(self, receipt):
        receipt = self.submit(receipt)
        return accept_receipt(actor=self.reviewer, receipt=receipt,
            expected_version=receipt.state_version, note="Independent follow-up inspection")

    def test_incremental_acceptances_retain_original_and_exact_retry(self):
        source = self.original()
        basis = source_basis(source)
        args = self.args(source)
        first = create_followup(**args)
        self.assertEqual(create_followup(**args).pk, first.pk)
        self.accept(first)
        self.assertEqual(create_followup(**args).pk, first.pk)
        second = create_followup(**self.args(source))
        self.accept(second)
        source.refresh_from_db()
        self.assertEqual(source_basis(source), basis)
        self.assertEqual(source.accepted_quantity, 6)
        self.assertEqual(remaining_quantity(source), 0)
        self.assertEqual(self.supply.on_hand, 8)
        self.assertEqual(StockMovement.objects.count(), 3)
        with self.assertRaises(ValidationError):
            create_followup(**self.args(source))

    def test_competing_drafts_cannot_overresolve_at_acceptance(self):
        source = self.original()
        first = create_followup(**self.args(source, accepted_quantity=Decimal("2")))
        second = create_followup(**self.args(source, accepted_quantity=Decimal("2")))
        second = self.submit(second)
        self.accept(first)
        with self.assertRaisesMessage(ValidationError, "remainder"):
            accept_receipt(actor=self.reviewer, receipt=second,
                expected_version=second.state_version, note="Stale competing inspection")
        second.refresh_from_db()
        self.assertEqual(second.status, second.SUBMITTED)
        self.assertEqual(self.supply.on_hand, 8)

    def test_rejected_followup_resolves_quantity_without_adding_stock(self):
        source = self.original()
        receipt = create_followup(**self.args(source, accepted_quantity=Decimal("0"),
            rejected_quantity=Decimal("2"), rejection_reason="Failed inspection"))
        self.accept(receipt)
        self.assertEqual(remaining_quantity(source), 0)
        self.assertEqual(self.supply.on_hand, 6)
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_source_drift_foreign_owner_and_reused_request_are_rejected(self):
        source = self.original()
        args = self.args(source)
        with self.assertRaises(PermissionDenied):
            create_followup(**dict(args, actor=self.outsider))
        wrong = dict(args, expected_basis={})
        with self.assertRaises(ValidationError):
            create_followup(**wrong)
        receipt = create_followup(**args)
        with self.assertRaisesMessage(ValidationError, "different content"):
            create_followup(**dict(args, inspection={**args["inspection"], "inspector_label": "Other"}))
        self.assertEqual(ReceivingReceipt.objects.count(), 2)
        receipt = self.submit(receipt)
        with self.assertRaises(PermissionDenied):
            accept_receipt(actor=self.clerk, receipt=receipt,
                expected_version=receipt.state_version, note="Self review")

    def test_followup_cannot_add_lines_or_chain_another_followup(self):
        source = self.original()
        receipt = create_followup(**self.args(source))
        from .receiving import update_receipt
        with self.assertRaisesMessage(ValidationError, "original delivery facts"):
            update_receipt(actor=self.clerk, receipt=receipt, expected_version=1,
                data={"supplier": "Unrelated supplier"})
        with self.assertRaisesMessage(ValidationError, "another item"):
            save_receipt_line(actor=self.clerk, receipt=receipt, expected_version=1,
                data=self.line_data())
        self.accept(receipt)
        child = receipt.lines.get()
        child.refresh_from_db()
        with self.assertRaises(ValidationError):
            create_followup(**self.args(child))

    def test_asset_followup_retains_delivery_but_uses_later_inspection_date(self):
        receipt = self.receipt()
        from .receiving import update_receipt
        yesterday = timezone.localdate() - timedelta(days=1)
        receipt = update_receipt(actor=self.clerk, receipt=receipt, expected_version=1,
            data={"delivery_date": yesterday, "inspection_date": yesterday})
        source = self.add_line(receipt, kind="asset", supply_item=None, description="Laptop",
            unit="piece", delivered_quantity=1, accepted_quantity=0, rejected_quantity=0,
            rejection_reason="", property_tag="LAPTOP-1")
        self.accept(receipt)
        source.refresh_from_db()
        args = self.args(source)
        args["inspection"]["inspection_date"] = timezone.localdate()
        child = self.accept(create_followup(**args))
        line = child.lines.get()
        self.assertIsNotNone(line.registered_asset_id)
        self.assertEqual(child.delivery_date, yesterday)
        basis = amendment_basis(line)
        self.assertIn("followup", basis)
        self.assertEqual(physical_date("receipt", {"physical": {"receipt": basis}}), timezone.localdate())
        self.assertEqual(source_basis(source), args["expected_basis"])

    def test_http_signed_draft_retry_and_followup_line_correction(self):
        source = self.original()
        self.client.force_login(self.clerk)
        url = reverse("inventory:receiving-followup", args=[source.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {**self.args(source)["inspection"], **self.args(source)["quantities"],
                "token": response.context["form"].initial["token"]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        child = source.followup_receipts.get()
        detail = reverse("inventory:receiving-detail", args=[child.pk])
        response = self.client.get(detail)
        self.assertContains(response, "Follow-up of an existing delivery")
        self.assertNotContains(response, "Void line")
        line = child.lines.get()
        form = response.context["line_form"]
        line_data = {name: form[name].value() or "" for name in form.fields}
        line_data.update(action="line", expected_version=child.state_version,
                         accepted_quantity="0.5", rejected_quantity="0", delivered_quantity="0.5")
        response = self.client.post(detail, line_data)
        self.assertEqual(response.status_code, 302)
        line.refresh_from_db()
        self.assertEqual(line.accepted_quantity, Decimal("0.5"))
        self.assertEqual(child.lines.count(), 1)
        self.assertEqual(self.supply.on_hand, 6)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_http_tampered_token_and_source_evidence_loss_do_not_create_draft(self):
        source = self.original()
        self.client.force_login(self.clerk)
        url = reverse("inventory:receiving-followup", args=[source.pk])
        data = {**self.args(source)["inspection"], **self.args(source)["quantities"], "token": "forged"}
        self.assertContains(self.client.post(url, data), "expired or changed")
        self.assertFalse(source.followup_receipts.exists())
        document = source.receipt.evidence.first()
        document.file.storage.delete(document.file.name)
        with self.assertRaises(ValidationError):
            create_followup(**self.args(source))
        self.assertFalse(source.followup_receipts.exists())
