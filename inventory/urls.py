from django.urls import path

from . import views
from . import receiving_views
from . import maintenance_views
from . import employee_custody_views
from . import custody_review
from . import custody_return_views

app_name = "inventory"

urlpatterns = [
    path("custody-returns/", custody_return_views.return_list, name="custody-return-list"),
    path("<int:pk>/custody-return/", custody_return_views.return_start, name="custody-return-start"),
    path("custody-returns/<int:pk>/", custody_return_views.return_detail, name="custody-return-detail"),
    path("custody-returns/evidence/<int:pk>/", custody_return_views.return_evidence, name="custody-return-evidence"),
    path("custody/", custody_review.custody_review, name="custody-review"),
    path("<int:pk>/employee-handoff/", employee_custody_views.employee_handoff, name="employee-handoff"),
    path("maintenance/", maintenance_views.maintenance_list, name="maintenance-list"),
    path("<int:pk>/maintenance/new/", maintenance_views.maintenance_open, name="maintenance-open"),
    path("maintenance/<int:pk>/", maintenance_views.maintenance_detail, name="maintenance-detail"),
    path("maintenance/evidence/<int:pk>/", maintenance_views.maintenance_evidence, name="maintenance-evidence"),
    path("receiving/", receiving_views.receipt_list, name="receiving-list"),
    path("receiving/new/", receiving_views.receipt_create, name="receiving-create"),
    path("receiving/<int:pk>/", receiving_views.receipt_detail, name="receiving-detail"),
    path("receiving/evidence/<int:pk>/", receiving_views.evidence_download, name="receiving-evidence"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("", views.asset_list, name="asset-list"),
    path("add/", views.asset_create, name="asset-create"),
    path("<int:pk>/", views.asset_detail, name="asset-detail"),
    path("<int:pk>/edit/", views.asset_edit, name="asset-edit"),
    path("<int:pk>/retire/", views.asset_retire, name="asset-retire"),
    path("transfers/", views.asset_transfer_list, name="asset-transfer-list"),
    path("<int:pk>/transfer/", views.asset_transfer_create, name="asset-transfer-create"),
    path("transfers/<int:pk>/acknowledge/", views.asset_transfer_acknowledge, name="asset-transfer-acknowledge"),
    path("transfers/<int:pk>/cancel/", views.asset_transfer_cancel, name="asset-transfer-cancel"),
    path("disposals/", views.asset_disposal_list, name="asset-disposal-list"),
    path("<int:pk>/disposal-request/", views.asset_disposal_request, name="asset-disposal-request"),
    path("disposals/<int:pk>/", views.asset_disposal_detail, name="asset-disposal-detail"),
    path("disposal-attachments/<int:pk>/", views.disposal_attachment_download, name="disposal-attachment-download"),
    path("verifications/", views.asset_verification_list, name="asset-verification-list"),
    path("verifications/<int:pk>/", views.asset_verification_detail, name="asset-verification-detail"),
    path("verifications/records/<int:pk>/", views.asset_verification_record, name="asset-verification-record"),
    path("verifications/records/<int:pk>/follow-up/", views.asset_verification_followup, name="asset-verification-followup"),
    path("verifications/<int:pk>/findings/add/", views.asset_verification_finding_add, name="asset-verification-finding-add"),
    path("verifications/findings/<int:pk>/review/", views.asset_verification_finding_review, name="asset-verification-finding-review"),
    path("verifications/<int:pk>/reconcile/", views.asset_verification_reconcile, name="asset-verification-reconcile"),
    path("verifications/accounting-template.csv", views.asset_accounting_template, name="asset-accounting-template"),
    path("verifications/accounting-snapshots/<int:pk>/", views.asset_accounting_source_download, name="asset-accounting-source-download"),
    path("verifications/<int:pk>/reconciliation.csv", views.asset_verification_reconciliation_export, name="asset-verification-reconciliation-export"),
    path("export/assets.csv", views.asset_export, name="asset-export"),
    path("consumables/", views.consumable_list, name="consumable-list"),
    path("consumables/export/movements.csv", views.stock_export, name="stock-export"),
    path("consumables/add/", views.consumable_create, name="consumable-create"),
    path("consumables/<int:pk>/edit/", views.consumable_edit, name="consumable-edit"),
    path("consumables/<int:pk>/", views.consumable_detail, name="consumable-detail"),
    path("consumables/<int:pk>/receive/", views.stock_receive, name="stock-receive"),
    path("consumables/<int:pk>/issue/", views.stock_issue, name="stock-issue"),
    path("consumables/<int:pk>/adjust/", views.stock_adjust, name="stock-adjust"),
]
