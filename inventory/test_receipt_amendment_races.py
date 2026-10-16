from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import TransactionTestCase
from . import test_receipt_amendments as service_tests
from .receipt_amendments import decide_amendment
from .models import ReceiptCostAmendment


@skipUnless(connection.vendor == "mysql", "Requires native MySQL row locks")
class ReceiptAmendmentConcurrencyTests(TransactionTestCase):
    make_user = service_tests.ReceiptAmendmentTests.make_user
    receipt = service_tests.ReceiptAmendmentTests.receipt
    line_data = service_tests.ReceiptAmendmentTests.line_data
    add_line = service_tests.ReceiptAmendmentTests.add_line
    attach = service_tests.ReceiptAmendmentTests.attach
    submit = service_tests.ReceiptAmendmentTests.submit
    upload = service_tests.ReceiptAmendmentTests.upload

    def setUp(self):
        service_tests.ReceiptAmendmentTests.setUpTestData.__func__(type(self))
        service_tests.ReceiptAmendmentTests.setUp(self)

    def race(self, *operations):
        barrier = Barrier(len(operations))
        def run(operation):
            connections.close_all()
            try:
                barrier.wait(timeout=15)
                return operation()
            except ValidationError:
                return "conflict"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            jobs = [pool.submit(run, operation) for operation in operations]
            return [job.result(timeout=45) for job in jobs]

    def test_repeated_submission_is_one_retained_document_and_event(self):
        request_id = uuid4()
        # Each worker gets its own ORM object and upload; receipt lock serializes writes.
        def record():
            from .models import ReceivingLine
            from .receipt_amendments import record_amendment, amendment_basis
            line = ReceivingLine.objects.select_related("receipt").get(pk=self.line.pk)
            return str(record_amendment(actor=get_user_model().objects.get(pk=self.clerk.pk), line=line,
                request_id=request_id, expected_basis=amendment_basis(line), unit_cost="12.00",
                reference="Duplicate", reason="Documentary correction", upload=self.upload()).public_id)
        self.assertEqual(self.race(record, record), [str(request_id)]*2)
        self.assertEqual(ReceiptCostAmendment.objects.count(), 1)
        self.assertEqual(ReceiptCostAmendment.objects.get().events.count(), 1)

    def test_repeated_review_changes_receipt_once(self):
        row = service_tests.ReceiptAmendmentTests.record(self)
        self.line.receipt.refresh_from_db()
        version = self.line.receipt.state_version
        def approve():
            return decide_amendment(actor=get_user_model().objects.get(pk=self.reviewer.pk),
                amendment=ReceiptCostAmendment.objects.get(pk=row.pk), expected_version=1,
                action="approve", note="Reviewed independently").status
        self.assertCountEqual(self.race(approve, approve), ["approved", "conflict"])
        self.line.receipt.refresh_from_db()
        self.assertEqual(self.line.receipt.state_version, version+1)
        self.assertEqual(row.events.count(), 2)
