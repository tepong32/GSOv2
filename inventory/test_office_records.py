from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase
from .office_records import workspace_url


class StandaloneOfficeRecordsTests(SimpleTestCase):
    def test_standalone_has_no_registry_target(self):
        class Actor:
            is_authenticated = True
            is_active = True
        self.assertIsNone(workspace_url(Actor()))
        self.assertIsNone(workspace_url(AnonymousUser()))
