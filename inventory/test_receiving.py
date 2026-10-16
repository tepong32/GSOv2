from decimal import Decimal
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from io import StringIO
import json

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command, CommandError
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from user.models import Department, User
from .models import Asset, ConsumableItem, StockMovement, ReceivingReceipt, ReceivingEvidence
from .receiving import (create_receipt, save_receipt_line, submit_receipt,
                        update_receipt, return_receipt, void_receipt_line, attach_receipt_evidence, accept_receipt)


class ReceivingPreparationTests(TestCase):
    def setUp(self):
        self.storage = TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.settings_override = override_settings(DISPOSAL_PRIVATE_ROOT=self.storage.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.storage_patch = patch.object(ReceivingEvidence._meta.get_field("file"), "storage",
                                          FileSystemStorage(location=self.storage.name))
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    @classmethod
    def setUpTestData(cls):
        cls.office = Department.objects.create(name="General Services")
        cls.other_office = Department.objects.create(name="General Services Office")
        cls.clerk = cls.make_user("clerk", cls.office)
        cls.reviewer = cls.make_user("reviewer", cls.office)
        cls.outsider = cls.make_user("outsider", cls.other_office)
        cls.supply = ConsumableItem.objects.create(department_id=cls.office.pk, name="Paper", unit="ream")

    @classmethod
    def make_user(cls, name, office):
        user = User.objects.create_user(username=name, email=f"{name}@example.test",
            first_name=name, last_name="Synthetic", department=office)
        user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="inventory", codename__in=(
                "view_receivingreceipt", "add_receivingreceipt", "change_receivingreceipt",
                "submit_receivingreceipt", "review_receivingreceipt", "add_asset", "receive_stock")))
        return user

    def receipt(self):
        return create_receipt(actor=self.clerk, data={
            "supplier": "Synthetic vendor", "delivery_reference": "DR-1",
            "delivery_date": timezone.localdate(), "inspection_date": timezone.localdate(),
            "inspection_reference": "IAR-1", "inspector_label": "Inspector",
            "evidence_reference": "Synthetic retained inspection packet",
        })

    def line_data(self, **overrides):
        data = dict(kind="supply", description="Paper", unit="ream", supply_item=self.supply,
            delivered_quantity=Decimal("10"), accepted_quantity=Decimal("6"),
            rejected_quantity=Decimal("2"), rejection_reason="Damaged packaging")
        data.update(overrides)
        return data

    def add_line(self, receipt, **overrides):
        receipt.refresh_from_db()
        return save_receipt_line(actor=self.clerk, receipt=receipt,
            expected_version=receipt.state_version, data=self.line_data(**overrides))

    def submit(self, receipt):
        for kind in ("delivery", "inspection"):
            if not receipt.evidence.filter(kind=kind).exists():
                self.attach(receipt, kind)
        receipt.refresh_from_db()
        return submit_receipt(actor=self.clerk, receipt=receipt, expected_version=receipt.state_version)

    def attach(self, receipt, kind="delivery", actor=None):
        receipt.refresh_from_db()
        return attach_receipt_evidence(actor=actor or self.clerk, receipt=receipt,
            expected_version=receipt.state_version, kind=kind,
            upload=SimpleUploadedFile("record.pdf", b"%PDF-1.4\nsynthetic test document\n%%EOF"),
            note="Synthetic source for service tests")

    def test_partial_delivery_submission_does_not_create_stock(self):
        receipt = self.receipt()
        self.add_line(receipt)
        submitted = self.submit(receipt)
        self.assertEqual(submitted.status, "submitted")
        self.assertEqual(StockMovement.objects.count(), 0)
        self.assertEqual(Asset.objects.count(), 0)
        self.assertEqual(receipt.events.count(), 5)
        with self.assertRaises(ValidationError):
            self.add_line(receipt)

    def test_overaccepted_and_unexplained_rejection_are_rejected(self):
        receipt = self.receipt()
        for data in (self.line_data(accepted_quantity=Decimal("9")),
                     self.line_data(rejection_reason=""), self.line_data(unit="box")):
            with self.assertRaises(ValidationError):
                save_receipt_line(actor=self.clerk, receipt=receipt, expected_version=1, data=data)
        self.assertEqual(receipt.lines.count(), 0)
        self.assertEqual(receipt.events.count(), 1)

    def test_stale_edit_and_foreign_office_are_denied(self):
        receipt = self.receipt()
        self.add_line(receipt)
        with self.assertRaises(ValidationError):
            update_receipt(actor=self.clerk, receipt=receipt, expected_version=1, data={"supplier": "Wrong"})
        with self.assertRaises(PermissionDenied):
            update_receipt(actor=self.outsider, receipt=receipt, expected_version=2, data={"supplier": "Wrong"})
        receipt.refresh_from_db()
        self.assertEqual(receipt.supplier, "Synthetic vendor")

    def test_independent_return_correction_and_resubmission_preserve_history(self):
        receipt = self.receipt()
        self.add_line(receipt)
        receipt = self.submit(receipt)
        with self.assertRaises(PermissionDenied):
            return_receipt(actor=self.clerk, receipt=receipt, expected_version=receipt.state_version, reason="Self review")
        receipt = return_receipt(actor=self.reviewer, receipt=receipt, expected_version=receipt.state_version, reason="Correct delivery reference")
        receipt = update_receipt(actor=self.clerk, receipt=receipt, expected_version=receipt.state_version, data={"delivery_reference": "DR-2"})
        self.submit(receipt)
        returned = receipt.events.get(action="returned")
        self.assertEqual(returned.snapshot["header"]["delivery_reference"], "DR-1")
        self.assertEqual(returned.snapshot["review_note"], "Correct delivery reference")

    def test_void_preserves_line_and_reason_but_prevents_empty_submission(self):
        receipt = self.receipt()
        line = self.add_line(receipt)
        receipt.refresh_from_db()
        receipt = void_receipt_line(actor=self.clerk, receipt=receipt, line_id=line.pk,
            expected_version=receipt.state_version, reason="Entered on wrong receipt")
        line.refresh_from_db()
        self.assertTrue(line.is_void)
        self.assertEqual(receipt.events.get(action="line_voided").snapshot["note"], "Entered on wrong receipt")
        with self.assertRaises(ValidationError):
            self.submit(receipt)

    def test_any_preparer_is_ineligible_to_review(self):
        receipt = self.receipt()
        receipt = update_receipt(actor=self.reviewer, receipt=receipt, expected_version=1,
            data={"supplier": "Corrected vendor"})
        self.add_line(receipt)
        receipt = self.submit(receipt)
        with self.assertRaises(PermissionDenied):
            return_receipt(actor=self.reviewer, receipt=receipt, expected_version=receipt.state_version, reason="I edited it")

    def test_submission_requires_retained_documents(self):
        receipt = self.receipt()
        self.add_line(receipt)
        receipt.refresh_from_db()
        with self.assertRaisesMessage(ValidationError, "both delivery and inspection"):
            submit_receipt(actor=self.clerk, receipt=receipt, expected_version=receipt.state_version)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_corrupt_evidence_blocks_submission_and_preserves_history(self):
        receipt = self.receipt()
        self.add_line(receipt)
        document = self.attach(receipt)
        self.attach(receipt, "inspection")
        Path(document.file.path).write_bytes(b"changed synthetic bytes")
        with self.assertRaisesMessage(ValidationError, "integrity check"):
            self.submit(receipt)
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, "draft")
        with self.assertRaises(ValidationError):
            document.delete()
        with self.assertRaises(ValidationError):
            document.save()

    def test_upload_is_scoped_and_uploading_makes_reviewer_a_preparer(self):
        receipt = self.receipt()
        self.add_line(receipt)
        with self.assertRaises(PermissionDenied):
            self.attach(receipt, actor=self.outsider)
        self.assertEqual(receipt.evidence.count(), 0)
        self.attach(receipt, actor=self.reviewer)
        receipt = self.submit(receipt)
        with self.assertRaises(PermissionDenied):
            return_receipt(actor=self.reviewer, receipt=receipt,
                expected_version=receipt.state_version, reason="Cannot review own evidence")

    def test_acceptance_registers_only_accepted_quantity_and_blocks_replay(self):
        receipt = self.receipt()
        line = self.add_line(receipt)
        receipt = self.submit(receipt)
        version = receipt.state_version
        accepted = accept_receipt(actor=self.reviewer, receipt=receipt, expected_version=version, note="Checked original documents")
        line.refresh_from_db()
        self.assertEqual(accepted.status, "accepted")
        self.assertEqual(line.stock_movement.quantity, 6)
        self.assertEqual(self.supply.on_hand, 6)
        with self.assertRaises(ValidationError):
            accept_receipt(actor=self.reviewer, receipt=receipt, expected_version=version, note="Retry")
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_late_duplicate_asset_rolls_back_earlier_stock_line(self):
        receipt = self.receipt()
        self.add_line(receipt)
        receipt.refresh_from_db()
        save_receipt_line(actor=self.clerk, receipt=receipt, expected_version=receipt.state_version,
            data=dict(kind="asset", description="Laptop", unit="piece", delivered_quantity=1,
                      accepted_quantity=1, rejected_quantity=0, property_tag="TAG-1"))
        receipt = self.submit(receipt)
        Asset.objects.create(department_id=self.office.pk, asset_name="Existing", property_tag=" tag-1 ")
        with self.assertRaises(ValidationError):
            accept_receipt(actor=self.reviewer, receipt=receipt, expected_version=receipt.state_version, note="Review")
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, "submitted")
        self.assertEqual(StockMovement.objects.count(), 0)

        self.assertFalse(receipt.lines.exclude(stock_movement=None).exists())
        self.assertFalse(receipt.events.filter(action="accepted").exists())

    def test_received_asset_edits_retain_source_facts_and_allow_tagging(self):
        from .services import update_asset, create_asset
        from .forms import AssetForm
        self.reviewer.user_permissions.add(Permission.objects.get(
            content_type__app_label="inventory", codename="change_asset"))
        self.reviewer = User.objects.get(pk=self.reviewer.pk)
        receipt = self.receipt()
        receipt.refresh_from_db()
        line = save_receipt_line(actor=self.clerk, receipt=receipt,
            expected_version=receipt.state_version, data=dict(kind="asset",
                description="Laptop", unit="piece", delivered_quantity=1,
                accepted_quantity=1, rejected_quantity=0, property_tag="TAG-INITIAL", unit_cost=Decimal("25000.00")))
        receipt = self.submit(receipt)
        accept_receipt(actor=self.reviewer, receipt=receipt,
            expected_version=receipt.state_version, note="Checked source")
        line.refresh_from_db()
        asset = line.registered_asset
        events = asset.audit_events.count()
        for field, value in (("unit_cost", Decimal("1.00")), ("quantity", 2),
                             ("supplier", "Different vendor"), ("purchase_order_reference", "PO-other")):
            with self.subTest(field=field), self.assertRaisesMessage(ValidationError, "Retain the accepted receipt"):
                update_asset(actor=self.reviewer, asset=asset, data={field: value, "notes": "Must roll back"})
        asset.refresh_from_db()
        self.assertEqual(asset.audit_events.count(), events)
        self.assertEqual(asset.notes, "")
        self.assertEqual(asset.unit_cost, Decimal("25000.00"))
        update_asset(actor=self.reviewer, asset=asset, data={"unit_cost": Decimal("25000.00"),
            "quantity": 1, "supplier": asset.supplier, "purchase_order_reference": "",
            "property_tag": "TAG-RECEIVED", "notes": "Tagged after acceptance"})
        asset.refresh_from_db()
        self.assertEqual(asset.property_tag, "TAG-RECEIVED")
        self.assertEqual(asset.audit_events.count(), events + 1)
        form = AssetForm(instance=asset)
        for field in ("unit_cost", "quantity", "supplier", "purchase_order_reference"):
            self.assertTrue(form.fields[field].disabled)
        payload = {key: value for key, value in form.initial.items() if value is not None}
        payload.update(unit_cost="1.00", quantity="2", supplier="Tampered", purchase_order_reference="Forged")
        bound = AssetForm(payload, instance=asset)
        self.assertTrue(bound.is_valid(), bound.errors)
        self.assertEqual(bound.cleaned_data["unit_cost"], Decimal("25000.00"))
        self.assertEqual(bound.cleaned_data["supplier"], "Synthetic vendor")
        update_asset(actor=self.reviewer, asset=asset, data=bound.cleaned_data)
        line.refresh_from_db()
        self.assertEqual(line.unit_cost, Decimal("25000.00"))
        legacy = create_asset(actor=self.reviewer, data={"asset_name": "Legacy entry", "quantity": 1})
        update_asset(actor=self.reviewer, asset=legacy, data={"unit_cost": Decimal("12.00")})
        legacy.refresh_from_db()
        self.assertEqual(legacy.unit_cost, Decimal("12.00"))
        self.assertFalse(AssetForm(instance=legacy).fields["unit_cost"].disabled)

    def test_asset_acceptance_keeps_physical_origin_without_inventing_accounting(self):
        receipt = self.receipt()
        line = save_receipt_line(actor=self.clerk, receipt=receipt, expected_version=1,
            data=dict(kind="asset", description="Vehicle", unit="piece", delivered_quantity=1,
                      accepted_quantity=1, rejected_quantity=0, property_tag="VEH-1", asset_kind="vehicle"))
        receipt = self.submit(receipt)
        with self.assertRaises(PermissionDenied):
            accept_receipt(actor=self.clerk, receipt=receipt, expected_version=receipt.state_version, note="Self acceptance")
        accept_receipt(actor=self.reviewer, receipt=receipt, expected_version=receipt.state_version, note="Reviewed")
        line.refresh_from_db()
        asset = line.registered_asset
        self.assertEqual(asset.property_tag, "VEH-1")
        self.assertEqual(asset.inventory_class, Asset.CLASS_TRANSPORT)
        self.assertEqual(asset.coa_account_code, "")
        self.assertIsNone(asset.purchase_date)
        self.assertIsNone(asset.unit_cost)
        self.assertEqual(asset.audit_events.count(), 1)
        from .services import update_asset
        self.reviewer.user_permissions.add(Permission.objects.get(
            content_type__app_label="inventory", codename="change_asset"))
        reviewer = User.objects.get(pk=self.reviewer.pk)
        with self.assertRaises(ValidationError):
            update_asset(actor=reviewer, asset=asset, data={"unit_cost": Decimal("0.00")})

    def test_receiving_screens_and_private_download_scope(self):
        receipt = self.receipt()
        document = self.attach(receipt)
        self.client.force_login(self.clerk)
        for route, args in (("receiving-list", []), ("receiving-create", []), ("receiving-detail", [receipt.pk])):
            self.assertEqual(self.client.get(reverse(f"inventory:{route}", args=args)).status_code, 200)
        download = reverse("inventory:receiving-evidence", args=[document.pk])
        response = self.client.get(download)
        body = b"".join(response.streaming_content)
        self.assertEqual(response.status_code, 200)
        directives = {value.strip() for value in response["Cache-Control"].split(",")}
        self.assertTrue({"private", "no-store", "no-cache"}.issubset(directives))
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))
        self.assertEqual(body, b"%PDF-1.4\nsynthetic test document\n%%EOF")
        # Exhausting the test client's streaming iterator already closes it.
        # A second close emits request_finished outside the client's DB guard.
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(download).status_code, 404)
        self.assertEqual(self.client.get(reverse("inventory:receiving-detail", args=[receipt.pk])).status_code, 404)

    def test_acceptance_http_uses_service_and_handles_stale_replay(self):
        receipt = self.receipt()
        self.add_line(receipt)
        receipt = self.submit(receipt)
        self.client.force_login(self.reviewer)
        url = reverse("inventory:receiving-detail", args=[receipt.pk])
        data = {"action": "accept", "note": "Compared retained documents", "expected_version": receipt.state_version}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        response = self.client.post(url, data)
        self.assertContains(response, "This receipt changed")
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_complete_http_workflow_with_csrf_and_invalid_quantity(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.clerk)
        create_url = reverse("inventory:receiving-create")
        client.get(create_url)
        header = dict(supplier="HTTP vendor", delivery_reference="DR-HTTP",
                      delivery_date=timezone.localdate().isoformat(),
                      inspection_date=timezone.localdate().isoformat(),
                      inspection_reference="IAR-HTTP", inspector_label="Inspector",
                      evidence_reference="Retained packet")
        self.assertEqual(client.post(create_url, header).status_code, 403)
        self.assertFalse(ReceivingReceipt.objects.exists())
        header["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        self.assertEqual(client.post(create_url, header).status_code, 302)
        receipt = ReceivingReceipt.objects.get()
        url = reverse("inventory:receiving-detail", args=[receipt.pk])

        def post(action, **fields):
            receipt.refresh_from_db()
            return client.post(url, dict(action=action, expected_version=receipt.state_version,
                csrfmiddlewaretoken=client.cookies["csrftoken"].value, **fields))

        fields = dict(kind="supply", description="Paper", unit="ream", supply_item=self.supply.pk,
                      delivered_quantity="10", accepted_quantity="9", rejected_quantity="2",
                      rejection_reason="Damaged", asset_kind="equipment")
        self.assertEqual(post("line", **fields).status_code, 200)
        self.assertEqual(receipt.lines.count(), 0)
        receipt.refresh_from_db()
        self.assertEqual(receipt.state_version, 1)
        fields["accepted_quantity"] = "6"
        response = post("line", **fields)
        self.assertEqual(response.status_code, 302, response.content.decode())
        for kind in ("delivery", "inspection"):
            response = post("evidence", kind=kind, note="Original synthetic packet",
                upload=SimpleUploadedFile("source.pdf", b"%PDF-1.4\nsynthetic\n%%EOF"))
            self.assertEqual(response.status_code, 302, response.content.decode())
        self.assertEqual(post("submit").status_code, 302)
        self.assertEqual(StockMovement.objects.count(), 0)
        self.assertEqual(post("accept", note="Self review").status_code, 403)
        client.force_login(self.reviewer)
        client.get(url)
        self.assertEqual(post("return", note="Correct reference").status_code, 302)
        client.force_login(self.clerk)
        client.get(url)
        header.pop("csrfmiddlewaretoken")
        header["delivery_reference"] = "DR-CORRECTED"
        self.assertEqual(post("header", **header).status_code, 302)
        self.assertEqual(post("submit").status_code, 302)
        client.force_login(self.reviewer)
        client.get(url)
        self.assertEqual(post("accept", note="Verified packet").status_code, 302)
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, "accepted")
        self.assertEqual(self.supply.on_hand, 6)
        self.assertIsNotNone(receipt.lines.get().stock_movement_id)
        self.assertEqual(receipt.events.get(action="returned").snapshot["header"]["delivery_reference"], "DR-HTTP")

    def test_view_permission_does_not_authorize_receiving_mutations(self):
        receipt = self.receipt()
        self.add_line(receipt)
        receipt = self.submit(receipt)
        viewer = self.make_user("viewer", self.office)
        viewer.user_permissions.set(Permission.objects.filter(content_type__app_label="inventory",
                                                             codename="view_receivingreceipt"))
        self.client.force_login(viewer)
        self.assertRedirects(self.client.get(reverse("inventory:dashboard")), reverse("inventory:receiving-list"))
        url = reverse("inventory:receiving-detail", args=[receipt.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:receiving-create")).status_code, 403)
        for action in ("submit", "accept", "return"):
            self.assertEqual(self.client.post(url, dict(action=action,
                expected_version=receipt.state_version, note="Unauthorized")).status_code, 403)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_receiving_forms_have_distinct_labels_and_no_duplicate_ids(self):
        from html.parser import HTMLParser
        class IdCollector(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = []
            def handle_starttag(self, tag, attrs):
                self.ids.extend(value for key, value in attrs if key == "id" and value)
        receipt = self.receipt()
        self.client.force_login(self.clerk)
        response = self.client.get(reverse("inventory:receiving-detail", args=[receipt.pk]))
        parser = IdCollector()
        parser.feed(response.content.decode())
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertContains(response, 'for="line_kind"')
        self.assertContains(response, 'for="evidence_kind"')

    def test_failed_upload_audit_rolls_back_database_and_preserves_file_for_reconciliation(self):
        receipt = self.receipt()
        with patch("inventory.receiving._event", side_effect=RuntimeError("Synthetic audit failure")):
            with self.assertRaisesMessage(RuntimeError, "Synthetic audit failure"):
                self.attach(receipt)
        receipt.refresh_from_db()
        self.assertEqual(receipt.state_version, 1)
        self.assertFalse(receipt.evidence.exists())
        self.assertEqual(receipt.events.count(), 1)
        # Storage cannot roll back with the database. Preserve rather than silently
        # deleting possible evidence; operational reconciliation must flag this file.
        retained = [p for p in Path(self.storage.name).rglob("*") if p.is_file()]
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_bytes(), b"%PDF-1.4\nsynthetic test document\n%%EOF")
        report = StringIO()
        with self.assertRaises(CommandError):
            call_command("check_receiving_evidence", stdout=report)
        self.assertEqual(len(json.loads(report.getvalue())["unreferenced"]), 1)
        self.assertTrue(retained[0].exists())

    def test_evidence_reconciliation_distinguishes_missing_changed_and_unreferenced(self):
        receipt = self.receipt()
        delivery = self.attach(receipt)
        inspection = self.attach(receipt, "inspection")
        report = StringIO()
        call_command("check_receiving_evidence", stdout=report)
        self.assertEqual(json.loads(report.getvalue())["checked"], 2)
        Path(delivery.file.path).unlink()
        Path(inspection.file.path).write_bytes(b"Synthetic corruption")
        orphan = Path(inspection.file.path).parent / "unreferenced.pdf"
        orphan.write_bytes(b"Synthetic orphan")
        report = StringIO()
        with self.assertRaises(CommandError):
            call_command("check_receiving_evidence", stdout=report)
        result = json.loads(report.getvalue())
        self.assertEqual([item["id"] for item in result["missing"]], [delivery.pk])
        self.assertEqual([item["id"] for item in result["changed"]], [inspection.pk])
        self.assertEqual(len(result["unreferenced"]), 1)
        self.assertEqual(orphan.read_bytes(), b"Synthetic orphan")
        self.assertEqual(receipt.evidence.count(), 2)

    def test_evidence_reconciliation_rejects_paths_outside_receiving_storage(self):
        receipt = self.receipt()
        document = self.attach(receipt)
        # Simulate damaged metadata, bypassing the application's immutable save hook.
        ReceivingEvidence.objects.filter(pk=document.pk).update(file="../outside.pdf")
        report = StringIO()
        with self.assertRaises(CommandError):
            call_command("check_receiving_evidence", stdout=report)
        result = json.loads(report.getvalue())
        self.assertEqual(result["unsafe"], [{"id": document.pk, "path": "../outside.pdf"}])
        self.assertEqual(result["checked"], 0)
        self.assertEqual(len(result["unreferenced"]), 1)
