from django.contrib import admin
from .models import DepartmentHead, Department, User

# Register your models here.

admin.site.register(DepartmentHead)
admin.site.register(Department)
admin.site.register(User)
