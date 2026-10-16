from django import forms
from .models import ReceivingReceipt, ReceivingLine, ReceivingEvidence, ConsumableItem


class ReceiptForm(forms.ModelForm):
    class Meta:
        model = ReceivingReceipt
        fields = ("supplier", "delivery_reference", "delivery_date", "purchase_order_reference",
                  "inspection_reference", "inspection_date", "inspector_label", "evidence_reference")
        widgets = {"delivery_date": forms.DateInput(attrs={"type": "date"}),
                   "inspection_date": forms.DateInput(attrs={"type": "date"}),
                   "evidence_reference": forms.Textarea(attrs={"rows": 3})}


class ReceiptLineForm(forms.ModelForm):
    class Meta:
        model = ReceivingLine
        fields = ("kind", "description", "unit", "delivered_quantity", "accepted_quantity",
                  "rejected_quantity", "rejection_reason", "unit_cost", "supply_item", "asset_kind",
                  "property_tag", "serial_number", "chassis_number")

    def __init__(self, *args, receipt, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.receipt = receipt
        self.fields["supply_item"].queryset = ConsumableItem.objects.filter(department_id=receipt.department_id, is_active=True)
        self.fields["accepted_quantity"].label = "Quantity supported for acceptance"
        self.fields["accepted_quantity"].help_text = "No stock is added until independent review accepts this receipt."


class EvidenceForm(forms.Form):
    kind = forms.ChoiceField(choices=ReceivingEvidence.KIND_CHOICES)
    upload = forms.FileField(label="Document (PDF, JPG, PNG or WebP; up to 15 MB)")
    note = forms.CharField(max_length=240, label="What does this document establish or correct?")


class ReceiptActionForm(forms.Form):
    expected_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput(attrs={"id": ""}))
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
