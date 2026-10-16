from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Asset(models.Model):
    """One register line for an asset or a homogeneous group of assets."""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    TRANSFERRED = "transferred"
    RETIRED = "retired"
    EQUIPMENT = "equipment"
    VEHICLE = "vehicle"
    KIND_CHOICES = ((EQUIPMENT, "Office equipment"), (VEHICLE, "Transport vehicle"))
    STATUS_CHOICES = (
        (ACTIVE, "In service"),
        (MAINTENANCE, "Under maintenance"),
        (TRANSFERRED, "Transferred"),
        (RETIRED, "Retired"),
    )

    department_id = models.PositiveBigIntegerField(db_index=True)
    department_label = models.CharField(max_length=160, default="General Services")
    asset_name = models.CharField(max_length=180, verbose_name="Asset name")
    asset_kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=EQUIPMENT)
    category = models.CharField(max_length=100, blank=True)
    property_tag = models.CharField(max_length=100, blank=True, verbose_name="Property tag / asset number")
    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True, verbose_name="Model")
    serial_number = models.CharField(max_length=120, blank=True)
    plate_number = models.CharField(max_length=30, blank=True)
    engine_number = models.CharField(max_length=80, blank=True)
    chassis_number = models.CharField(max_length=80, blank=True)
    registration_due = models.DateField(null=True, blank=True)
    obr_reference = models.CharField(max_length=80, blank=True, verbose_name="OBR / reference number")
    purchase_order_reference = models.CharField(max_length=100, blank=True, verbose_name="PO / contract reference")
    voucher_reference = models.CharField(max_length=100, blank=True, verbose_name="Voucher reference")
    journal_reference = models.CharField(max_length=100, blank=True, verbose_name="Journal reference")
    fund_code = models.CharField(max_length=40, blank=True)
    coa_account_code = models.CharField(max_length=40, blank=True, verbose_name="COA account code")
    coa_account_title = models.CharField(max_length=140, blank=True, verbose_name="COA account title")
    coa_basis = models.CharField(max_length=200, blank=True, verbose_name="Reviewed account mapping reference")
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
        permissions = (
            ("view_asset_audit", "Can view GSO asset change history"),
            ("export_asset_register", "Can export the scoped GSO asset register"),
        )
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


class ConsumableItem(models.Model):
    """A supply item. FIFO is an optional stock allocation aid, not an accounting workflow."""

    department_id = models.PositiveBigIntegerField(db_index=True)
    department_label = models.CharField(max_length=160, default="General Services")
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=40, default="piece", help_text="Examples: ream, bottle, box, roll.")
    use_fifo = models.BooleanField(
        default=False,
        verbose_name="Track receipt lots using FIFO",
        help_text="When enabled, issues use the oldest received stock first. Otherwise, track quantities only.",
    )
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_consumables_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_consumables_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "pk")
        constraints = (
            models.UniqueConstraint(fields=("department_id", "name"), name="gso_unique_consumable_name"),
        )
        permissions = (
            ("receive_stock", "Can record GSO supply receipts"),
            ("issue_stock", "Can issue GSO supplies to departments"),
            ("adjust_stock", "Can adjust GSO supply balances"),
            ("view_stock_audit", "Can view GSO supply movement history"),
            ("export_stock_register", "Can export GSO supply movement history"),
        )

    def __str__(self):
        return f"{self.name} ({self.unit})"

    def save(self, *args, **kwargs):
        if self.pk:
            prior = type(self).objects.get(pk=self.pk)
            if self.movements.exists() and (prior.name != self.name or prior.unit != self.unit):
                raise ValidationError("The name and unit cannot change after stock movements exist.")
            if prior.use_fifo != self.use_fifo and self.movements.exists():
                raise ValidationError({"use_fifo": "FIFO tracking cannot be changed after stock movements exist."})
        return super().save(*args, **kwargs)

    @property
    def on_hand(self):
        from django.db.models import Sum

        total = self.movements.aggregate(total=Sum("signed_quantity"))["total"]
        return total or 0


class ConsumableAuditEvent(models.Model):
    CREATED = "created"
    UPDATED = "updated"
    ACTION_CHOICES = ((CREATED, "Created"), (UPDATED, "Updated"))

    item = models.ForeignKey(ConsumableItem, on_delete=models.PROTECT, related_name="audit_events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_consumable_audit_events",
    )
    action = models.CharField(max_length=12, choices=ACTION_CHOICES)
    occurred_at = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ("-occurred_at", "-pk")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Supply item audit events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Supply item audit events are retained and cannot be deleted.")


class StockMovement(models.Model):
    RECEIPT = "receipt"
    ISSUE = "issue"
    RETURN = "return"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    KIND_CHOICES = (
        (RECEIPT, "Received"), (ISSUE, "Issued"), (RETURN, "Returned"),
        (ADJUSTMENT_IN, "Adjustment increase"), (ADJUSTMENT_OUT, "Adjustment decrease"),
    )

    item = models.ForeignKey(ConsumableItem, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    signed_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    department_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    department_label = models.CharField(max_length=160, blank=True)
    recipient = models.CharField(max_length=160, blank=True)
    reference = models.CharField(max_length=120, blank=True, help_text="Delivery, requisition, or other reference.")
    reason = models.CharField(max_length=240, blank=True)
    unit_cost = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_stock_movements",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at", "-pk")
        indexes = (models.Index(fields=("item", "occurred_at"), name="gso_stock_item_date"),)

    def __str__(self):
        return f"{self.get_kind_display()} · {self.quantity} {self.item.unit} · {self.item.name}"

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({"quantity": "Movement quantity must be greater than zero."})
        inbound = self.kind in (self.RECEIPT, self.RETURN, self.ADJUSTMENT_IN)
        expected = self.quantity if inbound else -self.quantity
        if self.signed_quantity != expected:
            raise ValidationError({"signed_quantity": "The signed quantity must match the movement type."})

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Stock movements are immutable. Record a correction as an adjustment.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Stock movements are retained and cannot be deleted.")


class StockLot(models.Model):
    item = models.ForeignKey(ConsumableItem, on_delete=models.PROTECT, related_name="lots")
    receipt = models.OneToOneField(StockMovement, on_delete=models.PROTECT, related_name="created_lot")
    received_at = models.DateTimeField()
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ("received_at", "pk")

    def __str__(self):
        return f"{self.item.name} · {self.quantity} {self.item.unit}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("FIFO lots are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("FIFO lots are retained and cannot be deleted.")


class StockLotAllocation(models.Model):
    issue = models.ForeignKey(StockMovement, on_delete=models.PROTECT, related_name="lot_allocations")
    lot = models.ForeignKey(StockLot, on_delete=models.PROTECT, related_name="allocations")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        constraints = (models.UniqueConstraint(fields=("issue", "lot"), name="gso_unique_issue_lot"),)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("FIFO allocations are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("FIFO allocations are retained and cannot be deleted.")
