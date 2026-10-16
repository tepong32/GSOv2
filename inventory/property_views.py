from uuid import uuid4
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from . import property_determinations as service
from .access import gso_department_for_user
from .models import Asset
from .property_forms import PropertyForm, PropertyDecisionForm, PropertyVersionForm

SALT = "gso-property-determination-v1"


def display_value(model, name, raw):
    field = model._meta.get_field(name)
    return dict(field.flatchoices).get(raw, service.value(raw)) if field.choices else service.value(raw)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def property_records(request, pk):
    if not service.can_act(request.user, "view"):
        raise PermissionDenied
    asset = get_object_or_404(Asset, pk=pk, department_id=gso_department_for_user(request.user).pk)
    can_record = service.can_act(request.user, "record", asset)
    if request.method == "POST" and not can_record:
        raise PermissionDenied
    previous = service.latest_verified(asset)
    source_error = ""
    try:
        basis = service.source_basis(asset)
    except ValidationError as error:
        basis = None
        source_error = " ".join(error.messages)
    token = signing.dumps({"actor": request.user.pk, "asset": str(asset.public_id), "source": basis,
        "previous": str(previous.public_id) if previous else None, "request_id": str(uuid4())}, salt=SALT)
    form = PropertyForm(request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None, initial={"source_token": token})
    if request.method == "POST" and form.is_valid():
        try:
            fields = dict(form.cleaned_data)
            payload = signing.loads(fields.pop("source_token"), salt=SALT, max_age=1800)
            if payload["actor"] != request.user.pk or payload["asset"] != str(asset.public_id):
                raise PermissionDenied
            upload = fields.pop("upload")
            row = service.record(actor=request.user, asset=asset, request_id=payload["request_id"],
                expected_source=payload["source"], expected_predecessor=payload["previous"], data=fields, upload=upload)
        except signing.BadSignature:
            form.add_error(None, "The source form expired or changed. Check existing records, then reopen it.")
        except ValidationError as error:
            form.add_error(None, " ".join(error.messages))
        else:
            return redirect("inventory:property-detail", pk=row.pk)
    rows = service.visible(request.user).filter(asset=asset)
    return render(request, "inventory/property_records.html", {"asset": asset, "form": form,
        "page": Paginator(rows, 25).get_page(request.GET.get("page")), "previous": previous,
        "can_record": can_record, "source_error": source_error,
        "pending": rows.filter(status="pending").exists()})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def property_detail(request, pk):
    row = get_object_or_404(service.visible(request.user).select_related("asset", "predecessor"), pk=pk)
    operation = request.POST.get("operation", "") if request.method == "POST" else ""
    version = PropertyVersionForm(request.POST if request.method == "POST" else None)
    forms = {name: PropertyDecisionForm(request.POST if operation == name else None, prefix=name) for name in ("verify", "reject", "cancel")}
    review = service.can_act(request.user, "review", row.asset) and row.recorded_by_id != request.user.pk
    record = service.can_act(request.user, "record", row.asset)
    if request.method == "POST":
        if operation not in forms:
            version.add_error(None, "Choose a supported property action.")
        else:
            if not (record if operation == "cancel" else review):
                raise PermissionDenied
            if version.is_valid() and forms[operation].is_valid():
                try:
                    service.decide(actor=request.user, row=row, expected_version=version.cleaned_data["expected_version"],
                        action=operation, **forms[operation].cleaned_data)
                except ValidationError as error:
                    version.add_error(None, " ".join(error.messages))
                else:
                    return redirect("inventory:property-detail", pk=row.pk)
    integrity_error = ""
    try:
        service.verify_history(row)
        service.verify_source(row)
        stale = service.source_basis(row.asset) != row.source_snapshot
    except ValidationError as error:
        integrity_error, stale = " ".join(error.messages), True
    latest = service.latest_verified(row.asset)
    can_request_finance = False
    if apps.is_installed("inventory_finance"):
        from inventory_finance.property_links import gso_allowed
        can_request_finance = gso_allowed(request.user, row, "request")
    return render(request, "inventory/property_detail.html", {"record": row, "version": version,
        "can_request_finance": can_request_finance,
        "verify_form": forms["verify"], "reject_form": forms["reject"], "cancel_form": forms["cancel"],
        "can_review": review and row.status == "pending", "can_cancel": record and row.status == "pending",
        "integrity_error": integrity_error, "stale": stale, "latest": latest,
        "basis_facts": [(Asset._meta.get_field(name).verbose_name, display_value(Asset, name, row.source_snapshot.get("facts", {}).get(name))) for name in service.ASSET_FIELDS],
        "facts": [(PropertyForm.Meta.labels.get(name, row._meta.get_field(name).verbose_name), display_value(type(row), name, getattr(row, name))) for name in service.CONTENT_FIELDS]})


@never_cache
@login_required
@require_GET
def property_evidence(request, pk):
    row = get_object_or_404(service.visible(request.user), pk=pk)
    try:
        source = service.verify_source(row).open("rb")
    except (OSError, ValidationError):
        raise Http404("Property evidence is unavailable or needs integrity review.")
    response = FileResponse(source, as_attachment=True, filename=row.original_filename, content_type="application/octet-stream")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
