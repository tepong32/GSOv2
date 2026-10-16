from django import forms
from django.core.exceptions import ValidationError
from .access import department_model
from .models import Asset, ConsumableItem, StockMovement


class AssetForm(forms.ModelForm):
    assigned_department = forms.TypedChoiceField(
        choices=(), required=False, coerce=int, empty_value=None,
        label="Assigned department",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (value, label) for value, label in Asset.STATUS_CHOICES if value != Asset.RETIRED
        ]
        model = department_model()
        if model is None:
            self.fields["assigned_department"].choices = [("", "Department directory is unavailable")]
        else:
            departments = model.objects.exclude(name="---select one---").order_by("name")
            self.fields["assigned_department"].choices = [
                (str(department.pk), department.name) for department in departments
            ]
            if self.instance and self.instance.assigned_department_id:
                self.fields["assigned_department"].initial = str(self.instance.assigned_department_id)
        self.order_fields((
            "asset_kind", "asset_name", "category", "property_tag", "brand", "model_number", "serial_number",
            "plate_number", "engine_number", "chassis_number", "registration_due",
            "obr_reference", "purchase_order_reference", "voucher_reference", "journal_reference", "fund_code",
            "coa_account_code", "coa_account_title", "coa_basis", "purchase_date", "supplier", "unit_cost", "quantity",
            "assigned_department", "assigned_office", "status", "returned_date", "notes",
        ))

    class Meta:
        model = Asset
        fields = (
            "asset_kind", "asset_name", "category", "property_tag", "brand", "model_number", "serial_number",
            "plate_number", "engine_number", "chassis_number", "registration_due",
            "obr_reference", "purchase_order_reference", "voucher_reference", "journal_reference", "fund_code",
            "coa_account_code", "coa_account_title", "coa_basis", "purchase_date", "supplier", "unit_cost", "quantity",
            "assigned_office", "status", "returned_date", "notes",
        )
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "returned_date": forms.DateInput(attrs={"type": "date"}),
            "registration_due": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "coa_account_code": "Enter only the account code confirmed by Accounting; leave blank until reviewed.",
            "coa_account_title": "Use the title from the locally approved LGU chart of accounts.",
            "coa_basis": "Record the reviewer or approved mapping reference used for this classification.",
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if self.instance.pk and quantity == self.instance.quantity:
            return quantity
        if quantity != 1:
            raise ValidationError("Record one tagged equipment item or vehicle per asset record.")
        return quantity

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == Asset.TRANSFERRED and not cleaned.get("returned_date"):
            self.add_error("returned_date", "Add the transfer or return date for a transferred asset.")
        return cleaned


class ConsumableItemForm(forms.ModelForm):
    class Meta:
        model = ConsumableItem
        fields = ("name", "category", "unit", "use_fifo", "minimum_stock", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def clean_use_fifo(self):
        use_fifo = self.cleaned_data["use_fifo"]
        if self.instance.pk and self.instance.use_fifo != use_fifo and self.instance.movements.exists():
            raise ValidationError("FIFO tracking cannot be changed after stock movements exist.")
        return use_fifo

    def clean_name(self):
        name = self.cleaned_data["name"]
        if self.instance.pk and self.instance.movements.exists() and name != self.instance.name:
            raise ValidationError("The name cannot change after stock movements exist; create a new item instead.")
        return name

    def clean_unit(self):
        unit = self.cleaned_data["unit"]
        if self.instance.pk and self.instance.movements.exists() and unit != self.instance.unit:
            raise ValidationError("The unit cannot change after stock movements exist; create a new item instead.")
        return unit


class StockReceiptForm(forms.Form):
    quantity = forms.DecimalField(min_value=0.001, max_digits=12, decimal_places=3)
    unit_cost = forms.DecimalField(required=False, min_value=0, max_digits=13, decimal_places=2)
    reference = forms.CharField(max_length=120, required=False, label="Delivery / purchase reference")
    reason = forms.CharField(max_length=240, required=False, label="Note")


class StockIssueForm(forms.Form):
    quantity = forms.DecimalField(min_value=0.001, max_digits=12, decimal_places=3)
    department = forms.TypedChoiceField(choices=(), coerce=int, label="Receiving department")
    recipient = forms.CharField(max_length=160, label="Received by")
    reference = forms.CharField(max_length=120, required=False, label="Requisition / issue reference")
    reason = forms.CharField(max_length=240, required=False, label="Purpose / note")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = department_model()
        if model is None:
            self.fields["department"].choices = [("", "Department directory unavailable")]
        else:
            qs = model.objects.exclude(name="---select one---").order_by("name")
            self.fields["department"].choices = [(str(row.pk), row.name) for row in qs]


class StockAdjustmentForm(forms.Form):
    direction = forms.ChoiceField(choices=(("in", "Increase balance"), ("out", "Decrease balance")))
    quantity = forms.DecimalField(min_value=0.001, max_digits=12, decimal_places=3)
    reason = forms.CharField(max_length=240, label="Reason for adjustment")
