import hashlib
import json
from io import StringIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.urls import reverse

from . import services
from .disposal_evidence import open_checked_evidence, verify_case_evidence
from .models import AssetDisposalAttachment
from .test_disposal_locking import DisposalFixture


class DisposalEvidenceTests(DisposalFixture, TestCase):
    def attach(self):
        return services._save_disposal_attachments(case=self.case, actor=self.actor,
            groups=[("supporting", [SimpleUploadedFile("source.pdf", b"%PDF-retained source")])])[0]

    def test_service_retains_hash_and_download_checks_same_bytes(self):
        row = self.attach()
        self.assertEqual(row.sha256, hashlib.sha256(b"%PDF-retained source").hexdigest())
        self.assertEqual(row.size, len(b"%PDF-retained source"))
        verify_case_evidence(self.case)
        self.client.force_login(self.actor)
        url = reverse("inventory:disposal-attachment-download", args=[row.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-retained source")
        Path(row.file.path).write_bytes(b"%PDF-altered source!")
        self.assertEqual(self.client.get(url).status_code, 409)
        with self.assertRaises(ValidationError):
            verify_case_evidence(self.case)

    def test_invalid_later_group_leaves_no_files_or_rows(self):
        with self.assertRaises(ValidationError):
            services._save_disposal_attachments(case=self.case, actor=self.actor, groups=[
                ("supporting", [SimpleUploadedFile("valid.pdf", b"%PDF-good")]),
                ("authority", [SimpleUploadedFile("bad.pdf", b"not a pdf")]),
            ])
        self.assertFalse(self.case.attachments.exists())
        root = Path(AssetDisposalAttachment._meta.get_field("file").storage.location)
        self.assertEqual(list(root.rglob("*.pdf")), [])

    def test_legacy_is_readable_but_not_verified_and_checker_does_not_backfill(self):
        row = self.attach()
        AssetDisposalAttachment.objects.filter(pk=row.pk).update(sha256="")
        row.refresh_from_db()
        with open_checked_evidence(row, allow_legacy=True) as source:
            self.assertEqual(source.read(), b"%PDF-retained source")
        with self.assertRaisesMessage(ValidationError, "unknown integrity"):
            verify_case_evidence(self.case)
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("check_disposal_evidence", stdout=output)
        report = json.loads(output.getvalue())
        self.assertEqual([r["id"] for r in report["unknown"]], [row.pk])
        self.assertEqual(report["changed"], [])
        row.refresh_from_db()
        self.assertEqual(row.sha256, "")

    def test_missing_or_tampered_evidence_blocks_completion_without_state_change(self):
        data = self.completion()
        row = self.attach()
        Path(row.file.path).unlink()
        with self.assertRaisesMessage(ValidationError, "unavailable"):
            services.review_asset_disposal_case(actor=self.actor, case=self.case, data=data)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, "authorized")
        self.assertEqual(self.case.events.count(), 0)

    def test_reopened_file_missing_after_success_is_validation_error(self):
        row = self.attach()
        with open_checked_evidence(row):
            pass
        Path(row.file.path).unlink()
        with self.assertRaisesMessage(ValidationError, "unavailable"):
            open_checked_evidence(row)
