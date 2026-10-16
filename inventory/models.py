from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Asset(models.Model):
    """One register line for an asset or a homogeneous group of assets."""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    TRANSFERRED = "transferred"
    RETIRED = "retired"
    STATUS_CHOICES = (
        (ACTIVE, "In service"),
        (MAINTENANCE, "Under maintenance"),
        (TRANSFERRED, "Transferred"),
        (RETIRED, "Retired"),
    )

    department_id = models.PositiveBigIntegerField(db_index=True)
    department_label = models.CharField(max_length=160, default="General Services")
    asset_name = models.CharField(max_length=180, verbose_name="Asset name")
    category = models.CharField(max_length=100, blank=True)
    property_tag = models.CharField(max_length=100, blank=True, verbose_name="Property tag / asset number")
    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True, verbose_name="Model")
    serial_number = models.CharField(max_length=120, blank=True)
    obr_reference = models.CharField(max_length=80, blank=True, verbose_name="OBR / reference number")
    purchase_date = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=160, blank=True)
    unit_cost = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    assigned_department_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    assigned_department_label = models.CharField(max_length=160, blank=True)
    assigned_office = models.CharField(max_length=160, blank=True, verbose_name="Assigned office / custodian")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    returned_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_assets_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_assets_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("asset_name", "pk")
        permissions = (("view_asset_audit", "Can view GSO asset change history"),)
        indexes = (
            models.Index(fields=("department_id", "status"), name="gso_asset_dept_status"),
            models.Index(fields=("department_id", "asset_name"), name="gso_asset_dept_name"),
        )

    def __str__(self):
        return f"{self.asset_name} ({self.obr_reference or 'No reference'})"


class AssetAuditEvent(models.Model):
    CREATED = "created"
    UPDATED = "updated"
    RETIRED = "retired"
    ACTION_CHOICES = ((CREATED, "Created"), (UPDATED, "Updated"), (RETIRED, "Retired"))

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="audit_events")
    department_id = models.PositiveBigIntegerField(db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_audit_events",
    )
    action = models.CharField(max_length=12, choices=ACTION_CHOICES)
    occurred_at = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ("-occurred_at", "-pk")

    def __str__(self):
        return f"{self.get_action_display()} · asset {self.asset_id} · {self.occurred_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Asset audit events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Asset audit events are retained and cannot be deleted.")
