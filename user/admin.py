from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Department, DepartmentHead, User


class AssignedDepartmentFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.exclude(name=Department.select).order_by("name")


class EmployeeCreationForm(AssignedDepartmentFormMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "department")


class EmployeeChangeForm(AssignedDepartmentFormMixin, UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class EmployeeUserAdmin(DjangoUserAdmin):
    add_form = EmployeeCreationForm
    form = EmployeeChangeForm
    list_display = ("username", "email", "department", "is_active", "is_staff")
    list_filter = ("department", "is_active", "is_staff", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("last_name", "first_name", "username")
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Employee information", {"fields": ("email", "first_name", "middle_name", "last_name", "ext_name", "image", "department")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": (
            "username", "email", "first_name", "last_name", "department", "password1", "password2",
        )}),
    )
    readonly_fields = ("date_joined", "last_login")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "dept_head")
    search_fields = ("name",)


admin.site.register(DepartmentHead)
