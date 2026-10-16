from django import forms
from .access import department_model
from .models import Asset


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
            "asset_name", "category", "property_tag", "brand", "model_number", "serial_number",
            "obr_reference", "purchase_date", "supplier", "unit_cost", "quantity",
            "assigned_department", "assigned_office", "status", "returned_date", "notes",
        ))

    class Meta:
        model = Asset
        fields = (
            "asset_name", "category", "property_tag", "brand", "model_number", "serial_number",
            "obr_reference", "purchase_date", "supplier", "unit_cost", "quantity",
            "assigned_office", "status", "returned_date", "notes",
        )
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "returned_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == Asset.TRANSFERRED and not cleaned.get("returned_date"):
            self.add_error("returned_date", "Add the transfer or return date for a transferred asset.")
        return cleaned
