from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from uuid import uuid4


def disposal_private_storage():
    return FileSystemStorage(location=settings.DISPOSAL_PRIVATE_ROOT, base_url=None)


class Asset(models.Model):
    """One register line for an asset or a homogeneous group of assets."""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    TRANSFERRED = "transferred"
    RETIRED = "retired"
    EQUIPMENT = "equipment"
    VEHICLE = "vehicle"
    KIND_CHOICES = ((EQUIPMENT, "Equipment / furniture"), (VEHICLE, "Transport vehicle"))
    CLASS_PENDING = "pending_review"
    CLASS_ICT = "ict_equipment"
    CLASS_OFFICE = "office_equipment"
    CLASS_PRINTING = "printing_equipment"
    CLASS_COMMUNICATIONS = "communications_equipment"
    CLASS_MACHINERY = "other_machinery_equipment"
    CLASS_FURNITURE = "furniture_fixtures"
    CLASS_TRANSPORT = "transportation_equipment"
    CLASS_OTHER = "other_equipment"
    INVENTORY_CLASS_CHOICES = (
        (CLASS_PENDING, "Needs Accounting review"),
        (CLASS_ICT, "ICT equipment"),
        (CLASS_OFFICE, "Office equipment"),
        (CLASS_PRINTING, "Printing equipment"),
        (CLASS_COMMUNICATIONS, "Communications equipment"),
        (CLASS_MACHINERY, "Other machinery and equipment"),
        (CLASS_FURNITURE, "Furniture and fixtures"),
        (CLASS_TRANSPORT, "Transportation equipment"),
        (CLASS_OTHER, "Other equipment"),
    )
    ITEM_TYPE_CHOICES = (
        ("desktop", "Desktop computer"),
        ("laptop", "Laptop computer"),
        ("monitor", "Monitor"),
        ("printer", "Printer"),
        ("photocopier", "Photocopier"),
        ("scanner", "Scanner"),
        ("shredder", "Paper shredder"),
        ("bookbinding_machine", "Bookbinding machine"),
        ("ups", "UPS / backup power unit"),
        ("external_drive", "External storage drive"),
        ("camera", "Camera"),
        ("walkie_talkie", "Walkie-talkie / radio"),
        ("sound_system", "Sound / public-address system"),
        ("projector", "Projector"),
        ("network_equipment", "Network equipment"),
        ("desk", "Desk"),
        ("chair", "Chair"),
        ("table", "Table"),
        ("cabinet", "Cabinet"),
        ("shelving", "Shelf / shelving"),
        ("fixture", "Other furniture or fixture"),
        ("motor_vehicle", "Motor vehicle"),
        ("other", "Other / describe below"),
    )
    FURNITURE_ITEM_TYPES = {"desk", "chair", "table", "cabinet", "shelving", "fixture"}
    STATUS_CHOICES = (
        (ACTIVE, "In service"),
        (MAINTENANCE, "Under maintenance"),
        (TRANSFERRED, "Transferred"),
        (RETIRED, "Retired"),
    )

    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    department_id = models.PositiveBigIntegerField(db_index=True)
    department_label = models.CharField(max_length=160, default="General Services")
    asset_name = models.CharField(max_length=180, verbose_name="Asset name")
    asset_kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=EQUIPMENT)
    inventory_class = models.CharField(
        max_length=32, choices=INVENTORY_CLASS_CHOICES, default=CLASS_PENDING,
        verbose_name="Inventory class",
    )
    item_type = models.CharField(max_length=32, choices=ITEM_TYPE_CHOICES, default="other")
    category = models.CharField(
        max_length=100, blank=True, verbose_name="Additional item description",
        help_text="Optional legacy category or detail. Use the class and item type fields for consistent reporting.",
    )
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
            ("transfer_asset", "Can initiate GSO asset handoffs"),
            ("acknowledge_asset_transfer", "Can acknowledge asset handoffs to the assigned department"),
            ("request_asset_disposal", "Can request assessment for disposal of an assigned asset"),
            ("review_asset_disposal", "Can review and record GSO asset disposal cases"),
            ("start_asset_verification", "Can start GSO physical asset verification rounds"),
            ("record_asset_verification", "Can record physical asset verification results"),
            ("close_asset_verification", "Can close completed physical asset verification rounds"),
            ("import_asset_accounting_snapshot", "Can import an Accounting asset snapshot for reconciliation"),
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
    TRANSFERRED = "transferred"
    DISPOSED = "disposed"
    ACTION_CHOICES = (
        (CREATED, "Created"), (UPDATED, "Updated"), (TRANSFERRED, "Transferred"),
        (RETIRED, "Retired"), (DISPOSED, "Disposed"),
    )

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


class AssetTransfer(models.Model):
    """A simple, acknowledged custody handoff for one registered asset."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (PENDING, "Waiting for acknowledgment"),
        (ACCEPTED, "Acknowledged"),
        (CANCELLED, "Cancelled"),
    )

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="transfers")
    source_department_id = models.PositiveBigIntegerField(null=True, blank=True)
    source_department_label = models.CharField(max_length=160, blank=True)
    source_custodian = models.CharField(max_length=160, blank=True)
    destination_department_id = models.PositiveBigIntegerField(db_index=True)
    destination_department_label = models.CharField(max_length=160)
    destination_custodian = models.CharField(max_length=160)
    transfer_date = models.DateField()
    reason = models.CharField(max_length=240)
    reference = models.CharField(max_length=120, blank=True, verbose_name="PAR / ICS / other reference")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_transfers_requested",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_transfers_acknowledged",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_transfers_cancelled",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=240, blank=True)
    pending_identity_marker = models.GeneratedField(
        expression=models.Case(models.When(status="pending", then=models.Value(1)), default=models.Value(None)),
        output_field=models.PositiveSmallIntegerField(), db_persist=False, null=True,
    )

    class Meta:
        ordering = ("-requested_at", "-pk")
        constraints = (
            models.UniqueConstraint(
                fields=("asset", "pending_identity_marker"),
                name="gso_one_pending_asset_transfer",
            ),
        )

    def __str__(self):
        return f"{self.asset.asset_name}: {self.source_department_label or 'Unassigned'} to {self.destination_department_label}"


class AssetVerificationRound(models.Model):
    """A dated GSO exercise that snapshots the assets to be physically checked."""

    title = models.CharField(max_length=160)
    as_of_date = models.DateField(default=timezone.localdate, verbose_name="Physical count as of")
    department_id = models.PositiveBigIntegerField(db_index=True)
    department_label = models.CharField(max_length=160)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_verification_rounds_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_verification_rounds_closed",
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")

    @property
    def is_closed(self):
        return self.closed_at is not None

    def __str__(self):
        return self.title


class AssetVerificationRecord(models.Model):
    NOT_CHECKED = "not_checked"
    MATCHED = "matched"
    DISCREPANCY = "discrepancy"
    NOT_FOUND = "not_found"
    RESULT_CHOICES = (
        (NOT_CHECKED, "Not checked"),
        (MATCHED, "Found and matched"),
        (DISCREPANCY, "Found with a discrepancy"),
        (NOT_FOUND, "Not found during visit"),
    )
    CONDITION_CHOICES = (("serviceable", "Serviceable"), ("damaged", "Damaged / needs attention"), ("unknown", "Not assessed"))
    FOLLOW_UP_OPEN = "open"
    FOLLOW_UP_RESOLVED = "resolved"
    FOLLOW_UP_ACCEPTED = "accepted_difference"
    FOLLOW_UP_CHOICES = (
        (FOLLOW_UP_OPEN, "Follow-up needed"),
        (FOLLOW_UP_RESOLVED, "Resolved"),
        (FOLLOW_UP_ACCEPTED, "Difference reviewed / accepted"),
    )

    verification_round = models.ForeignKey(AssetVerificationRound, on_delete=models.PROTECT, related_name="records")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="verification_records")
    asset_name_snapshot = models.CharField(max_length=180)
    property_tag_snapshot = models.CharField(max_length=100, blank=True)
    serial_number_snapshot = models.CharField(max_length=120, blank=True)
    assigned_department_snapshot = models.CharField(max_length=160, blank=True)
    assigned_office_snapshot = models.CharField(max_length=160, blank=True)
    account_code_snapshot = models.CharField(max_length=40, blank=True)
    account_title_snapshot = models.CharField(max_length=140, blank=True)
    purchase_date_snapshot = models.DateField(null=True, blank=True)
    acquisition_cost_snapshot = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default=NOT_CHECKED, db_index=True)
    observed_department = models.CharField(max_length=160, blank=True)
    observed_office = models.CharField(max_length=160, blank=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True)
    notes = models.TextField(blank=True)
    follow_up_status = models.CharField(max_length=24, choices=FOLLOW_UP_CHOICES, default=FOLLOW_UP_OPEN, db_index=True)
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_verification_followups_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_verifications_recorded",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("result", "asset_name_snapshot", "pk")
        constraints = (models.UniqueConstraint(fields=("verification_round", "asset"), name="gso_asset_once_per_verification"),)

    def __str__(self):
        return f"{self.asset_name_snapshot} — {self.get_result_display()}"

    @property
    def needs_followup(self):
        return self.result in (self.DISCREPANCY, self.NOT_FOUND) and self.follow_up_status == self.FOLLOW_UP_OPEN


class AssetVerificationEvent(models.Model):
    record = models.ForeignKey(AssetVerificationRecord, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_verification_events",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ("occurred_at", "pk")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Verification history is immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Verification history is retained and cannot be deleted.")


class AssetVerificationFinding(models.Model):
    """An asset found during a count that was not in that round's register snapshot."""

    PENDING = "pending"
    REGISTERED = "registered"
    NOT_LGU_ASSET = "not_lgu_asset"
    DUPLICATE = "duplicate"
    STATUS_CHOICES = (
        (PENDING, "Needs review"),
        (REGISTERED, "Added to register"),
        (NOT_LGU_ASSET, "Confirmed not an LGU asset"),
        (DUPLICATE, "Duplicate of another record"),
    )

    verification_round = models.ForeignKey(AssetVerificationRound, on_delete=models.PROTECT, related_name="findings")
    asset_name = models.CharField(max_length=180)
    property_tag = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    found_department = models.CharField(max_length=160, blank=True)
    found_office = models.CharField(max_length=160, blank=True)
    condition = models.CharField(max_length=20, choices=AssetVerificationRecord.CONDITION_CHOICES, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    resolution_note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_findings_recorded",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_findings_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    related_asset = models.ForeignKey(
        Asset, null=True, blank=True, on_delete=models.PROTECT,
        related_name="verification_findings_linked",
    )

    class Meta:
        ordering = ("status", "asset_name", "pk")


def accounting_import_path(instance, filename):
    return f"inventory/reconciliation/{instance.verification_round_id}/{uuid4().hex}.csv"


class AssetAccountingImport(models.Model):
    """Immutable imported snapshot from Accounting for a physical count comparison."""

    verification_round = models.ForeignKey(AssetVerificationRound, on_delete=models.PROTECT, related_name="accounting_imports")
    source_filename = models.CharField(max_length=255)
    source_file = models.FileField(blank=True, default="", upload_to=accounting_import_path, storage=disposal_private_storage)
    source_sha256 = models.CharField(max_length=64)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_accounting_snapshots_imported",
    )
    imported_at = models.DateTimeField(auto_now_add=True)
    line_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-imported_at", "-pk")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Accounting snapshots are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Accounting snapshots are retained and cannot be deleted.")


class AssetAccountingLine(models.Model):
    accounting_import = models.ForeignKey(AssetAccountingImport, on_delete=models.PROTECT, related_name="lines")
    row_number = models.PositiveIntegerField()
    property_tag = models.CharField(max_length=100, blank=True)
    asset_name = models.CharField(max_length=180)
    serial_number = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=160, blank=True)
    account_code = models.CharField(max_length=40, blank=True)
    account_title = models.CharField(max_length=140, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    acquisition_cost = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ("row_number", "pk")
        constraints = (models.UniqueConstraint(fields=("accounting_import", "row_number"), name="gso_accounting_import_row_once"),)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Imported Accounting rows are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Imported Accounting rows are retained and cannot be deleted.")


class AssetVerificationFindingEvent(models.Model):
    finding = models.ForeignKey(AssetVerificationFinding, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_finding_events",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ("occurred_at", "pk")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Verification finding history is immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Verification finding history is retained and cannot be deleted.")


class AssetDisposalCase(models.Model):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    NEEDS_INFORMATION = "needs_information"
    AUTHORIZED = "authorized"
    DISPOSED = "disposed"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (SUBMITTED, "Submitted to GSO"),
        (UNDER_REVIEW, "Under GSO review"),
        (NEEDS_INFORMATION, "More information needed"),
        (AUTHORIZED, "Authorized for disposal"),
        (DISPOSED, "Disposal completed"),
        (REJECTED, "Request rejected"),
    )
    DISPOSAL_METHOD_CHOICES = (
        ("", "Select after authorization"),
        ("sale", "Sale"),
        ("donation", "Donation"),
        ("transfer", "Transfer"),
        ("barter", "Barter"),
        ("destruction", "Condemnation / destruction"),
    )

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="disposal_cases")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=SUBMITTED, db_index=True)
    reason = models.CharField(max_length=240)
    condition_details = models.TextField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_disposal_requests",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_disposal_cases_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    authority_reference = models.CharField(max_length=160, blank=True)
    disposal_method = models.CharField(max_length=20, choices=DISPOSAL_METHOD_CHOICES, blank=True)
    disposal_date = models.DateField(null=True, blank=True)
    completion_reference = models.CharField(max_length=160, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_disposals_completed",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    open_identity_marker = models.GeneratedField(
        expression=models.Case(models.When(
            status__in=("submitted", "under_review", "needs_information", "authorized"),
            then=models.Value(1)), default=models.Value(None)),
        output_field=models.PositiveSmallIntegerField(), db_persist=False, null=True,
    )

    class Meta:
        ordering = ("-submitted_at", "-pk")
        constraints = (
            models.UniqueConstraint(
                fields=("asset", "open_identity_marker"),
                name="gso_one_open_disposal_case",
            ),
        )

    def __str__(self):
        return f"Disposal request for {self.asset.asset_name} ({self.get_status_display()})"


def disposal_attachment_path(instance, filename):
    tag = slugify(instance.disposal_case.asset.property_tag or f"asset-{instance.disposal_case.asset_id}")[:70]
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"inventory/disposal/{instance.disposal_case.asset_id}/{tag}-case-{instance.disposal_case_id}-{instance.kind}-{uuid4().hex[:10]}.{extension}"


class AssetDisposalAttachment(models.Model):
    PHOTO = "photo"
    REQUEST_FORM = "request_form"
    SUPPORTING = "supporting"
    KIND_CHOICES = (
        (PHOTO, "Asset condition photo"),
        (REQUEST_FORM, "Signed disposal request form"),
        (SUPPORTING, "Supporting document"),
        ("authority", "Approval / authority document"),
        ("completion", "Disposal completion evidence"),
    )

    disposal_case = models.ForeignKey(AssetDisposalCase, on_delete=models.PROTECT, related_name="attachments")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    file = models.FileField(upload_to=disposal_attachment_path, storage=disposal_private_storage)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_disposal_attachments_uploaded",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("kind", "uploaded_at", "pk")

    def __str__(self):
        return f"{self.get_kind_display()} for case {self.disposal_case_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Disposal evidence is retained and cannot be replaced.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Disposal evidence is retained and cannot be deleted.")


class AssetDisposalEvent(models.Model):
    ACTION_CHOICES = (
        ("submitted", "Submitted"), ("under_review", "Under review"),
        ("needs_information", "More information requested"),
        ("authorized", "Authorized for disposal"), ("disposed", "Disposal completed"),
        ("rejected", "Rejected"), ("resubmitted", "Resubmitted"),
    )
    disposal_case = models.ForeignKey(AssetDisposalCase, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gso_asset_disposal_events",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    occurred_at = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ("occurred_at", "pk")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Disposal case history is immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Disposal case history is retained and cannot be deleted.")


class ConsumableItem(models.Model):
    """A supply item. FIFO is an optional stock allocation aid, not an accounting workflow."""

    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
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

    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
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


class ReceivingReceipt(models.Model):
    """Physical delivery and inspection evidence; never a Finance approval."""

    DRAFT, SUBMITTED, ACCEPTED, RETURNED = "draft", "submitted", "accepted", "returned"
    STATUS_CHOICES = ((DRAFT, "Draft"), (SUBMITTED, "For review"),
                      (ACCEPTED, "Accepted into inventory"), (RETURNED, "Returned for correction"))
    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    department_id = models.PositiveBigIntegerField(db_index=True)
    department_label = models.CharField(max_length=160)
    supplier = models.CharField(max_length=160)
    delivery_reference = models.CharField(max_length=180)
    delivery_date = models.DateField()
    purchase_order_reference = models.CharField(max_length=100, blank=True)
    inspection_reference = models.CharField(max_length=180)
    inspection_date = models.DateField()
    inspector_label = models.CharField(max_length=160)
    evidence_reference = models.TextField(help_text="Location/reference of the retained delivery and inspection documents.")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=DRAFT)
    state_version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gso_receipts_created")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="gso_receipts_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        permissions = (("submit_receivingreceipt", "Can submit GSO receiving records"),
                       ("review_receivingreceipt", "Can independently review GSO receiving records"))

    def clean(self):
        if self.delivery_date and self.delivery_date > timezone.localdate():
            raise ValidationError({"delivery_date": "Delivery cannot be in the future."})
        if self.inspection_date and (self.inspection_date > timezone.localdate() or
                                    self.delivery_date and self.inspection_date < self.delivery_date):
            raise ValidationError({"inspection_date": "Inspection must be on or after delivery and not in the future."})


class ReceivingLine(models.Model):
    ASSET, SUPPLY = "asset", "supply"
    receipt = models.ForeignKey(ReceivingReceipt, on_delete=models.PROTECT, related_name="lines")
    sequence = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=12, choices=((ASSET, "Individually tracked asset"), (SUPPLY, "Consumable supply")))
    description = models.CharField(max_length=180)
    unit = models.CharField(max_length=40)
    delivered_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    accepted_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    rejected_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    rejection_reason = models.CharField(max_length=240, blank=True)
    unit_cost = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    supply_item = models.ForeignKey(ConsumableItem, on_delete=models.PROTECT, null=True, blank=True, related_name="receiving_lines")
    asset_kind = models.CharField(max_length=20, choices=Asset.KIND_CHOICES, default=Asset.EQUIPMENT)
    property_tag = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    chassis_number = models.CharField(max_length=80, blank=True)
    is_void = models.BooleanField(default=False)
    registered_asset = models.OneToOneField(Asset, on_delete=models.PROTECT, null=True, blank=True, related_name="receiving_line")
    stock_movement = models.OneToOneField(StockMovement, on_delete=models.PROTECT, null=True, blank=True, related_name="receiving_line")

    class Meta:
        ordering = ("sequence",)
        constraints = [
            models.UniqueConstraint(fields=("receipt", "sequence"), name="gso_receipt_line_sequence"),
            models.CheckConstraint(condition=models.Q(delivered_quantity__gt=0, accepted_quantity__gte=0, rejected_quantity__gte=0), name="gso_receipt_nonnegative_qty"),
            models.CheckConstraint(condition=models.Q(delivered_quantity__gte=models.F("accepted_quantity") + models.F("rejected_quantity")), name="gso_receipt_quantity_capacity"),
        ]

    def clean(self):
        if self.accepted_quantity is not None and self.rejected_quantity is not None and self.delivered_quantity is not None:
            if self.accepted_quantity + self.rejected_quantity > self.delivered_quantity:
                raise ValidationError("Accepted and rejected quantities exceed the delivery.")
        if self.rejected_quantity and not self.rejection_reason.strip():
            raise ValidationError({"rejection_reason": "Explain the rejected quantity."})
        if self.unit_cost is not None and self.unit_cost < 0:
            raise ValidationError({"unit_cost": "Cost cannot be negative."})
        if self.kind == self.ASSET:
            if self.delivered_quantity != 1 or self.accepted_quantity not in (0, 1) or self.rejected_quantity not in (0, 1):
                raise ValidationError("Use one line per individually tracked asset.")
            if self.accepted_quantity and not self.property_tag.strip():
                raise ValidationError({"property_tag": "Record the property tag before accepting this asset."})
            if self.supply_item_id:
                raise ValidationError("An asset line cannot select a supply item.")
        elif self.kind == self.SUPPLY:
            if not self.supply_item_id:
                raise ValidationError({"supply_item": "Select an existing supply item."})
            if self.property_tag or self.serial_number or self.chassis_number:
                raise ValidationError("Use an individually tracked asset line for tagged or serialized property.")
            if self.supply_item_id and (self.supply_item.department_id != self.receipt.department_id or
                                       self.unit != self.supply_item.unit or not self.supply_item.is_active):
                raise ValidationError("Select an active supply in this office and use its registered unit.")


class ReceivingEvent(models.Model):
    receipt = models.ForeignKey(ReceivingReceipt, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gso_receiving_events")
    action = models.CharField(max_length=32)
    occurred_at = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ("occurred_at", "pk")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Receiving history cannot be replaced.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Receiving history is retained.")


def receiving_evidence_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"inventory/receiving/{instance.receipt.public_id}/{instance.kind}-{uuid4().hex}.{extension}"


class ReceivingEvidence(models.Model):
    KIND_CHOICES = (("delivery", "Delivery document"), ("inspection", "Inspection / acceptance document"),
                    ("supporting", "Supporting record"))
    receipt = models.ForeignKey(ReceivingReceipt, on_delete=models.PROTECT, related_name="evidence")
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    file = models.FileField(upload_to=receiving_evidence_path, storage=disposal_private_storage, max_length=255)
    original_filename = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveBigIntegerField()
    note = models.CharField(max_length=240)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gso_receiving_uploads")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("uploaded_at", "pk")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Receiving evidence cannot be replaced. Append a correction document.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Receiving evidence is retained.")


class AssetMaintenanceCase(models.Model):
    OPEN, COMPLETED, CANCELLED = "open", "completed", "cancelled"
    STATUS_CHOICES = ((OPEN, "Open"), (COMPLETED, "Completed"), (CANCELLED, "Cancelled"))
    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="maintenance_cases")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=OPEN)
    state_version = models.PositiveIntegerField(default=1)
    prior_asset_status = models.CharField(max_length=16, choices=Asset.STATUS_CHOICES)
    reported_date = models.DateField()
    problem = models.TextField(max_length=4000)
    provider = models.CharField(max_length=240, blank=True)
    work_performed = models.TextField(max_length=4000, blank=True)
    documented_cost = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True,
                                         validators=[MinValueValidator(0)])
    cost_reference = models.CharField(max_length=240, blank=True)
    finished_date = models.DateField(null=True, blank=True)
    resulting_asset_status = models.CharField(max_length=16, blank=True, choices=Asset.STATUS_CHOICES)
    closure_note = models.TextField(max_length=4000, blank=True)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gso_maintenance_opened")
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="gso_maintenance_closed")
    closed_at = models.DateTimeField(null=True, blank=True)
    open_identity_marker = models.GeneratedField(
        expression=models.Case(models.When(status="open", then=models.Value(1)), default=models.Value(None)),
        output_field=models.PositiveSmallIntegerField(), db_persist=False, null=True,
    )

    class Meta:
        ordering = ("-opened_at", "-pk")
        default_permissions = ("view",)
        permissions = (("manage_assetmaintenancecase", "Can record asset maintenance work"),)
        constraints = (
            models.UniqueConstraint(fields=("asset", "open_identity_marker"), name="gso_one_open_maintenance"),
            models.CheckConstraint(condition=models.Q(documented_cost__isnull=True) | models.Q(documented_cost__gte=0),
                                   name="gso_maintenance_cost_nonnegative"),
        )

    def delete(self, *args, **kwargs):
        raise ValidationError("Maintenance history is retained. Cancel an open case instead.")


class AssetMaintenanceEvent(models.Model):
    case = models.ForeignKey(AssetMaintenanceCase, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gso_maintenance_events")
    action = models.CharField(max_length=24)
    occurred_at = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ("occurred_at", "pk")
        default_permissions = ()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Maintenance events cannot be replaced.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Maintenance events are retained.")


def maintenance_evidence_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"inventory/maintenance/{instance.case.public_id}/{uuid4().hex}.{extension}"


class AssetMaintenanceEvidence(models.Model):
    case = models.ForeignKey(AssetMaintenanceCase, on_delete=models.PROTECT, related_name="evidence")
    file = models.FileField(upload_to=maintenance_evidence_path, storage=disposal_private_storage, max_length=255)
    original_filename = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveBigIntegerField()
    note = models.CharField(max_length=240)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gso_maintenance_uploads")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("uploaded_at", "pk")
        default_permissions = ()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Maintenance evidence cannot be replaced. Append a correction document.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Maintenance evidence is retained.")
