from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event, Barrier
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from user.models import Department, User
from .models import Asset, AssetDisposalCase, AssetDisposalAttachment
from . import services


class DisposalFixture:
    def setUp(self):
        super().setUp()
        self.office = Department.objects.create(name="General Services")
        self.other = Department.objects.create(name="General Services Office")
        self.actor = User.objects.create_user(username="disposal-lock", department=self.office)
        self.actor.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventory",
            codename__in=("view_asset", "review_asset_disposal", "request_asset_disposal")))
        self.asset = Asset.objects.create(asset_name="Synthetic disposal", department_id=self.office.pk,
            assigned_department_id=self.office.pk, assigned_office="Retained custodian", unit_cost="100.00")
        self.case = AssetDisposalCase.objects.create(asset=self.asset, submitted_by=self.actor,
            reason="Documented disposal", condition_details="Synthetic condition")
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        storage = patch.object(AssetDisposalAttachment._meta.get_field("file"), "storage",
            FileSystemStorage(location=root.name))
        storage.start()
        self.addCleanup(storage.stop)

    def completion(self):
        AssetDisposalCase.objects.filter(pk=self.case.pk).update(status="authorized")
        self.case.refresh_from_db()
        AssetDisposalAttachment.objects.create(disposal_case=self.case, kind="completion",
            file=SimpleUploadedFile("completion.pdf", b"%PDF-synthetic completion"),
            original_filename="completion.pdf", content_type="application/pdf", size=len(b"%PDF-synthetic completion"),
            uploaded_by=self.actor)
        return dict(action="disposed", note="Checked completion", disposal_method="destruction",
            disposal_date=timezone.localdate(), completion_reference="COMPLETION-1")


class DisposalLockingTests(DisposalFixture, TestCase):
    def test_review_and_response_recheck_locked_asset_scope(self):
        Asset.objects.filter(pk=self.asset.pk).update(department_id=self.other.pk)
        with self.assertRaises(PermissionDenied):
            services.review_asset_disposal_case(actor=self.actor, case=self.case, data={"action": "under_review"})
        AssetDisposalCase.objects.filter(pk=self.case.pk).update(status="needs_information")
        with self.assertRaises(PermissionDenied):
            services.respond_to_disposal_case(actor=self.actor, case=self.case, data={"response": "Source supplied"})
        with self.assertRaises(PermissionDenied):
            services.submit_asset_disposal_request(actor=self.actor, asset=self.asset,
                data={"photos": [object()], "signed_request": object()})
        self.assertEqual(self.case.events.count(), 0)
        self.assertEqual(AssetDisposalAttachment.objects.count(), 0)

    def test_retargeted_case_cannot_write_using_stale_asset_authority(self):
        other_asset = Asset.objects.create(asset_name="Other office", department_id=self.other.pk)
        AssetDisposalCase.objects.filter(pk=self.case.pk).update(asset=other_asset)
        with self.assertRaisesMessage(ValidationError, "disposal asset changed"):
            services.review_asset_disposal_case(actor=self.actor, case=self.case, data={"action": "under_review"})
        self.assertEqual(self.case.events.count(), 0)

    def test_completion_updates_locked_asset_once_preserving_custody_and_cost(self):
        data = self.completion()
        services.review_asset_disposal_case(actor=self.actor, case=self.case, data=data)
        with self.assertRaises(ValidationError):
            services.review_asset_disposal_case(actor=self.actor, case=self.case, data=data)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.RETIRED)
        self.assertEqual(str(self.asset.unit_cost), "100.00")
        self.assertEqual(self.asset.assigned_office, "Retained custodian")
        self.assertEqual(self.case.events.filter(action="disposed").count(), 1)
        self.assertEqual(self.asset.audit_events.filter(action="disposed").count(), 1)


@skipUnlessDBFeature("has_select_for_update_nowait")
class DisposalLockingConcurrencyTests(DisposalFixture, TransactionTestCase):
    def blocked_asset_does_not_lock_case(self, response=False):
        if response:
            AssetDisposalCase.objects.filter(pk=self.case.pk).update(status="needs_information")
        entered = Event()

        def run():
            connections.close_all()
            try:
                actor = User.objects.get(pk=self.actor.pk)
                def observe(execute, sql, params, many, context):
                    if "FOR UPDATE" in sql.upper():
                        entered.set()
                    return execute(sql, params, many, context)
                with connection.execute_wrapper(observe):
                    if response:
                        services.respond_to_disposal_case(actor=actor, case=self.case, data={"response": "Additional source"})
                    else:
                        services.review_asset_disposal_case(actor=actor, case=self.case, data={"action": "under_review"})
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                Asset.objects.select_for_update().get(pk=self.asset.pk)
                job = pool.submit(run)
                self.assertTrue(entered.wait(timeout=10))
                with self.assertRaises(TimeoutError):
                    job.result(timeout=0.25)
                # If the worker took the case first, this fails NOWAIT. The
                # asset owner must remain able to lock its case without a cycle.
                AssetDisposalCase.objects.select_for_update(nowait=True).get(pk=self.case.pk)
            job.result(timeout=20)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, "submitted" if response else "under_review")
        self.assertEqual(self.case.events.count(), 1)

    def test_review_waits_for_asset_before_locking_case(self):
        self.blocked_asset_does_not_lock_case()

    def test_resubmission_waits_for_asset_before_locking_case(self):
        self.blocked_asset_does_not_lock_case(response=True)

    def test_competing_completions_retain_one_event_and_asset_change(self):
        data = self.completion()
        barrier = Barrier(2)
        def run():
            connections.close_all()
            try:
                actor = User.objects.get(pk=self.actor.pk)
                barrier.wait(timeout=10)
                services.review_asset_disposal_case(actor=actor, case=self.case, data=data)
                return "completed"
            except ValidationError:
                return "conflict"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(run) for _ in range(2)]
            self.assertCountEqual([job.result(timeout=30) for job in jobs], ["completed", "conflict"])
        self.assertEqual(self.case.events.filter(action="disposed").count(), 1)
        self.assertEqual(self.asset.audit_events.filter(action="disposed").count(), 1)
