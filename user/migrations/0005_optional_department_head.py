from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("user", "0004_department_slug")]

    operations = [
        migrations.AlterField(
            model_name="department",
            name="dept_head",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="user.departmenthead"),
        ),
    ]
