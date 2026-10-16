from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from . import test_property_determinations as fixtures
from . import property_determinations as service
from .models import PropertyDetermination as Record
from user.models import User


@skipUnlessDBFeature("has_select_for_update")
class PropertyRaceTests(TransactionTestCase):
    def test_competing_reviews_keep_one_decision(self):
        fixtures.PropertyDeterminationTests.setUpTestData.__func__(type(self))
        with TemporaryDirectory() as root, patch.object(Record._meta.get_field("file"), "storage", FileSystemStorage(location=root)):
            row = service.record(actor=self.clerk, asset=self.asset, request_id=uuid4(),
                expected_source=service.source_basis(self.asset), expected_predecessor=None,
                data=fixtures.PropertyDeterminationTests.data(self), upload=SimpleUploadedFile("source.pdf", b"%PDF-race"))
            barrier = Barrier(2)
            def worker(_):
                close_old_connections()
                try:
                    actor = User.objects.get(pk=self.reviewer.pk)
                    current = Record.objects.select_related("asset").get(pk=row.pk)
                    barrier.wait(timeout=10)
                    try:
                        service.decide(actor=actor, row=current, expected_version=1, action="verify", note="Checked source")
                        return "verified"
                    except ValidationError:
                        return "stale"
                finally:
                    close_old_connections()
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(worker, range(2)))
            self.assertCountEqual(outcomes, ["verified", "stale"])
            row.refresh_from_db()
            self.assertEqual(row.state_version, 2)
            self.assertEqual(row.events.count(), 2)
            service.verify_history(row)
