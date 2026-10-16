from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from io import StringIO
import json
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command, CommandError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from user.models import Department, User
from .models import Asset, AssetMaintenanceCase, AssetMaintenanceEvidence, AssetTransfer, AssetDisposalCase
from .maintenance import (open_maintenance, update_maintenance, close_maintenance, attach_maintenance_evidence)
from .services import update_asset, create_asset_transfer, submit_asset_disposal_request


class AssetMaintenanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.office = Department.objects.create(name="General Services")
        cls.other = Department.objects.create(name="General Services Office")
        cls.actor = User.objects.create_user(username="maintenance", department=cls.office)
        cls.actor.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventory", codename__in=(
            "manage_assetmaintenancecase", "view_asset", "change_asset", "transfer_asset", "request_asset_disposal")))
        cls.outsider = User.objects.create_user(username="outside", department=cls.other)
        cls.outsider.user_permissions.add(Permission.objects.get(codename="manage_assetmaintenancecase"))

    def setUp(self):
        self.asset = Asset.objects.create(asset_name="Inspection vehicle", department_id=self.office.pk,
                                          assigned_department_id=self.other.pk, assigned_office="Driver",
                                          unit_cost=Decimal("800000.00"))
        self.storage = TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        storage_patch = patch.object(AssetMaintenanceEvidence._meta.get_field("file"), "storage",
                                     FileSystemStorage(location=self.storage.name))
        storage_patch.start()
        self.addCleanup(storage_patch.stop)

    def start(self):
        return open_maintenance(actor=self.actor, asset=self.asset, data={
            "reported_date": timezone.localdate(), "problem": "Brake inspection", "provider": "Municipal workshop"})

    def finish(self, case, **overrides):
        data = dict(actor=self.actor, case=case, expected_version=case.state_version,
                    action="completed", finished_date=timezone.localdate(), note="Checked by mechanic", outcome="active")
        data.update(overrides)
        return close_maintenance(**data)

    def test_work_and_completion_preserve_custody_value_and_event_history(self):
        case = self.start()
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.MAINTENANCE)
        case = update_maintenance(actor=self.actor, case=case, expected_version=1,
                                  data={"work_performed": "Adjusted brakes", "documented_cost": Decimal("0.00")})
        case = self.finish(case)
        self.asset.refresh_from_db()
        self.assertEqual((self.asset.status, self.asset.assigned_department_id, self.asset.assigned_office,
                          self.asset.unit_cost), (Asset.ACTIVE, self.other.pk, "Driver", Decimal("800000")))
        self.assertEqual(list(case.events.values_list("action", flat=True)), ["opened", "work_recorded", "completed"])
        self.assertEqual(case.events.first().snapshot["work_performed"], "")
        self.assertEqual(self.asset.audit_events.count(), 2)
        with self.assertRaises(ValidationError):
            self.finish(case)
        # Retained completed cases do not prevent the next repair.
        self.start()
        self.assertEqual(self.asset.maintenance_cases.count(), 2)

    def test_lifecycle_mutations_and_duplicate_starts_are_blocked(self):
        self.start()
        for operation in (
            lambda: self.start(),
            lambda: update_asset(actor=self.actor, asset=self.asset, data={"status": "active"}),
            lambda: create_asset_transfer(actor=self.actor, asset=self.asset, data={}),
            lambda: submit_asset_disposal_request(actor=self.actor, asset=self.asset,
                                                  data={"photos": [object()], "signed_request": object()}),
        ):
            with self.assertRaisesMessage(ValidationError, "maintenance case"):
                operation()
        self.assertEqual(self.asset.maintenance_cases.count(), 1)

    def test_scope_permissions_and_identity_fields_are_not_bypassable(self):
        case = self.start()
        with self.assertRaises(PermissionDenied):
            update_maintenance(actor=self.outsider, case=case, expected_version=1, data={"provider": "X"})
        with self.assertRaises(ValidationError):
            update_maintenance(actor=self.actor, case=case, expected_version=1, data={"asset_id": self.asset.pk})
        with self.assertRaises(ValidationError):
            update_maintenance(actor=self.actor, case=case, expected_version=0, data={"provider": "X"})
        self.actor.is_active = False
        with self.assertRaises(PermissionDenied):
            self.finish(case)

    def test_cancel_restores_prior_status_and_preserves_legacy_maintenance(self):
        self.asset.status = Asset.MAINTENANCE
        self.asset.save()
        case = self.start()
        self.finish(case, action="cancelled", outcome="", note="Duplicate paper work order")
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.MAINTENANCE)
        self.assertEqual(case.events.count(), 2)

    def test_unserviceable_completion_requires_work_and_retains_status(self):
        case = self.start()
        with self.assertRaises(ValidationError):
            self.finish(case)
        case = update_maintenance(actor=self.actor, case=case, expected_version=1,
                                  data={"work_performed": "Inspected; replacement part unavailable"})
        case = self.finish(case, outcome=Asset.MAINTENANCE)
        self.assertEqual(case.status, case.COMPLETED)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.MAINTENANCE)

    def test_cost_evidence_is_required_verified_and_retained(self):
        case = self.start()
        case = update_maintenance(actor=self.actor, case=case, expected_version=1,
                                  data={"work_performed": "Brake replacement", "documented_cost": Decimal("1200.25"),
                                        "cost_reference": "Workshop bill 18"})
        with self.assertRaises(ValidationError):
            self.finish(case)
        evidence = attach_maintenance_evidence(actor=self.actor, case=case, expected_version=2,
            upload=SimpleUploadedFile("bill.pdf", b"%PDF-1.4\nretained bill", content_type="application/pdf"),
            note="Repair bill")
        case.refresh_from_db()
        original = Path(evidence.file.path).read_bytes()
        Path(evidence.file.path).write_bytes(b"corruption")
        with self.assertRaisesMessage(ValidationError, "integrity"):
            self.finish(case)
        case.refresh_from_db()
        self.assertEqual(case.status, case.OPEN)
        Path(evidence.file.path).write_bytes(original)
        case = self.finish(case)
        self.assertEqual(case.events.last().snapshot["evidence"][0]["sha256"], evidence.sha256)
        with self.assertRaises(ValidationError):
            evidence.delete()
        with self.assertRaises(ValidationError):
            case.events.first().save()
        with self.assertRaises(ValidationError):
            case.delete()

    def test_bad_dates_costs_and_failed_events_roll_back(self):
        with self.assertRaises(ValidationError):
            open_maintenance(actor=self.actor, asset=self.asset,
                             data={"problem": "Future", "reported_date": timezone.localdate() + timedelta(days=1)})
        with patch("inventory.maintenance._record", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.start()
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.ACTIVE)
        self.assertFalse(self.asset.maintenance_cases.exists())
        case = self.start()
        for cost in (Decimal("-1"), Decimal("1.001"), Decimal("NaN"), 1.5, True):
            with self.assertRaises(ValidationError):
                update_maintenance(actor=self.actor, case=case, expected_version=1, data={"documented_cost": cost})

    def test_database_prevents_two_open_cases(self):
        self.start()
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssetMaintenanceCase.objects.create(asset=self.asset, opened_by=self.actor, prior_asset_status="active",
                                                 reported_date=timezone.localdate(), problem="Duplicate")

    def test_evidence_reconciliation_detects_loss_corruption_and_orphans_without_writes(self):
        case = self.start()
        evidence = attach_maintenance_evidence(actor=self.actor, case=case, expected_version=1,
            upload=SimpleUploadedFile("record.pdf", b"%PDF-1.4\noriginal evidence"), note="Repair inspection")
        output = StringIO()
        call_command("check_maintenance_evidence", stdout=output)
        self.assertEqual(json.loads(output.getvalue())["checked"], 1)
        path = Path(evidence.file.path)
        original = path.read_bytes()
        path.write_bytes(b"corrupted")
        orphan = path.parent / "orphan.pdf"
        orphan.write_bytes(b"%PDF-1.4\ninterrupted upload")
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("check_maintenance_evidence", stdout=output)
        report = json.loads(output.getvalue())
        self.assertEqual(report["changed"][0]["id"], evidence.pk)
        self.assertEqual(len(report["unreferenced"]), 1)
        self.assertEqual(path.read_bytes(), b"corrupted")
        self.assertTrue(orphan.exists())
        path.unlink()
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("check_maintenance_evidence", stdout=output)
        self.assertEqual(json.loads(output.getvalue())["missing"][0]["id"], evidence.pk)
        # Restore synthetic evidence and quarantine the synthetic unreferenced file.
        path.write_bytes(original)
        orphan.rename(Path(self.storage.name) / "quarantined.pdf")
        call_command("check_maintenance_evidence", stdout=StringIO())
        self.assertEqual(case.events.count(), 2)

    def test_existing_handoff_disposal_and_retirement_prevent_start(self):
        transfer = AssetTransfer.objects.create(asset=self.asset, destination_department_id=self.other.pk,
            destination_department_label=self.other.name, destination_custodian="Driver", transfer_date=timezone.localdate(),
            reason="Handoff", requested_by=self.actor)
        with self.assertRaises(ValidationError):
            self.start()
        transfer.status = AssetTransfer.CANCELLED
        transfer.save()
        disposal = AssetDisposalCase.objects.create(asset=self.asset, reason="Unserviceable", condition_details="Damaged",
                                                     submitted_by=self.actor)
        with self.assertRaises(ValidationError):
            self.start()
        disposal.status = AssetDisposalCase.REJECTED
        disposal.save()
        self.asset.status = Asset.RETIRED
        self.asset.save()
        with self.assertRaises(ValidationError):
            self.start()

    def test_staff_http_flow_and_closed_record_are_read_only(self):
        self.client.force_login(self.actor)
        response = self.client.post(reverse("inventory:maintenance-open", args=(self.asset.pk,)), {
            "reported_date": timezone.localdate().isoformat(), "problem": "Inspection", "provider": "Workshop"})
        case = self.asset.maintenance_cases.get()
        url = reverse("inventory:maintenance-detail", args=(case.pk,))
        self.assertRedirects(response, url)
        response = self.client.post(url, {"operation": "work", "expected_version": 1,
            "work-reported_date": timezone.localdate().isoformat(), "work-problem": "Inspection",
            "work-provider": "Workshop", "work-work_performed": "Checked brakes", "work-documented_cost": "0.00"})
        self.assertRedirects(response, url)
        response = self.client.post(url, {"operation": "close", "expected_version": 2,
            "close-action": "completed", "close-finished_date": timezone.localdate().isoformat(),
            "close-note": "Returned to service after testing", "close-outcome": "active"})
        self.assertRedirects(response, url)
        detail = self.client.get(url)
        self.assertContains(detail, "Returned to service after testing")
        self.assertNotContains(detail, "Save work details")
        self.assertIn("no-store", detail["Cache-Control"])
        self.assertContains(self.client.get(reverse("inventory:asset-detail", args=(self.asset.pk,))), "Maintenance history")
        self.assertContains(self.client.get(reverse("inventory:dashboard")), "Open maintenance")
        self.assertContains(self.client.get(reverse("inventory:maintenance-list") + "?status=completed"), "Inspection vehicle")

    def test_http_scope_readonly_grants_download_headers_and_csrf(self):
        case = self.start()
        evidence = attach_maintenance_evidence(actor=self.actor, case=case, expected_version=1,
            upload=SimpleUploadedFile("check.pdf", b"%PDF-1.4\ninspection"), note="Inspection")
        url = reverse("inventory:maintenance-detail", args=(case.pk,))
        download = reverse("inventory:maintenance-evidence", args=(evidence.pk,))
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(download).status_code, 404)
        self.client.force_login(self.actor)
        response = self.client.get(download)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment", response["Content-Disposition"])
        # Consume through the test client's wrapper; direct close emits the request
        # signal outside that wrapper and closes MySQL's enclosing test transaction.
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4\ninspection")
        viewer = User.objects.create_user(username="maintenance-reader", department=self.office)
        viewer.user_permissions.add(Permission.objects.get(codename="view_assetmaintenancecase"))
        self.client.force_login(viewer)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"operation": "close"}).status_code, 403)
        self.assertEqual(self.client.post(download).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.actor)
        self.assertEqual(secure.post(url, {"operation": "close"}).status_code, 403)
