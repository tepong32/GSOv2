from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import ReceivingReceipt, ReceivingEvidence
from .receiving import (require_receiving, create_receipt, update_receipt, save_receipt_line,
    void_receipt_line, attach_receipt_evidence, submit_receipt, accept_receipt, return_receipt,
    PREPARATION_ACTIONS)
from .receiving_forms import ReceiptForm, ReceiptLineForm, EvidenceForm, ReceiptActionForm


def scoped(actor):
    department = require_receiving(actor, "view")
    rows = ReceivingReceipt.objects.all()
    return rows if actor.is_superuser else rows.filter(department_id=department.pk)


@login_required
@require_http_methods(["GET"])
def receipt_list(request):
    return render(request, "inventory/receiving_list.html", {
        "page": Paginator(scoped(request.user), 25).get_page(request.GET.get("page")),
    })


@login_required
@require_http_methods(["GET", "POST"])
def receipt_create(request):
    require_receiving(request.user, "add")
    form = ReceiptForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            receipt = create_receipt(actor=request.user, data=form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, " ".join(error.messages))
        else:
            return redirect("inventory:receiving-detail", pk=receipt.pk)
    return render(request, "inventory/receiving_form.html", {"form": form, "heading": "Record a delivery"})


@login_required
@require_http_methods(["GET", "POST"])
def receipt_detail(request, pk):
    receipt = get_object_or_404(scoped(request.user), pk=pk)
    action = request.POST.get("action", "") if request.method == "POST" else ""
    header_form = ReceiptForm(request.POST if action == "header" else None, instance=receipt, auto_id="header_%s")
    line_form = ReceiptLineForm(request.POST if action == "line" else None, receipt=receipt, auto_id="line_%s")
    evidence_form = EvidenceForm(request.POST if action == "evidence" else None, request.FILES if action == "evidence" else None, auto_id="evidence_%s")
    control = ReceiptActionForm(request.POST or None, initial={"expected_version": receipt.state_version})
    if request.method == "POST" and control.is_valid():
        args = dict(actor=request.user, receipt=receipt, expected_version=control.cleaned_data["expected_version"])
        try:
            if action == "header" and header_form.is_valid():
                update_receipt(**args, data=header_form.cleaned_data)
            elif action == "line" and line_form.is_valid():
                save_receipt_line(**args, data=line_form.cleaned_data)
            elif action == "evidence" and evidence_form.is_valid():
                attach_receipt_evidence(**args, **evidence_form.cleaned_data)
            elif action == "submit":
                submit_receipt(**args)
            elif action == "accept":
                accept_receipt(**args, note=control.cleaned_data["note"])
            elif action == "return":
                return_receipt(**args, reason=control.cleaned_data["note"])
            elif action == "void":
                try:
                    line_id = int(request.POST.get("line_id", ""))
                except ValueError:
                    raise ValidationError("Select a valid line.")
                void_receipt_line(**args, line_id=line_id, reason=control.cleaned_data["note"])
            else:
                raise ValidationError("Review the fields for the selected action.")
        except ValidationError as error:
            control.add_error(None, " ".join(error.messages))
        else:
            messages.success(request, "Receiving record updated.")
            return redirect("inventory:receiving-detail", pk=receipt.pk)
    receipt.refresh_from_db()
    return render(request, "inventory/receiving_detail.html", {
        "receipt": receipt, "header_form": header_form, "line_form": line_form,
        "evidence_form": evidence_form, "control": control,
        "editable": receipt.status in (receipt.DRAFT, receipt.RETURNED),
        "is_preparer": receipt.events.filter(actor=request.user, action__in=PREPARATION_ACTIONS).exists(),
    })


@login_required
@require_http_methods(["GET"])
def evidence_download(request, pk):
    evidence = get_object_or_404(ReceivingEvidence, pk=pk, receipt__in=scoped(request.user))
    try:
        source = evidence.file.open("rb")
    except OSError:
        raise Http404("The retained document is unavailable.")
    response = FileResponse(source, as_attachment=True, filename=evidence.original_filename,
                            content_type="application/octet-stream")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
