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
