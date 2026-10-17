from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from user.models import Department, User
from .models import Asset, AssetVerificationRound, AssetVerificationRecord
from .services import record_asset_verification, resolve_asset_verification_followup, verification_observation


class VerificationFollowupIntegrityTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name='General Services')
        self.actor = User.objects.create_superuser(username='count-reviewer', password='synthetic-only', email='count@example.test')
        self.asset = Asset.objects.create(department_id=self.department.pk, asset_name='Desk')
        self.round = AssetVerificationRound.objects.create(title='Count', department_id=self.department.pk)
        self.record = AssetVerificationRecord.objects.create(verification_round=self.round, asset=self.asset, asset_name_snapshot='Desk')
        self.observe()

    def observe(self, result='not_found', notes='Not located in assigned room'):
        self.record = record_asset_verification(actor=self.actor, record=self.record, data={'result': result, 'notes': notes})

    def latest(self):
        return self.record.events.order_by('-pk').first().pk

    def resolve(self, event=None):
        return resolve_asset_verification_followup(actor=self.actor, record=self.record,
            status='resolved', note='Reviewed original finding', expected_event_id=event if event is not None else self.latest(),
            expected_observation=verification_observation(self.record))

    def test_new_check_reopens_review_and_preserves_prior_decision(self):
        self.resolve()
        prior = list(self.record.events.values('pk', 'snapshot'))
        self.observe(notes='Still absent; new search location checked')
        self.assertTrue(self.record.needs_followup)
        self.assertEqual(self.record.resolution_note, '')
        self.assertIsNone(self.record.resolved_by_id)
        self.assertIsNone(self.record.resolved_at)
        self.assertEqual(list(self.record.events.filter(pk__in=[e['pk'] for e in prior]).values('pk','snapshot')), prior)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.ACTIVE)

    def test_matched_check_clears_old_resolution_without_requiring_followup(self):
        self.resolve()
        self.observe('matched', 'Located')
        self.assertFalse(self.record.needs_followup)
        self.assertEqual(self.record.resolution_note, '')
        with self.assertRaises(ValidationError):
            self.resolve()

    def test_stale_observation_and_duplicate_decision_are_rejected(self):
        first = self.latest()
        self.observe(notes='New location searched')
        with self.assertRaises(ValidationError):
            self.resolve(first)
        current = self.latest()
        self.resolve(current)
        with self.assertRaises(ValidationError):
            self.resolve(current)
        self.assertEqual(self.record.events.last().snapshot['reviewed_event_id'], current)

    def test_signed_form_rejects_changed_observation_and_displays_error(self):
        self.client.force_login(self.actor)
        url = reverse('inventory:asset-verification-followup', args=[self.record.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        token = response.context['review_token']
        self.observe(notes='A later count observation')
        response = self.client.post(url, {'status':'resolved', 'note':'Old review', 'review_token':token})
        self.assertContains(response, 'Reload and review it again.')
        self.record.refresh_from_db()
        self.assertTrue(self.record.needs_followup)
        response = self.client.post(url, {'status':'resolved', 'note':'Missing token'})
        self.assertContains(response, 'expired or is invalid')
        token = self.client.get(url).context['review_token']
        response = self.client.post(url, {'status':'resolved', 'note':'Fresh review', 'review_token':token})
        self.assertEqual(response.status_code, 302)

    def test_new_event_cannot_authorize_an_unseen_observation(self):
        old_observation = verification_observation(self.record)
        self.observe(notes='Changed before form event read')
        with self.assertRaises(ValidationError):
            resolve_asset_verification_followup(actor=self.actor, record=self.record,
                status='resolved', note='Unseen observation', expected_event_id=self.latest(),
                expected_observation=old_observation)
