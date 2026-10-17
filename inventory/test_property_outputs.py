from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from user.models import Department, User


class PARPreparationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gso = Department.objects.create(name='General Services')
        cls.actor = User.objects.create_user(username='par-reader', department=cls.gso)
        cls.actor.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory',
            codename__in=('view_asset','view_property_determination')))
        cls.ungranted = User.objects.create_user(username='par-denied', department=cls.gso)

    def setUp(self):
        self.client.force_login(self.actor)
        self.url = reverse('inventory:par-preparation')

    def data(self, **kwargs):
        data={'lines-TOTAL_FORMS':'5','lines-INITIAL_FORMS':'0','lines-MIN_NUM_FORMS':'0','lines-MAX_NUM_FORMS':'5'}
        data.update(kwargs)
        return data

    def test_blank_preview_preserves_placeholders_without_writes(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(self.url, self.data())
        self.assertContains(response, '[LGU / municipality]')
        self.assertContains(response, 'DRAFT')
        self.assertContains(response, 'Unsigned preparation only')
        self.assertTrue(response.context['ready'])
        self.assertIn('no-store',response['Cache-Control'])
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT','UPDATE','DELETE')) for q in queries))

    def test_values_are_escaped_zero_is_not_unknown_and_small_quantity_valid(self):
        response=self.client.post(self.url,self.data(**{'header-lgu':'<script>alert(1)</script>',
            'lines-0-quantity':'0.001','lines-0-acquisition_cost':'0','lines-0-description':'Desk'}))
        self.assertTrue(response.context['ready'])
        self.assertContains(response,'&lt;script&gt;')
        self.assertNotContains(response,'<script>alert(1)</script>')
        self.assertContains(response,'<td>0</td>',html=True)

    def test_invalid_values_or_oversized_formset_do_not_render_preview(self):
        for fields in ({'lines-0-acquisition_cost':'-1'}, {'lines-TOTAL_FORMS':'99999'},
                       {'header-number':'X'*81}, {'lines-0-acquisition_date':'invalid'}):
            with self.subTest(fields=fields):
                response=self.client.post(self.url,self.data(**fields))
                self.assertFalse(response.context['ready'])
                self.assertNotContains(response,'aria-label="PAR draft preview"')

    def test_permission_method_and_csrf_boundaries(self):
        self.client.force_login(self.ungranted)
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code,302)
        secured=Client(enforce_csrf_checks=True)
        secured.force_login(self.actor)
        self.assertEqual(secured.post(self.url,self.data()).status_code,403)
        self.client.force_login(self.actor)
        self.assertEqual(self.client.put(self.url).status_code,405)
