from datetime import timedelta
from time import time
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core import signing
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from user.models import User

from .models import Asset, PropertyMovementRecord as Record
from .property_movement_views import SALT
from .test_property_movements import PropertyMovementFixture


class PropertyMovementHTTPTests(PropertyMovementFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.actor)
        self.new_url = reverse("inventory:property-movement-new", args=[self.asset.pk])
        self.list_url = reverse("inventory:property-movements", args=[self.asset.pk])

    def entry(self, **changes):
        response = self.client.get(self.new_url)
        self.assertEqual(response.status_code, 200)
        data = dict(determination=self.determination.pk, source="opening",
            source_token=response.context["form"].initial["source_token"],
            movement_date=(timezone.localdate()-timedelta(days=2)).isoformat(),
            reference="HTTP opening", item_number="", office_officer_label="GSO stockroom",
            opening_quantity="1", unit_cost="", remarks="Documented end-of-day stock",
            csrfmiddlewaretoken=self.client.cookies["csrftoken"].value)
        data.update(changes)
        return data

    def post_entry(self, data):
        return self.client.post(self.new_url, {**data, "upload": self.upload()})

    def test_csrf_independent_review_replay_and_visible_zero_balance(self):
        data = self.entry(opening_quantity="0", unit_cost="0")
        forged = {k: v for k, v in data.items() if k != "csrfmiddlewaretoken"}
        self.assertEqual(self.post_entry(forged).status_code, 403)
        self.assertFalse(Record.objects.exists())
        response = self.post_entry(data)
        self.assertEqual(response.status_code, 302)
        row = Record.objects.get()
        self.assertEqual(self.post_entry(data).status_code, 302)
        self.assertEqual(Record.objects.count(), 1)
        self.assertEqual(row.events.count(), 1)
        detail = reverse("inventory:property-movement-detail", args=[row.pk])
        decision = dict(operation="verify", expected_version="1", **{"verify-note": "Checked independently"},
            csrfmiddlewaretoken=self.client.cookies["csrftoken"].value)
        self.assertEqual(self.client.post(detail, decision).status_code, 403)
        self.client.force_login(self.reviewer)
        self.assertContains(self.client.get(detail), "Verify movement document")
        decision["csrfmiddlewaretoken"] = self.client.cookies["csrftoken"].value
        self.assertEqual(self.client.post(detail, decision).status_code, 302)
        response = self.client.get(self.list_url)
        self.assertEqual(response.context["projection"]["balance"], 0)
        self.assertNotContains(response, "Balance unresolved.")
        response = self.client.get(detail)
        self.assertContains(response, "0.00")
        self.assertNotContains(response, "Verify movement document")
        self.assertEqual(self.client.post(detail, decision).status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.events.count(), 2)
        self.assertFalse(self.asset.audit_events.exists())

    def test_foreign_scope_and_read_only_grants(self):
        row = self.record()
        detail = reverse("inventory:property-movement-detail", args=[row.pk])
        packet = reverse("inventory:property-movement-evidence", args=[row.pk])
        self.client.force_login(self.outsider)
        for url in (self.new_url, self.list_url, detail, packet):
            self.assertEqual(self.client.get(url).status_code, 404)
        viewer = User.objects.create_user(username="movement-viewer", department=self.office)
        viewer.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventory",
            codename__in=("view_asset", "view_property_movement")))
        self.client.force_login(viewer)
        self.assertEqual(self.client.get(self.new_url).status_code, 403)
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        self.assertNotContains(self.client.get(detail), "Verify movement document")
        self.assertNotContains(self.client.get(detail), "Cancel pending entry")
        response = self.client.get(packet)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))

    def test_signed_actor_source_and_expiry_binding(self):
        data = self.entry()
        self.client.force_login(self.reviewer)
        self.assertEqual(self.post_entry(data).status_code, 403)
        self.client.force_login(self.actor)
        handoff = self.handoff()
        substituted = {**data, "source": f"handoff:{handoff.pk}", "within_day_order": "1", "stock_delta": "0"}
        self.assertEqual(self.post_entry(substituted).status_code, 403)
        payload = signing.loads(data["source_token"], salt=SALT)
        with patch("django.core.signing.time.time", return_value=time()-1900):
            expired = signing.dumps(payload, salt=SALT)
        response = self.post_entry({**data, "source_token": expired})
        self.assertContains(response, "source form expired or changed")
        self.assertFalse(Record.objects.exists())

    def test_stale_property_source_rejected_and_unknown_balance_shown(self):
        data = self.entry()
        Asset.objects.filter(pk=self.asset.pk).update(unit_cost="200.00")
        response = self.post_entry(data)
        self.assertContains(response, "basis changed")
        self.assertFalse(Record.objects.exists())
        response = self.client.get(self.list_url)
        self.assertContains(response, "Balance unresolved.")
        self.assertIsNone(response.context["projection"]["balance"])

    def test_physical_date_is_fixed_and_unknown_cost_is_not_replaced(self):
        handoff = self.handoff()
        response = self.client.get(self.new_url, {"source": f"handoff:{handoff.pk}", "determination": self.determination.pk})
        self.assertEqual(response.status_code, 200)
        data = self.entry(source=f"handoff:{handoff.pk}", within_day_order="1", stock_delta="-1",
            movement_date="2000-01-01", source_token=response.context["form"].initial["source_token"])
        response = self.post_entry(data)
        self.assertEqual(response.status_code, 302)
        row = Record.objects.get()
        self.assertEqual(row.movement_date, handoff.transfer_date)
        self.assertIsNone(row.unit_cost)

    def test_correction_prefills_documented_content_and_preserves_verified_predecessor(self):
        original = self.decide(self.record(data=self.data(opening_quantity=0, unit_cost="12.50")))
        response = self.client.get(self.new_url)
        form = response.context["form"]
        self.assertEqual(form.initial["opening_quantity"], 0)
        self.assertEqual(str(form.initial["unit_cost"]), "12.50")
        data = self.entry(opening_quantity="1", unit_cost="12.50", reference="Corrected opening")
        self.assertEqual(self.post_entry(data).status_code, 302)
        successor = Record.objects.exclude(pk=original.pk).get()
        self.assertEqual(successor.predecessor_id, original.pk)
        self.assertIsNone(self.client.get(self.list_url).context["projection"]["balance"])
        self.decide(successor)
        self.assertEqual(self.client.get(self.list_url).context["projection"]["balance"], 1)
        original.refresh_from_db()
        self.assertEqual(original.status, "verified")
        self.assertEqual(original.opening_quantity, 0)
