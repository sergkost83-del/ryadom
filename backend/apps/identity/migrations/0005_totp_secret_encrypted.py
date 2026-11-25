from django.db import migrations, models


def encrypt_existing_secrets(apps, schema_editor):
    from apps.identity import crypto

    Device = apps.get_model("identity", "TOTPDevice")
    for device in Device.objects.all():
        if not device.secret.startswith(crypto.PREFIX):
            device.secret = crypto.encrypt(device.secret)
            device.save(update_fields=["secret"])


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0004_totp_backup_codes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="totpdevice",
            name="secret",
            field=models.CharField(max_length=255),
        ),
        migrations.RunPython(encrypt_existing_secrets, migrations.RunPython.noop),
    ]
