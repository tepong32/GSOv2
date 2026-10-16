from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase, TestCase

from .employee_sources import resolve_employee_custodian


class StandaloneEmployeeBoundaryTests(SimpleTestCase):
    def test_standalone_does_not_invent_a_grand_employee_source(self):
        with self.assertRaisesMessage(ValidationError, "GRAND integration"):
            resolve_employee_custodian(actor=None, user_id=1)


class CustodyOwnerGuardTests(TestCase):
    def test_historical_handoff_actors_cannot_be_deleted(self):
        from user.models import User
        from .models import Asset, AssetTransfer
        from django.db.models.deletion import ProtectedError
        from django.utils import timezone
        asset = Asset.objects.create(asset_name="Preserved handoff", department_id=1)
        for field in ("requested_by", "acknowledged_by", "cancelled_by"):
            actor = User.objects.create_user(username=f"history-{field}")
            AssetTransfer.objects.create(asset=asset, destination_department_id=2,
                destination_department_label="Accounting", destination_custodian="Historical officer",
                transfer_date=timezone.localdate(), reason="Historical handoff", status="cancelled", **{field: actor})
            with self.subTest(field=field), self.assertRaises(ProtectedError):
                actor.delete()

    def test_handoff_checks_the_locked_owner_not_the_callers_object(self):
        from user.models import Department, User
        from .models import Asset
        from .services import create_asset_transfer
        office = Department.objects.create(name="General Services")
        other = Department.objects.create(name="General Services Office")
        actor = User.objects.create_user(username="custody-owner", department=office)
        actor.user_permissions.add(Permission.objects.get(codename="transfer_asset"))
        asset = Asset.objects.create(asset_name="Other owner's asset", department_id=other.pk)
        asset.department_id = office.pk  # Stale or manipulated caller-supplied object.
        with self.assertRaises(PermissionDenied):
            create_asset_transfer(actor=actor, asset=asset, data={})
        self.assertEqual(asset.transfers.count(), 0)
