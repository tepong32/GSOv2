from decimal import Decimal
from uuid import uuid4

from django.test import TransactionTestCase, skipUnlessDBFeature

from . import test_receiving, test_receiving_concurrency
from .models import StockMovement
from .receiving import save_receipt_line, accept_receipt
from .receiving_followups import create_followup, source_basis, remaining_quantity


@skipUnlessDBFeature("has_select_for_update")
class FollowupConcurrencyTests(TransactionTestCase):
    setUp = test_receiving_concurrency.ReceivingConcurrencyTests.setUp
    race = test_receiving_concurrency.ReceivingConcurrencyTests.race
    acceptance = test_receiving_concurrency.ReceivingConcurrencyTests.acceptance
    receipt = test_receiving.ReceivingPreparationTests.receipt
    submit = test_receiving.ReceivingPreparationTests.submit
    attach = test_receiving.ReceivingPreparationTests.attach

    def test_competing_followups_share_original_capacity_lock(self):
        root = self.receipt()
        source = save_receipt_line(actor=self.clerk, receipt=root, expected_version=1,
            data=dict(kind="supply", description="Paper", unit="ream", supply_item=self.supply,
                delivered_quantity=10, accepted_quantity=6, rejected_quantity=2, rejection_reason="Damaged"))
        root = self.submit(root)
        accept_receipt(actor=self.reviewer, receipt=root, expected_version=root.state_version, note="Original")
        source.refresh_from_db()
        children = []
        for number in (1, 2):
            child = create_followup(actor=self.clerk, source_line_id=source.pk, request_id=uuid4(),
                expected_basis=source_basis(source), inspection=dict(inspection_reference=f"Follow-up{number}",
                    inspection_date=root.inspection_date, inspector_label="Inspector", evidence_reference="Retained packet"),
                quantities=dict(accepted_quantity=Decimal("2"), rejected_quantity=Decimal("0")))
            children.append(self.submit(child))
        self.race([self.acceptance(child) for child in children])
        self.assertEqual(self.supply.on_hand, 8)
        self.assertEqual(remaining_quantity(source), 0)
        self.assertEqual(StockMovement.objects.count(), 2)
        self.assertEqual(source.followup_receipts.filter(status="accepted").count(), 1)
