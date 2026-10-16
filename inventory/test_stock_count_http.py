from time import time
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import test_stock_counts as service_tests
from .models import StockCount
from .services import record_stock_movement


class StockCountHttpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        service_tests.StockCountTests.setUpTestData.__func__(cls)

    create_item = service_tests.StockCountTests.create_item

    def setUp(self):
        service_tests.StockCountTests.setUp(self)
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.actor)
        self.start = reverse("inventory:stock-count-start", args=[self.item.pk])

    def token(self):
        return self.client.cookies["csrftoken"].value

    def payload(self):
        response = self.client.get(self.start)
        self.assertEqual(response.status_code, 200)
        return dict(source_token=response.context["form"].initial["source_token"],
            counted_on=timezone.localdate().isoformat(), quantity="8", reference="COUNT-HTTP",
            note="Counted eight reams", csrfmiddlewaretoken=self.token())

    def test_signed_observation_upload_private_download_and_independent_approval(self):
        payload = self.payload()
        self.assertEqual(self.client.post(self.start, payload).status_code, 302)
        self.assertEqual(self.client.post(self.start, payload).status_code, 302)
        count = StockCount.objects.get()
        detail = reverse("inventory:stock-count-detail", args=[count.pk])
        self.assertNotContains(self.client.get(detail), "Approve count and record difference")
        self.assertEqual(self.client.post(detail, dict(operation="approve", expected_version=1,
            **{"approve-note":"Self review", "csrfmiddlewaretoken":self.token()})).status_code, 403)
        self.assertEqual(self.client.post(detail, dict(operation="evidence", expected_version=1,
            **{"evidence-note":"Count sheet", "csrfmiddlewaretoken":self.token(),
               "evidence-upload":SimpleUploadedFile("count.pdf", b"%PDF-1.4\ncount\n%%EOF", content_type="application/pdf")})).status_code, 302)
        response = self.client.get(reverse("inventory:stock-count-evidence", args=[count.evidence.get().pk]))
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))
        self.client.force_login(self.reviewer)
        self.assertContains(self.client.get(detail), "Approve count and record difference")
        self.assertEqual(self.client.post(detail, dict(operation="approve", expected_version=2,
            **{"approve-note":"Independently checked", "csrfmiddlewaretoken":self.token()})).status_code, 302)
        self.assertContains(self.client.get(detail), "Retained adjustment")
        self.assertEqual(self.item.on_hand, 8)

    def test_csrf_wrong_actor_tampering_expiry_and_intervening_receipt(self):
        payload = self.payload()
        self.assertEqual(self.client.post(self.start, {k:v for k,v in payload.items() if k != "csrfmiddlewaretoken"}).status_code, 403)
        with patch("django.core.signing.time.time", return_value=time()+1900):
            self.assertContains(self.client.post(self.start, payload), "basis expired or changed")
        self.assertContains(self.client.post(self.start, dict(payload, source_token=payload["source_token"]+"changed")), "basis expired or changed")
        self.client.force_login(self.reviewer)
        self.client.get(self.start)
        self.assertEqual(self.client.post(self.start, dict(payload, csrfmiddlewaretoken=self.token())).status_code, 403)
        self.client.force_login(self.actor)
        self.client.get(self.start)
        record_stock_movement(actor=self.actor, item=self.item, kind="receipt", quantity="1")
        self.assertContains(self.client.post(self.start, dict(payload, csrfmiddlewaretoken=self.token())), "ledger changed")
        self.assertEqual(StockCount.objects.count(), 0)

    def test_register_low_stock_is_scoped_and_count_links_are_available(self):
        self.item.minimum_stock = 10
        self.item.save(update_fields=("minimum_stock",))
        self.assertContains(self.client.get(reverse("inventory:consumable-list")), "At or below minimum")
        self.assertContains(self.client.get(reverse("inventory:consumable-detail", args=[self.item.pk])), "Record physical count")
        self.item.is_active = False
        self.item.save(update_fields=("is_active",))
        self.assertNotContains(self.client.get(reverse("inventory:consumable-list")), "At or below minimum")
