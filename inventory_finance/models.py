"""Optional GRAND-only relationships; no replacement Finance or supplier tables."""
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ReceiptClaimAttribution(models.Model):
    PROPOSED, APPROVED, REJECTED, WITHDRAWN = "proposed", "approved", "rejected", "withdrawn"
    STATUS_CHOICES = tuple((value, value.title()) for value in (PROPOSED, APPROVED, REJECTED, WITHDRAWN))

    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    receipt_line = models.ForeignKey("inventory.ReceivingLine", on_delete=models.PROTECT,
                                     related_name="claim_attributions")
    case = models.ForeignKey("vouchers.VoucherCase", on_delete=models.PROTECT,
                             related_name="gso_receipt_attributions")
    finance_department = models.ForeignKey("departments.Department", on_delete=models.PROTECT,
                                           related_name="gso_claim_attributions")
    # GRAND replaces DV lines during re-preparation; retain the reviewed identity,
    # never protect the replaceable line or silently retarget its replacement.
    source_line_id = models.PositiveBigIntegerField()
    source_snapshot = models.JSONField()
    source_checksum = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    basis = models.TextField(help_text="Explain the documented amount this receipt line supports in the claim.")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PROPOSED)
    state_version = models.PositiveIntegerField(default=1)
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="gso_claim_attributions_proposed")
    proposed_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="gso_claim_attributions_reviewed", null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-proposed_at", "-pk")
        default_permissions = ("view",)
        permissions = (("propose_receiptclaimattribution", "Can propose GSO receipt claim attribution"),
                       ("review_receiptclaimattribution", "Can independently review receipt claim attribution"))
        indexes = [models.Index(fields=("case", "source_line_id", "status"), name="gso_claim_source_status")]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="gso_claim_positive_amount"),
            models.CheckConstraint(
                condition=~models.Q(status__in=("approved", "rejected")) | (
                    models.Q(reviewed_by__isnull=False, reviewed_at__isnull=False)
                    & ~models.Q(reviewed_by=models.F("proposed_by"))),
                name="gso_claim_independent_review"),
        ]

    def delete(self, *args, **kwargs):
        raise ValidationError("Claim attribution history must be retained; withdraw it with a reason.")


class ReceiptClaimEvent(models.Model):
    attribution = models.ForeignKey(ReceiptClaimAttribution, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="gso_claim_events")
    action = models.CharField(max_length=20)
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        default_permissions = ("view",)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Claim attribution events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Claim attribution events must be retained.")
