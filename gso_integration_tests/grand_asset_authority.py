"""Legacy register workflows obey GRAND explicit grants and UAT boundaries."""
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from inventory import access, services
from inventory.models import Asset, AssetDisposalCase, AssetTransfer, AssetVerificationRound
from inventory.maintenance_views import can_view_maintenance
from . import grand_maintenance


class GrandAssetAuthorityTests(TestCase):
    databases = {"default", "finance"}

    @classmethod
    def setUpTestData(cls):
        grand_maintenance.GrandMaintenanceTests.setUpTestData.__func__(cls)
        permissions = Permission.objects.filter(content_type__app_label="inventory")
        for actor in (cls.clerk, cls.outsider, cls.viewer):
            actor.user_permissions.add(*permissions)

    def test_explicit_grants_and_uat_override_all_legacy_writes(self):
        checks = [lambda u: access.can(u, "add"), lambda u: access.can(u, "change"),
            access.can_transfer_asset, access.can_acknowledge_asset_transfer,
            access.can_request_asset_disposal, access.can_review_asset_disposal]
        checks += [lambda u, action=a: access.can_manage_asset_verification(u, action)
                   for a in ("start", "record", "close", "import")]
        for actor in (self.super_no_grant, self.viewer):
            for index, check in enumerate(checks):
                with self.subTest(actor=actor.username, check=index):
                    self.assertFalse(check(actor))
        self.assertFalse(access.can(self.super_no_grant, "view"))
        self.assertFalse(access.can_view_audit(self.super_no_grant))
        self.assertFalse(can_view_maintenance(self.super_no_grant))
        self.assertTrue(access.can(self.viewer, "view"))
        self.assertTrue(access.can_view_audit(self.viewer))
        self.assertTrue(can_view_maintenance(self.viewer))

    def test_denied_services_leave_register_custody_and_finance_unchanged(self):
        case = AssetDisposalCase.objects.create(asset=self.asset, submitted_by=self.clerk,
            reason="Synthetic", condition_details="Inspection required")
        before = services.asset_snapshot(self.asset)
        with CaptureQueriesContext(connections["finance"]) as finance:
            for actor in (self.super_no_grant, self.viewer):
                operations = [
                    lambda: services.create_asset(actor=actor, data={"asset_name": "Denied"}),
                    lambda: services.update_asset(actor=actor, asset=self.asset, data={"asset_name": "Denied"}),
                    lambda: services.create_asset_transfer(actor=actor, asset=self.asset, data={}),
                    lambda: services.submit_asset_disposal_request(actor=actor, asset=self.asset, data={}),
                    lambda: services.review_asset_disposal_case(actor=actor, case=case, data={}),
                    lambda: services.start_asset_verification_round(actor=actor, title="Denied", as_of_date=timezone.localdate()),
                ]
                for index, operation in enumerate(operations):
                    with self.subTest(actor=actor.username, operation=index), self.assertRaises(PermissionDenied):
                        operation()
        self.asset.refresh_from_db()
        self.assertEqual(services.asset_snapshot(self.asset), before)
        self.assertEqual(Asset.objects.count(), 1)
        self.assertEqual(AssetTransfer.objects.count(), 0)
        self.assertEqual(AssetVerificationRound.objects.count(), 0)
        self.assertEqual(case.events.count(), 0)
        self.assertEqual(len(finance), 0)

    def test_scoped_history_read_only_controls_and_post_denials(self):
        count = services.start_asset_verification_round(actor=self.clerk, title="Authority count", as_of_date=timezone.localdate())
        case = AssetDisposalCase.objects.create(asset=self.asset, submitted_by=self.clerk,
            reason="Synthetic", condition_details="Inspection required")
        self.client.force_login(self.viewer)
        for name, args in (("asset-list", []), ("asset-detail", [self.asset.pk]),
            ("asset-transfer-list", []), ("asset-disposal-list", []),
            ("asset-disposal-detail", [case.pk]), ("asset-verification-list", []),
            ("asset-verification-detail", [count.pk]), ("asset-verification-reconcile", [count.pk])):
            with self.subTest(read=name):
                response = self.client.get(reverse("inventory:"+name, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "Save review")
        for name, args in (("asset-create", []), ("asset-edit", [self.asset.pk]),
            ("asset-transfer-create", [self.asset.pk]), ("asset-disposal-request", [self.asset.pk]),
            ("asset-disposal-detail", [case.pk]), ("asset-verification-list", []),
            ("asset-verification-detail", [count.pk]), ("asset-verification-reconcile", [count.pk])):
            with self.subTest(write=name):
                self.assertEqual(self.client.post(reverse("inventory:"+name, args=args), {}).status_code, 403)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse("inventory:asset-detail", args=[self.asset.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("inventory:asset-verification-detail", args=[count.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("inventory:asset-disposal-detail", args=[case.pk])).status_code, 404)
        self.assertEqual(AssetVerificationRound.objects.count(), 1)
        count.refresh_from_db()
        self.assertIsNone(count.closed_at)

    def test_granted_asset_edit_and_legacy_handoff_preserve_finance(self):
        with CaptureQueriesContext(connections["finance"]) as finance:
            asset = services.create_asset(actor=self.clerk, data={"asset_name": "New chair", "property_tag": "AUTH-CHAIR"})
            asset = services.update_asset(actor=self.clerk, asset=asset, data={"notes": "Inspected"})
            transfer = services.create_asset_transfer(actor=self.clerk, asset=asset,
                data={"destination_department": self.other.pk, "destination_custodian": "Legacy office label",
                      "transfer_date": timezone.localdate(), "reason": "Office use", "reference": "AUTH-HANDOFF"})
            with self.assertRaises(PermissionDenied):
                services.acknowledge_asset_transfer(actor=self.super_no_grant, transfer=transfer)
            services.acknowledge_asset_transfer(actor=self.outsider, transfer=transfer)
        asset.refresh_from_db()
        self.assertEqual(asset.assigned_department_id, self.other.pk)
        self.assertEqual(asset.notes, "Inspected")
        self.assertEqual(len(finance), 0)

    def test_uat_cannot_acknowledge_legacy_handoff_to_its_own_office(self):
        transfer = services.create_asset_transfer(actor=self.clerk, asset=self.asset,
            data={"destination_department": self.gso.pk, "destination_custodian": "Incoming desk",
                  "transfer_date": timezone.localdate(), "reason": "Return to office", "reference": "AUTH-IN"})
        with self.assertRaises(PermissionDenied):
            services.acknowledge_asset_transfer(actor=self.viewer, transfer=transfer)
        with self.assertRaises(PermissionDenied):
            services.cancel_asset_transfer(actor=self.viewer, transfer=transfer, reason="UAT cancel")
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, AssetTransfer.PENDING)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.assigned_department_id, self.other.pk)
