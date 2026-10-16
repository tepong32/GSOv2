from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Record
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .finance_sources import claim_line_snapshot, resolve_claim_line


class ClaimSourceSnapshotTests(SimpleTestCase):
    """Pure payload tests; they do not claim native GRAND access integration proof."""
    def source(self):
        case = Record(pk=7, public_id=uuid4(), state_version=4, current_stage="accounting_preparation",
            reference_code="SYNTHETIC", requesting_department_id=10,
            configuration_release=Record(pk=3, department_id=20),
            payee=Record(department_id=20, code="vendor", version=2, release_id=3, display_name="Synthetic vendor"))
        voucher = Record(case_id=7, dv_number="SYNTHETIC-DV", voucher_date=date(2026, 10, 17),
                         gross_amount=Decimal("1234567890123456.78"))
        line = Record(pk=8, voucher=voucher, description="Goods", account_code="REVIEWED",
                      amount=Decimal("1234567890123456.78"))
        return case, line

    def test_snapshot_preserves_owner_party_identity_and_decimal_capacity(self):
        case, line = self.source()
        result = claim_line_snapshot(case, line)
        self.assertEqual(result["source"]["line_amount"], "1234567890123456.78")
        self.assertEqual(result["source"]["finance_department_id"], 20)
        self.assertEqual(result["source"]["party"]["version"], 2)
        self.assertEqual(result, claim_line_snapshot(case, line))

    def test_version_or_line_replacement_changes_fingerprint(self):
        case, line = self.source()
        original = claim_line_snapshot(case, line)["sha256"]
        case.state_version += 1
        self.assertNotEqual(original, claim_line_snapshot(case, line)["sha256"])
        case.state_version -= 1
        line.pk += 1
        self.assertNotEqual(original, claim_line_snapshot(case, line)["sha256"])

    def test_cross_case_or_party_owner_mismatch_is_rejected(self):
        case, line = self.source()
        line.voucher.case_id = 9
        with self.assertRaises(ValidationError):
            claim_line_snapshot(case, line)
        line.voucher.case_id = 7
        case.payee.department_id = 10
        with self.assertRaises(ValidationError):
            claim_line_snapshot(case, line)

    def test_standalone_shell_does_not_simulate_finance_sources(self):
        with self.assertRaisesMessage(ValidationError, "only after GRAND integration"):
            resolve_claim_line(actor=None, case_public_id=uuid4(), line_id=1)
