from django.urls import path
from . import views

app_name = "inventory_finance"
urlpatterns = [
    path("", views.workbench, name="workbench"),
    path("case/<uuid:case_id>/propose/", views.propose, name="propose"),
    path("<uuid:attribution_id>/", views.detail, name="detail"),
]
