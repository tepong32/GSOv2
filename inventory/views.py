import csv

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Sum
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .access import (
    _is_gso_department, asset_access_required, asset_in_scope, can,
    can_acknowledge_asset_transfer, can_request_asset_disposal,
    can_review_asset_disposal, can_stock, can_transfer_asset, can_view_audit,
    department_for_user, department_model, gso_department_for_user,
)
from .forms import (
    AssetDisposalRequestForm, AssetDisposalResponseForm, AssetDisposalReviewForm,
    AssetForm, AssetTransferForm, ConsumableItemForm, StockAdjustmentForm,
    StockIssueForm, StockReceiptForm, TransferCancellationForm,
)
from .models import Asset, AssetDisposalAttachment, AssetDisposalCase, AssetTransfer, ConsumableItem, StockMovement
from .services import (
    acknowledge_asset_transfer, cancel_asset_transfer, create_asset,
    create_asset_transfer, create_consumable, record_stock_movement,
    respond_to_disposal_case, review_asset_disposal_case,
    submit_asset_disposal_request, update_asset, update_consumable,
)


def _csv_cell(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def _scoped_assets(user):
    if user.is_superuser:
        return Asset.objects.all()
    department = department_for_user(user)
    if not department:
        raise PermissionDenied
    if _is_gso_department(department):
        return Asset.objects.filter(department_id=department.pk)
    return Asset.objects.filter(assigned_department_id=department.pk)


@asset_access_required("view")
def dashboard(request):
    assets = _scoped_assets(request.user)
    return render(request, "inventory/dashboard.html", {
        "department": department_for_user(request.user) or gso_department_for_user(request.user),
        "is_gso": request.user.is_superuser or _is_gso_department(department_for_user(request.user)),
        "total_assets": assets.count(),
        "in_service_count": assets.filter(status=Asset.ACTIVE).count(),
        "maintenance_count": assets.filter(status=Asset.MAINTENANCE).count(),
        "retired_count": assets.filter(status=Asset.RETIRED).count(),
        "can_add": can(request.user, "add"),
        "can_view_stock": can_stock(request.user, "view"),
        "can_view_transfers": can_transfer_asset(request.user) or can_acknowledge_asset_transfer(request.user),
        "pending_transfer_count": _transfer_queryset(request.user).filter(status=AssetTransfer.PENDING).count()
        if can_transfer_asset(request.user) or can_acknowledge_asset_transfer(request.user) else 0,
        "can_view_disposals": can_review_asset_disposal(request.user) or can_request_asset_disposal(request.user),
        "open_disposal_count": _disposal_queryset(request.user).filter(status__in=(
            AssetDisposalCase.SUBMITTED, AssetDisposalCase.UNDER_REVIEW,
            AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.AUTHORIZED,
        )).count() if can_review_asset_disposal(request.user) or can_request_asset_disposal(request.user) else 0,
    })


@asset_access_required("view")
def asset_list(request):
    assets = _scoped_assets(request.user)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    inventory_class = request.GET.get("class", "").strip()
    if query:
        class_matches = [
            value for value, label in Asset.INVENTORY_CLASS_CHOICES
            if query.casefold() in label.casefold()
        ]
        item_type_matches = [
            value for value, label in Asset.ITEM_TYPE_CHOICES
            if query.casefold() in label.casefold()
        ]
        assets = assets.filter(
            Q(asset_name__icontains=query) | Q(inventory_class__icontains=query)
            | Q(inventory_class__in=class_matches) | Q(item_type__icontains=query)
            | Q(item_type__in=item_type_matches) | Q(category__icontains=query)
            | Q(property_tag__icontains=query)
            | Q(brand__icontains=query) | Q(serial_number__icontains=query)
            | Q(obr_reference__icontains=query) | Q(assigned_office__icontains=query)
        )
    if status in dict(Asset.STATUS_CHOICES):
        assets = assets.filter(status=status)
    if inventory_class in dict(Asset.INVENTORY_CLASS_CHOICES):
        assets = assets.filter(inventory_class=inventory_class)
    page = Paginator(assets, 25).get_page(request.GET.get("page"))
    return render(request, "inventory/asset_list.html", {
        "page": page, "query": query, "selected_status": status,
        "selected_class": inventory_class,
        "inventory_classes": Asset.INVENTORY_CLASS_CHOICES,
        "statuses": Asset.STATUS_CHOICES,
        "can_add": can(request.user, "add"),
        "can_change": can(request.user, "change"),
        "can_retire": can(request.user, "delete"),
        "can_export": can(request.user, "export"),
    })


@asset_access_required("export")
def asset_export(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="gso-asset-register.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow((
        "Property tag", "Asset type", "Inventory class", "Item type", "Name", "Additional description", "Brand", "Model", "Serial number",
        "Plate number", "Engine number", "Chassis number", "Status", "Department", "Office / custodian",
        "Acquisition date", "Acquisition cost", "Fund", "COA account code", "COA account title",
        "Mapping reference", "OBR", "PO / contract", "Voucher", "Journal",
    ))
    for asset in _scoped_assets(request.user).order_by("asset_name", "pk"):
        writer.writerow(_csv_cell(value) for value in (
            asset.property_tag, asset.get_asset_kind_display(), asset.get_inventory_class_display(),
            asset.get_item_type_display(), asset.asset_name, asset.category, asset.brand,
            asset.model_number, asset.serial_number, asset.plate_number, asset.engine_number, asset.chassis_number,
            asset.get_status_display(), asset.assigned_department_label, asset.assigned_office,
            asset.purchase_date or "", asset.unit_cost or "", asset.fund_code, asset.coa_account_code,
            asset.coa_account_title, asset.coa_basis, asset.obr_reference, asset.purchase_order_reference,
            asset.voucher_reference, asset.journal_reference,
        ))
    return response


@asset_access_required("view")
def asset_detail(request, pk):
    asset = get_object_or_404(_scoped_assets(request.user), pk=pk)
    pending_transfer = asset.transfers.filter(status=AssetTransfer.PENDING).first()
    return render(request, "inventory/asset_detail.html", {
        "asset": asset,
        "events": asset.audit_events.all() if can_view_audit(request.user) else (),
        "can_change": can(request.user, "change"),
        "can_retire": can(request.user, "delete"),
        "can_view_audit": can_view_audit(request.user),
        "can_transfer": can_transfer_asset(request.user) and pending_transfer is None and asset.status != Asset.RETIRED,
        "pending_transfer": pending_transfer,
        "transfer_history": asset.transfers.all() if can_view_audit(request.user) else (),
        "can_request_disposal": can_request_asset_disposal(request.user, asset)
        and not asset.transfers.filter(status=AssetTransfer.PENDING).exists()
        and not asset.disposal_cases.filter(status__in=(
            AssetDisposalCase.SUBMITTED, AssetDisposalCase.UNDER_REVIEW,
            AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.AUTHORIZED,
        )).exists() and asset.status != Asset.RETIRED,
        "disposal_case": asset.disposal_cases.exclude(status=AssetDisposalCase.REJECTED).first(),
    })


@asset_access_required("add")
def asset_create(request):
    form = AssetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        asset = create_asset(actor=request.user, data=form.cleaned_data)
        messages.success(request, "Asset added to the register.")
        return redirect("inventory:asset-detail", pk=asset.pk)
    return render(request, "inventory/asset_form.html", {"form": form, "heading": "Add an asset"})


@asset_access_required("change")
def asset_edit(request, pk):
    asset = get_object_or_404(_scoped_assets(request.user), pk=pk)
    if asset.status == Asset.RETIRED:
        raise PermissionDenied("Retired asset records are read-only.")
    if asset.transfers.filter(status=AssetTransfer.PENDING).exists():
        messages.error(request, "This asset has a handoff waiting for acknowledgment. Cancel it before editing the record.")
        return redirect("inventory:asset-detail", pk=asset.pk)
    if asset.disposal_cases.filter(status__in=(
        AssetDisposalCase.SUBMITTED, AssetDisposalCase.UNDER_REVIEW,
        AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.AUTHORIZED,
    )).exists():
        messages.error(request, "This asset has an open disposal case and cannot be edited.")
        return redirect("inventory:asset-detail", pk=asset.pk)
    form = AssetForm(request.POST or None, instance=asset)
    if request.method == "POST" and form.is_valid():
        asset = update_asset(actor=request.user, asset=asset, data=form.cleaned_data)
        messages.success(request, "Asset record updated.")
        return redirect("inventory:asset-detail", pk=asset.pk)
    return render(request, "inventory/asset_form.html", {"form": form, "asset": asset, "heading": "Edit asset"})


@asset_access_required("delete")
@require_POST
def asset_retire(request, pk):
    asset = get_object_or_404(_scoped_assets(request.user), pk=pk)
    messages.info(request, "Assets must be retired through a reviewed disposal case.")
    if can_request_asset_disposal(request.user, asset):
        return redirect("inventory:asset-disposal-request", pk=asset.pk)
    return redirect("inventory:asset-detail", pk=asset.pk)


def _transfer_queryset(user):
    transfers = AssetTransfer.objects.select_related("asset", "requested_by", "acknowledged_by", "cancelled_by")
    if user.is_superuser:
        return transfers
    department = department_for_user(user)
    if not department:
        return transfers.none()
    if _is_gso_department(department):
        return transfers.filter(asset__department_id=department.pk)
    return transfers.filter(destination_department_id=department.pk)


@asset_access_required("view")
def asset_transfer_list(request):
    if not (can_transfer_asset(request.user) or can_acknowledge_asset_transfer(request.user)):
        raise PermissionDenied
    rows = list(_transfer_queryset(request.user))
    for transfer in rows:
        transfer.user_can_acknowledge = can_acknowledge_asset_transfer(request.user, transfer)
        transfer.user_can_view_asset = asset_in_scope(request.user, transfer.asset)
    return render(request, "inventory/asset_transfer_list.html", {
        "transfers": rows,
        "is_gso": can_transfer_asset(request.user),
        "can_cancel": can_transfer_asset(request.user),
        "can_acknowledge": can_acknowledge_asset_transfer(request.user),
    })


@asset_access_required("view")
def asset_transfer_create(request, pk):
    if not can_transfer_asset(request.user):
        raise PermissionDenied
    asset = get_object_or_404(_scoped_assets(request.user), pk=pk)
    if asset.status == Asset.RETIRED or asset.transfers.filter(status=AssetTransfer.PENDING).exists():
        messages.error(request, "This asset cannot start another handoff right now.")
        return redirect("inventory:asset-detail", pk=asset.pk)
    form = AssetTransferForm(request.POST or None, asset=asset)
    if request.method == "POST" and form.is_valid():
        try:
            transfer = create_asset_transfer(actor=request.user, asset=asset, data=form.cleaned_data)
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Handoff sent. The receiving department must acknowledge it before the assignment changes.")
            return redirect("inventory:asset-detail", pk=transfer.asset_id)
    return render(request, "inventory/asset_transfer_form.html", {"form": form, "asset": asset})


@asset_access_required("view")
@require_POST
def asset_transfer_acknowledge(request, pk):
    transfer = get_object_or_404(_transfer_queryset(request.user), pk=pk)
    try:
        acknowledge_asset_transfer(actor=request.user, transfer=transfer)
    except (PermissionDenied, ValidationError) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Handoff acknowledged. The asset is now assigned to your department.")
    return redirect("inventory:asset-transfer-list")


@asset_access_required("view")
@require_POST
def asset_transfer_cancel(request, pk):
    transfer = get_object_or_404(_transfer_queryset(request.user), pk=pk)
    form = TransferCancellationForm(request.POST)
    if form.is_valid():
        try:
            cancel_asset_transfer(actor=request.user, transfer=transfer, reason=form.cleaned_data["reason"])
        except (PermissionDenied, ValidationError) as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Pending handoff cancelled; the current assignment is unchanged.")
    else:
        messages.error(request, "Enter a reason before cancelling the handoff.")
    return redirect("inventory:asset-transfer-list")


def _disposal_queryset(user):
    cases = AssetDisposalCase.objects.select_related("asset", "submitted_by", "reviewed_by", "completed_by")
    if can_review_asset_disposal(user):
        if user.is_superuser:
            return cases
        gso = gso_department_for_user(user)
        return cases.filter(asset__department_id=gso.pk) if gso else cases.none()
    department = department_for_user(user)
    if not department:
        return cases.none()
    return cases.filter(asset__assigned_department_id=department.pk)


@asset_access_required("view")
def asset_disposal_list(request):
    if not (can_review_asset_disposal(request.user) or can_request_asset_disposal(request.user)):
        raise PermissionDenied
    return render(request, "inventory/asset_disposal_list.html", {
        "cases": _disposal_queryset(request.user),
        "can_review": can_review_asset_disposal(request.user),
    })


@asset_access_required("view")
def asset_disposal_request(request, pk):
    asset = get_object_or_404(_scoped_assets(request.user), pk=pk)
    if not can_request_asset_disposal(request.user, asset):
        raise PermissionDenied
    open_statuses = (
        AssetDisposalCase.SUBMITTED, AssetDisposalCase.UNDER_REVIEW,
        AssetDisposalCase.NEEDS_INFORMATION, AssetDisposalCase.AUTHORIZED,
    )
    if asset.disposal_cases.filter(status__in=open_statuses).exists():
        messages.info(request, "There is already an open disposal request for this asset.")
        return redirect("inventory:asset-detail", pk=asset.pk)
    form = AssetDisposalRequestForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            case = submit_asset_disposal_request(actor=request.user, asset=asset, data=form.cleaned_data)
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Request sent to GSO with its photo and signed form.")
            return redirect("inventory:asset-disposal-detail", pk=case.pk)
    return render(request, "inventory/asset_disposal_request.html", {"form": form, "asset": asset})


@asset_access_required("view")
def asset_disposal_detail(request, pk):
    case = get_object_or_404(_disposal_queryset(request.user), pk=pk)
    reviewer = can_review_asset_disposal(request.user) and asset_in_scope(request.user, case.asset)
    requester = case.submitted_by_id == request.user.pk and can_request_asset_disposal(request.user, case.asset)
    review_form = AssetDisposalReviewForm(request.POST or None, request.FILES or None, case=case) if reviewer else None
    response_form = AssetDisposalResponseForm(request.POST or None, request.FILES or None) if requester and case.status == AssetDisposalCase.NEEDS_INFORMATION else None
    if request.method == "POST":
        if reviewer and review_form and review_form.is_valid():
            try:
                review_asset_disposal_case(actor=request.user, case=case, data=review_form.cleaned_data)
            except (PermissionDenied, ValidationError) as error:
                review_form.add_error(None, error)
            else:
                messages.success(request, "Disposal case updated and recorded in its history.")
                return redirect("inventory:asset-disposal-detail", pk=case.pk)
        elif response_form and response_form.is_valid():
            try:
                respond_to_disposal_case(actor=request.user, case=case, data=response_form.cleaned_data)
            except (PermissionDenied, ValidationError) as error:
                response_form.add_error(None, error)
            else:
                messages.success(request, "Your response was sent to GSO.")
                return redirect("inventory:asset-disposal-detail", pk=case.pk)
        elif not reviewer and not response_form:
            raise PermissionDenied
    return render(request, "inventory/asset_disposal_detail.html", {
        "case": case, "attachments": case.attachments.all(),
        "events": case.events.select_related("actor").all(),
        "reviewer": reviewer, "requester": requester,
        "review_form": review_form, "response_form": response_form,
    })


@asset_access_required("view")
def disposal_attachment_download(request, pk):
    attachment = get_object_or_404(
        AssetDisposalAttachment.objects.select_related("disposal_case__asset"), pk=pk,
    )
    case = attachment.disposal_case
    if not (asset_in_scope(request.user, case.asset)
            or (case.submitted_by_id == request.user.pk and request.user.has_perm("inventory.request_asset_disposal"))):
        raise PermissionDenied
    response = FileResponse(
        attachment.file.open("rb"), as_attachment=True,
        content_type=attachment.content_type,
        filename=attachment.file.name.rsplit("/", 1)[-1],
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


def _stock_items(user):
    items = ConsumableItem.objects.all()
    department = department_for_user(user)
    if user.is_superuser or _is_gso_department(department):
        return items
    if not department:
        raise PermissionDenied
    return items.filter(movements__department_id=department.pk).distinct()


def stock_access_required(action="view"):
    from functools import wraps
    from django.contrib.auth.views import redirect_to_login

    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not can_stock(request.user, action):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


@stock_access_required()
def consumable_list(request):
    items = _stock_items(request.user).annotate(on_hand_value=Sum("movements__signed_quantity"))
    query = request.GET.get("q", "").strip()
    if query:
        items = items.filter(Q(name__icontains=query) | Q(category__icontains=query))
    return render(request, "inventory/consumable_list.html", {
        "items": items, "query": query,
        "is_gso": request.user.is_superuser or _is_gso_department(department_for_user(request.user)),
        "can_add": can_stock(request.user, "add"),
        "can_receive": can_stock(request.user, "receive"),
        "can_export": can_stock(request.user, "export"),
    })


@stock_access_required("export")
def stock_export(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="gso-consumable-movements.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow((
        "Supply item", "Category", "Unit", "Movement", "Date", "Quantity", "Signed quantity",
        "Department", "Recipient", "Reference", "Reason", "Unit cost", "Recorded by",
    ))
    movements = StockMovement.objects.select_related("item", "actor").order_by("occurred_at", "pk")
    for movement in movements:
        writer.writerow(_csv_cell(value) for value in (
            movement.item.name, movement.item.category, movement.item.unit, movement.get_kind_display(),
            movement.occurred_at.isoformat(), movement.quantity, movement.signed_quantity,
            movement.department_label, movement.recipient, movement.reference, movement.reason,
            movement.unit_cost or "", movement.actor or "",
        ))
    return response


@stock_access_required("add")
def consumable_create(request):
    form = ConsumableItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = create_consumable(actor=request.user, data=form.cleaned_data)
        messages.success(request, "Supply item added. You can now record stock received.")
        return redirect("inventory:consumable-detail", pk=item.pk)
    return render(request, "inventory/consumable_form.html", {"form": form, "heading": "Add a supply item"})


@stock_access_required("change")
def consumable_edit(request, pk):
    item = get_object_or_404(ConsumableItem, pk=pk)
    form = ConsumableItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        try:
            item = update_consumable(actor=request.user, item=item, data=form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Supply item details updated and recorded in its history.")
            return redirect("inventory:consumable-detail", pk=item.pk)
    return render(request, "inventory/consumable_form.html", {"form": form, "item": item, "heading": "Edit supply item"})


@stock_access_required()
def consumable_detail(request, pk):
    item = get_object_or_404(_stock_items(request.user), pk=pk)
    movements = item.movements.all()
    department = department_for_user(request.user)
    is_gso = request.user.is_superuser or _is_gso_department(department)
    if not is_gso:
        movements = movements.filter(department_id=department.pk)
    page = Paginator(movements.select_related("actor"), 50).get_page(request.GET.get("page"))
    audit_events = item.audit_events.all() if is_gso and request.user.has_perm("inventory.view_stock_audit") else ()
    return render(request, "inventory/consumable_detail.html", {
        "item": item, "page": page, "is_gso": is_gso, "audit_events": audit_events,
        "can_receive": can_stock(request.user, "receive"),
        "can_issue": can_stock(request.user, "issue"),
        "can_adjust": can_stock(request.user, "adjust"),
        "can_change": can_stock(request.user, "change"),
    })


@stock_access_required("receive")
def stock_receive(request, pk):
    item = get_object_or_404(ConsumableItem, pk=pk)
    form = StockReceiptForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            record_stock_movement(
                actor=request.user, item=item, kind=StockMovement.RECEIPT, **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Stock receipt recorded.")
            return redirect("inventory:consumable-detail", pk=item.pk)
    return render(request, "inventory/stock_movement_form.html", {"form": form, "item": item, "heading": "Record received stock"})


@stock_access_required("issue")
def stock_issue(request, pk):
    item = get_object_or_404(ConsumableItem, pk=pk)
    form = StockIssueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        department = _resolve_department(data.pop("department"))
        try:
            record_stock_movement(
                actor=request.user, item=item, kind=StockMovement.ISSUE,
                department_id=department.pk, department_label=department.name, **data,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Supply issue recorded.")
            return redirect("inventory:consumable-detail", pk=item.pk)
    return render(request, "inventory/stock_movement_form.html", {"form": form, "item": item, "heading": "Issue supplies"})


@stock_access_required("adjust")
def stock_adjust(request, pk):
    item = get_object_or_404(ConsumableItem, pk=pk)
    form = StockAdjustmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        kind = StockMovement.ADJUSTMENT_IN if data["direction"] == "in" else StockMovement.ADJUSTMENT_OUT
        try:
            record_stock_movement(
                actor=request.user, item=item, kind=kind, quantity=data["quantity"], reason=data["reason"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Stock adjustment recorded with its reason.")
            return redirect("inventory:consumable-detail", pk=item.pk)
    return render(request, "inventory/stock_movement_form.html", {"form": form, "item": item, "heading": "Adjust stock balance"})


def _resolve_department(pk):
    model = department_model()
    department = model.objects.filter(pk=pk).first() if model else None
    if department is None:
        raise PermissionDenied("The selected department is no longer available.")
    return department
