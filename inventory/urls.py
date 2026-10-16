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
]
