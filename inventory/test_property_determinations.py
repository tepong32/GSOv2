from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from user.models import Department, User
from .models import Asset, PropertyDetermination as Record, PropertyDeterminationEvent as Event
from . import property_determinations as service


class PropertyDeterminationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gso = Department.objects.create(name="General Services")
        cls.other = Department.objects.create(name="General Services Office")
        permissions = Permission.objects.filter(content_type__app_label="inventory", codename__in=(
            "view_asset", "view_property_determination", "record_property_determination", "review_property_determination"))
        cls.clerk = User.objects.create_user(username="property-clerk", department=cls.gso)
        cls.reviewer = User.objects.create_user(username="property-reviewer", department=cls.gso)
        cls.outsider = User.objects.create_user(username="property-outsider", department=cls.other)
        for actor in (cls.clerk, cls.reviewer, cls.outsider):
            actor.user_permissions.add(*permissions)
        cls.asset = Asset.objects.create(department_id=cls.gso.pk, asset_name="Synthetic laptop",
            unit_cost=Decimal("60000"), property_tag="PROPERTY-1", quantity=1)

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage = patch.object(Record._meta.get_field("file"), "storage", FileSystemStorage(location=self.directory.name))
        self.storage.start()
        self.addCleanup(self.storage.stop)

    def data(self, **changes):
        data = dict(treatment="semi_expendable", reference="DOC-1", source_date=timezone.localdate(),
            source_authority="Supplied Accounting determination", property_class="Office equipment", fund_label="General fund",
            useful_life=None, life_unit="", life_basis="", life_start=None, expires_on=None,
            reason="Retain supplied determination without inferring treatment from original cost")
        data.update(changes)
        return data

    def upload(self):
        return SimpleUploadedFile("property.pdf", b"%PDF-1.4\nSynthetic determination\n%%EOF")

    def record(self, **changes):
        previous = service.latest_verified(self.asset)
        args = dict(actor=self.clerk, asset=self.asset, request_id=uuid4(), expected_source=service.source_basis(self.asset),
            expected_predecessor=str(previous.public_id) if previous else None, data=self.data(), upload=self.upload())
        args.update(changes)
        return service.record(**args)

    def decide(self, row, **changes):
        args = dict(actor=self.reviewer, row=row, expected_version=row.state_version, action="verify", note="Checked supplied facts")
        args.update(changes)
        return service.decide(**args)

    def test_supplied_treatment_unknown_life_and_successor_preserve_asset(self):
        original = service.source_basis(self.asset)
        first = self.record()
        with self.assertRaises(PermissionDenied):
            self.decide(first, actor=self.clerk)
        first = self.decide(first)
        with self.assertRaises(ValidationError):
            first.save()
        first._workflow_write = True
        first.reference = "Accidental overwrite"
        with self.assertRaises(ValidationError):
            first.save()
        first.refresh_from_db()
        first._workflow_write = False
        self.assertEqual(first.treatment, "semi_expendable")
        self.assertIsNone(first.useful_life)
        self.assertIsNone(first.expires_on)
        second = self.record(data=self.data(reference="CORRECTION", treatment="ppe", useful_life=Decimal("5.00"),
            life_unit="years", life_basis="Documented service start", life_start=timezone.localdate()))
        self.assertEqual(second.predecessor_id, first.pk)
        self.assertEqual(service.latest_verified(self.asset).pk, first.pk)
        second = self.decide(second)
        self.assertEqual(service.latest_verified(self.asset).pk, second.pk)
        first.refresh_from_db()
        self.assertEqual(first.status, "verified")
        self.assertIsNone(second.expires_on)
        self.asset.refresh_from_db()
        self.assertEqual(service.source_basis(self.asset), original)
        self.assertEqual(self.asset.audit_events.count(), 0)
        for row in (first, second):
            service.verify_history(row)
            service.verify_source(row)

    def test_exact_replay_and_pending_capacity(self):
        identity = uuid4()
        row = self.record(request_id=identity)
        replay = self.record(request_id=identity)
        self.assertEqual(replay.pk, row.pk)
        with self.assertRaises(ValidationError):
            self.record(request_id=identity, data=self.data(reference="Different"))
        with self.assertRaises(ValidationError):
            self.record()
        self.decide(row)
        self.assertEqual(self.record(request_id=identity, expected_predecessor=None).pk, row.pk)
        with self.assertRaises(ValidationError):
            self.decide(row, expected_version=1)
        self.assertEqual(Record.objects.count(), 1)
        self.assertEqual(Event.objects.count(), 2)

    def test_acquisition_facts_retain_source_and_do_not_rewrite_asset_or_old_history(self):
        original = service.source_basis(self.asset)
        old = self.decide(self.record())
        before = list(old.events.values("snapshot", "checksum"))
        self.assertTrue(set(service.ACQUISITION_DEFAULTS).isdisjoint(service.snapshot(old)))
        facts = self.data(acquisition_date=timezone.localdate(), acquisition_reference="IAR-2026-01",
                          receipt_item_number="26-01-01")
        identity = uuid4()
        row = self.record(data=facts, request_id=identity)
        replay = self.record(data=facts, request_id=identity)
        self.assertEqual(row.pk, replay.pk)
        with self.assertRaises(ValidationError):
            self.record(data={**facts, "receipt_item_number": "26-01-02"}, request_id=identity)
        row = self.decide(row)
        self.assertEqual(service.snapshot(row)["receipt_item_number"], "26-01-01")
        self.assertEqual(list(old.events.values("snapshot", "checksum")), before)
        self.asset.refresh_from_db()
        self.assertEqual(service.source_basis(self.asset), original)
        service.verify_history(old)
        service.verify_history(row)
        self.client.force_login(self.clerk)
        self.assertContains(self.client.get(reverse("inventory:property-detail", args=[row.pk])), "IAR-2026-01")
        self.assertContains(self.client.get(reverse("inventory:property-register")), "26-01-01")
        Record.objects.filter(pk=row.pk).update(receipt_item_number="Altered")
        row.refresh_from_db()
        with self.assertRaises(ValidationError):
            service.verify_history(row)

    def test_acquisition_facts_require_source_but_never_guess_unknown_date(self):
        for changes in ({"receipt_item_number": "26-01-01"}, {"acquisition_date": timezone.localdate()},
                {"acquisition_reference": "IAR", "acquisition_date": timezone.localdate()+timedelta(days=1)}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.record(data=self.data(**changes))
        row = self.record(data=self.data(acquisition_reference="Legacy IAR", receipt_item_number="Retained source number"))
        self.assertIsNone(row.acquisition_date)
        self.assertEqual(row.receipt_item_number, "Retained source number")

    def test_working_register_latest_verified_scope_and_missing_facts(self):
        first = self.decide(self.record())
        pending = self.record(data=self.data(property_class="Pending class", fund_label="Pending fund"))
        Asset.objects.create(department_id=self.gso.pk, asset_name="Undocumented group", quantity=4)
        Asset.objects.create(department_id=self.other.pk, asset_name="Private other office")
        self.client.force_login(self.clerk)
        url = reverse("inventory:property-register")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page"].paginator.count, 2)
        self.assertContains(response, "Unknown useful life")
        self.assertContains(response, "Grouped quantity needs reconciliation")
        self.assertContains(response, "awaiting review")
        self.assertNotContains(response, "Private other office")
        self.assertNotContains(response, "Pending class")
        self.assertIn("no-store", response["Cache-Control"])
        filtered = self.client.get(url, {"property_class": "Office", "fund": "General", "treatment": "semi_expendable"})
        self.assertEqual(filtered.context["page"].paginator.count, 1)
        self.assertEqual(filtered.context["rows"][0]["record"].pk, first.pk)
        self.assertEqual(self.client.get(url, {"treatment": "missing"}).context["page"].paginator.count, 1)
        self.decide(pending)
        self.assertEqual(self.client.get(url, {"property_class": "Office"}).context["page"].paginator.count, 0)
        self.assertEqual(self.client.get(url, {"property_class": "Pending"}).context["rows"][0]["record"].pk, pending.pk)

    def test_working_register_detects_drift_preserves_retired_and_denies_writes(self):
        row = self.decide(self.record())
        self.client.force_login(self.clerk)
        url = reverse("inventory:property-register")
        Asset.objects.filter(pk=self.asset.pk).update(unit_cost=None, status="retired")
        response = self.client.get(url)
        self.assertContains(response, "Asset or receipt facts changed")
        self.assertContains(response, "Register unit cost unknown")
        self.assertEqual(response.context["page"].paginator.count, 1)
        Path(row.file.path).unlink()
        self.assertContains(self.client.get(url), "Property evidence is missing")
        self.assertEqual(self.client.post(url, {"status": "verified"}).status_code, 405)
        self.assertEqual(self.client.get(url, {"treatment": "invented"}).context["page"].paginator.count, 0)
        ungranted = User.objects.create_user(username="no-property-grant", department=self.gso)
        self.client.force_login(ungranted)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).context["page"].paginator.count, 0)

    def test_validation_does_not_invent_life_dates_or_split_legacy_groups(self):
        for changes in ({"useful_life": Decimal("1.001"), "life_unit": "years", "life_basis": "Source"},
                {"useful_life": 0}, {"life_unit": "years"}, {"useful_life": 2},
                {"source_date": timezone.localdate()+timedelta(days=1)},
                {"useful_life": 1, "life_unit": "years", "life_basis": "Source", "life_start": timezone.localdate(),
                 "expires_on": timezone.localdate()-timedelta(days=1)}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.record(data=self.data(**changes))
        Asset.objects.filter(pk=self.asset.pk).update(quantity=4)
        with self.assertRaisesMessage(ValidationError, "grouped quantity"):
            self.record()
        self.assertEqual(Record.objects.count(), 0)

    def test_missing_changed_source_and_stale_basis_deny_verification_but_allow_cancel(self):
        row = self.record()
        path = Path(row.file.path)
        original = path.read_bytes()
        path.unlink()
        for _ in range(2):
            with self.assertRaises(ValidationError):
                self.decide(row)
        path.write_bytes(b"changed")
        with self.assertRaises(ValidationError):
            self.decide(row)
        path.write_bytes(original)
        Asset.objects.filter(pk=self.asset.pk).update(unit_cost=Decimal("70000"))
        with self.assertRaisesMessage(ValidationError, "source basis changed"):
            self.decide(row)
        cancelled = self.decide(row, actor=self.clerk, action="cancel", note="Source changed")
        self.assertEqual(cancelled.status, "cancelled")
        self.assertIsNone(service.latest_verified(self.asset))

    def test_history_tamper_and_event_failure_are_detected(self):
        with patch.object(service, "event", side_effect=RuntimeError("Synthetic audit failure")), self.assertRaises(RuntimeError):
            self.record()
        self.assertEqual(Record.objects.count(), 0)
        row = self.record()
        Record.objects.filter(pk=row.pk).update(reference="Changed")
        with self.assertRaises(ValidationError):
            self.decide(row)
        with self.assertRaises(ValidationError):
            row.save()
        with self.assertRaises(ValidationError):
            row.delete()

    def test_receipt_version_change_is_retained_and_rejection_allows_new_basis(self):
        from .models import ReceivingReceipt, ReceivingLine
        receipt = ReceivingReceipt.objects.create(department_id=self.gso.pk, created_by=self.clerk,
            supplier="Source vendor", delivery_reference="DR-PROPERTY", delivery_date=timezone.localdate(),
            inspection_date=timezone.localdate(), status="accepted")
        ReceivingLine.objects.create(receipt=receipt, sequence=1, kind="asset", description="Laptop", unit="piece",
            delivered_quantity=1, accepted_quantity=1, registered_asset=self.asset, unit_cost=Decimal("60000.00"))
        row = self.record()
        self.assertEqual(row.source_snapshot["receipt"]["receipt_version"], 1)
        ReceivingReceipt.objects.filter(pk=receipt.pk).update(state_version=2)
        with self.assertRaisesMessage(ValidationError, "source basis changed"):
            self.decide(row)
        rejected = self.decide(row, action="reject", note="Receipt basis requires fresh source review")
        self.assertEqual(rejected.status, "rejected")
        replacement = self.record(data=self.data(reference="DOC-REPLACEMENT"))
        self.assertEqual(replacement.source_snapshot["receipt"]["receipt_version"], 2)
        self.decide(replacement)
        row.refresh_from_db()
        self.assertEqual(row.source_snapshot["receipt"]["receipt_version"], 1)

    def test_signed_http_review_download_and_office_scope(self):
        url = reverse("inventory:property-records", args=[self.asset.pk])
        self.client.force_login(self.clerk)
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertIn("no-store", page["Cache-Control"])
        token = page.context["form"].initial["source_token"]
        payload = {key: value if value is not None else "" for key, value in self.data().items()}
        payload.update(source_token=token+"bad", upload=self.upload())
        self.assertEqual(self.client.post(url, payload).status_code, 200)
        self.assertEqual(Record.objects.count(), 0)
        payload.update(source_token=token, upload=self.upload())
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 302)
        row = Record.objects.get()
        detail = reverse("inventory:property-detail", args=[row.pk])
        self.assertNotContains(self.client.get(detail), "Verify supplied document</button>")
        self.client.force_login(self.reviewer)
        self.assertContains(self.client.get(detail), "Verify supplied document</button>")
        self.assertEqual(self.client.post(detail, {"operation": "verify", "expected_version": 1,
            "verify-note": "Checked private document"}).status_code, 302)
        self.assertEqual(self.client.post(detail, {"operation": "verify", "expected_version": 1,
            "verify-note": "Retry"}).status_code, 200)
        download = reverse("inventory:property-evidence", args=[row.pk])
        response = self.client.get(download)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.get(download).status_code, 404)
        with self.assertRaises(PermissionDenied):
            self.record(actor=self.outsider)
