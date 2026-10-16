from django.db import migrations, models
from django.utils.text import slugify


def populate_department_slugs(apps, schema_editor):
    Department = apps.get_model("user", "Department")
    for department in Department.objects.filter(slug__isnull=True).iterator():
        department.slug = slugify(department.name) or f"department-{department.pk}"
        department.save(update_fields=("slug",))


class Migration(migrations.Migration):
    dependencies = [("user", "0003_alter_user_middle_name")]

    operations = [
        migrations.AddField(
            model_name="department",
            name="slug",
            field=models.SlugField(blank=True, max_length=120, null=True, unique=True),
        ),
        migrations.RunPython(populate_department_slugs, migrations.RunPython.noop),
    ]
