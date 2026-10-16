from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
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
