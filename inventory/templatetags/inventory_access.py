"""Navigation uses the same scoped read checks as inventory views."""
from django import template
from inventory.access import can, can_stock
from inventory.receiving import can_receiving

register = template.Library()


@register.simple_tag
def inventory_navigation(user):
    return {"assets": can(user, "view"), "stock": can_stock(user, "view"),
            "receiving": can_receiving(user, "view")}
