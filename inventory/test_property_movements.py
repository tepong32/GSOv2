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
from django.utils import timezone
from user.models import User

from . import property_determinations as properties, property_movements as service
from .models import Asset, AssetTransfer, PropertyDetermination, PropertyMovementRecord as Record
from .test_disposal_locking import DisposalFixture


class PropertyMovementFixture(DisposalFixture):
    def setUp(self):
        super().setUp()
        self.reviewer = User.objects.create_user(username="movement-reviewer", department=self.office)
        self.outsider = User.objects.create_user(username="movement-outsider", department=self.other)
        grants = Permission.objects.filter(content_type__app_label="inventory", codename__in=(
            "view_asset", "record_property_determination", "review_property_determination",
            "record_property_movement", "review_property_movement"))
        for actor in (self.actor, self.reviewer, self.outsider):
            actor.user_permissions.add(*grants)
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        for model in (PropertyDetermination, Record):
            storage = patch.object(model._meta.get_field("file"), "storage", FileSystemStorage(location=root.name))
            storage.start()
            self.addCleanup(storage.stop)
        self.determination = self.determine()

    def determine(self):
        row = properties.record(actor=self.actor, asset=self.asset, request_id=uuid4(),
            expected_source=properties.source_basis(self.asset), expected_predecessor=None,
            data=dict(treatment="semi_expendable", reference="Classification source", source_date=timezone.localdate(),
                source_authority="Supplied determination", property_class="Equipment", fund_label="General fund",
                useful_life=None, life_unit="", life_basis="", life_start=None, expires_on=None, reason="Synthetic packet"),
            upload=self.upload())
        return properties.decide(actor=self.reviewer, row=row, expected_version=1,
            action="verify", note="Independent document check")

    def upload(self):
        return SimpleUploadedFile("source.pdf", b"%PDF-synthetic source")

    def data(self, **changes):
        data = dict(movement_date=timezone.localdate()-timedelta(days=2), within_day_order=0,
            reference="Opening source", item_number="", office_officer_label="GSO stockroom",
            stock_delta=0, opening_quantity=1, unit_cost=None, remarks="Documented end-of-day stock")
        data.update(changes)
        return data

    def record(self, **changes):
        args = dict(actor=self.actor, asset=self.asset, determination_id=self.determination.pk,
            source_kind="opening", source_id=None, request_id=uuid4(), expected_predecessor=None,
            data=self.data(), upload=self.upload())
        args.update(changes)
        if "expected_source" not in args:
            _, args["expected_source"], _ = service.source_basis(asset=args["asset"],
                determination_id=args["determination_id"], source_kind=args["source_kind"], source_id=args["source_id"])
        return service.record(**args)

    def decide(self, row, **changes):
        args = dict(actor=self.reviewer, row=row, expected_version=row.state_version,
                    action="verify", note="Checked source, chronology and stock effect")
        args.update(changes)
        return service.decide(**args)

    def handoff(self):
        return AssetTransfer.objects.create(asset=self.asset, destination_department_id=self.office.pk,
            destination_department_label=self.office.name, destination_custodian="Existing custodian",
            transfer_date=timezone.localdate()-timedelta(days=1), reason="Retained source fixture",
            reference="HANDOFF-1", status="accepted", requested_by=self.actor,
            acknowledged_by=self.reviewer, acknowledged_at=timezone.now())

class PropertyMovementTests(PropertyMovementFixture, TestCase):
    def test_opening_review_replay_and_correction_retain_original_and_asset(self):
        original = properties.source_basis(self.asset)
        identity = uuid4()
        row = self.record(request_id=identity, data=self.data(unit_cost=Decimal("12.50")))
        self.assertEqual(self.record(request_id=identity, data=self.data(unit_cost="12.50")).pk, row.pk)
        with self.assertRaises(PermissionDenied):
            self.decide(row, actor=self.actor)
        row = self.decide(row)
        service.verify_history(row)
        with self.assertRaises(ValidationError):
            self.decide(row, expected_version=1)
        second = self.record(expected_predecessor=str(row.public_id), data=self.data(opening_quantity=0))
        second = self.decide(second)
        row.refresh_from_db()
        self.assertEqual(row.status, "verified")
        self.assertEqual(row.opening_quantity, 1)
        self.assertEqual(second.predecessor_id, row.pk)
        self.assertEqual(service.latest_verified(self.asset, "opening"), second)
        self.asset.refresh_from_db()
        self.assertEqual(properties.source_basis(self.asset), original)
        self.assertFalse(self.asset.audit_events.exists())

    def test_changed_physical_source_blocks_review_but_allows_rejection(self):
        handoff = self.handoff()
        row = self.record(source_kind="handoff", source_id=handoff.pk,
            data=self.data(movement_date=handoff.transfer_date, within_day_order=1, opening_quantity=None, stock_delta=0, item_number="ITEM-1"))
        AssetTransfer.objects.filter(pk=handoff.pk).update(reference="Changed reference")
        with self.assertRaisesMessage(ValidationError, "source or predecessor changed"):
            self.decide(row)
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")
        self.assertEqual(row.events.count(), 1)
        self.assertEqual(self.decide(row, action="reject").status, "rejected")

    def test_tampered_annotation_and_source_packets_fail_closed(self):
        row = self.record()
        path = Path(row.file.path)
        original = path.read_bytes()
        path.write_bytes(b"%PDF-altered source")
        with self.assertRaisesMessage(ValidationError, "Movement evidence"):
            self.decide(row)
        path.write_bytes(original)
        Path(self.determination.file.path).unlink()
        with self.assertRaisesMessage(ValidationError, "Property evidence"):
            self.decide(row)
        self.assertEqual(self.decide(row, action="cancel", actor=self.actor).status, "cancelled")

    def test_foreign_owner_and_stale_owner_cannot_record_or_review(self):
        with self.assertRaises(PermissionDenied):
            self.record(actor=self.outsider)
        row = self.record()
        Asset.objects.filter(pk=self.asset.pk).update(department_id=self.other.pk)
        with self.assertRaises(PermissionDenied):
            self.decide(row)
        with self.assertRaises(PermissionDenied):
            self.record(expected_source=row.source_snapshot)
        self.assertEqual(row.events.count(), 1)

    def test_unacknowledged_or_foreign_source_rejected_and_pending_preserved(self):
        handoff = self.handoff()
        AssetTransfer.objects.filter(pk=handoff.pk).update(status="pending")
        with self.assertRaisesMessage(ValidationError, "acknowledged"):
            self.record(source_kind="handoff", source_id=handoff.pk)
        row = self.record()
        with self.assertRaisesMessage(ValidationError, "pending movement"):
            self.record()
        with self.assertRaises(ValidationError):
            self.record(request_id=row.public_id, data=self.data(reference="Different"))
        self.assertEqual(Record.objects.count(), 1)

    def test_projection_requires_complete_chain_and_preserves_unknown_cost(self):
        cutoff = timezone.localdate()
        self.assertIsNone(service.project(actor=self.actor, asset=self.asset, cutoff=cutoff)["balance"])
        opening = self.decide(self.record())
        first, second = self.handoff(), self.handoff()
        projection = service.project(actor=self.actor, asset=self.asset, cutoff=cutoff)
        self.assertIsNone(projection["balance"])
        self.assertTrue(any("2 confirmed" in issue for issue in projection["issues"]))
        for order, transfer in enumerate((first, second), 1):
            row = self.record(source_kind="handoff", source_id=transfer.pk,
                data=self.data(movement_date=transfer.transfer_date, within_day_order=order,
                    opening_quantity=None, stock_delta=-1 if order == 1 else 0, item_number="ITEM-1"))
            self.assertIsNone(service.project(actor=self.actor, asset=self.asset, cutoff=cutoff)["balance"])
            self.decide(row)
        projection = service.project(actor=self.actor, asset=self.asset, cutoff=cutoff)
        self.assertEqual(projection["issues"], [])
        self.assertEqual(projection["balance"], 0)
        self.assertEqual([item["balance"] for item in projection["rows"]], [0, 0])
        self.assertTrue(all(item["record"].unit_cost is None for item in projection["rows"]))
        self.assertEqual(service.project(actor=self.actor, asset=self.asset,
            cutoff=opening.movement_date)["balance"], 1)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.unit_cost, Decimal("100.00"))

    def test_projection_refuses_negative_stock_until_reviewed_successor_corrects_effect(self):
        self.decide(self.record())
        first, second = self.handoff(), self.handoff()
        for order, transfer in enumerate((first, second), 1):
            row = self.decide(self.record(source_kind="handoff", source_id=transfer.pk,
                data=self.data(movement_date=transfer.transfer_date, within_day_order=order,
                    opening_quantity=None, stock_delta=-1, item_number="ITEM-1")))
        projection = service.project(actor=self.actor, asset=self.asset, cutoff=timezone.localdate())
        self.assertIsNone(projection["balance"])
        self.assertTrue(any("outside zero or one" in issue for issue in projection["issues"]))
        corrected = self.record(source_kind="handoff", source_id=second.pk, expected_predecessor=str(row.public_id),
            data=self.data(movement_date=second.transfer_date, within_day_order=2,
                opening_quantity=None, stock_delta=0, item_number="ITEM-1"))
        self.decide(corrected)
        projection = service.project(actor=self.actor, asset=self.asset, cutoff=timezone.localdate())
        self.assertEqual(projection["balance"], 0)
        row.refresh_from_db()
        self.assertEqual(row.stock_delta, -1)
        self.assertEqual(row.status, "verified")

    def test_projection_refuses_duplicate_order_and_drift(self):
        opening = self.decide(self.record())
        first, second = self.handoff(), self.handoff()
        for transfer in (first, second):
            self.decide(self.record(source_kind="handoff", source_id=transfer.pk,
                data=self.data(movement_date=transfer.transfer_date, within_day_order=1,
                    opening_quantity=None, stock_delta=0, item_number="ITEM-1")))
        projection = service.project(actor=self.actor, asset=self.asset, cutoff=timezone.localdate())
        self.assertIsNone(projection["balance"])
        self.assertTrue(any("same date" in issue for issue in projection["issues"]))
        Path(opening.file.path).unlink()
        projection = service.project(actor=self.actor, asset=self.asset, cutoff=timezone.localdate())
        self.assertIsNone(projection["balance"])
        self.assertTrue(any("Movement evidence" in issue for issue in projection["issues"]))

    def test_cannot_backdate_a_physical_source_out_of_the_projection_window(self):
        handoff = self.handoff()
        with self.assertRaisesMessage(ValidationError, "physical source date"):
            self.record(source_kind="handoff", source_id=handoff.pk,
                data=self.data(within_day_order=1, opening_quantity=None, stock_delta=-1))
        self.assertFalse(Record.objects.exists())

    def test_changed_property_basis_and_undated_legacy_retirement_are_unresolved(self):
        self.decide(self.record())
        Asset.objects.filter(pk=self.asset.pk).update(unit_cost=Decimal("150.00"))
        projection = service.project(actor=self.actor, asset=self.asset, cutoff=timezone.localdate())
        self.assertIsNone(projection["balance"])
        self.assertTrue(any("basis changed" in issue for issue in projection["issues"]))
        Asset.objects.filter(pk=self.asset.pk).update(unit_cost=Decimal("100.00"), status="retired")
        projection = service.project(actor=self.actor, asset=self.asset, cutoff=timezone.localdate())
        self.assertIsNone(projection["balance"])
        self.assertTrue(any("no dated completed disposal" in issue for issue in projection["issues"]))
