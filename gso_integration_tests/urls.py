"""Isolated integration routes; never edits the parallel GRAND checkout."""
from django.urls import include, path
from src.urls import urlpatterns as grand_patterns

urlpatterns = [*grand_patterns, path("gso/claim-support/", include("inventory_finance.urls")),
               path("gso/inventory/", include("inventory.urls"))]
