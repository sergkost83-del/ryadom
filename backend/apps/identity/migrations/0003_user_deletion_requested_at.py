from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0002_auth_sessions_consents"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="deletion_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
