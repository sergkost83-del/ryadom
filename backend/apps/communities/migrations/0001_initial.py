import uuid

import django.db.models.deletion
from django.db import migrations, models


def base_fields():
    return [
        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("updated_at", models.DateTimeField(auto_now=True)),
    ]


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Region",
            fields=base_fields() + [("name", models.CharField(max_length=120, unique=True))],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Locality",
            fields=base_fields()
            + [
                ("name", models.CharField(max_length=120)),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="localities", to="communities.region"
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Community",
            fields=base_fields()
            + [
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=80)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "locality",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="communities",
                        to="communities.locality",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Street",
            fields=base_fields()
            + [
                ("name", models.CharField(max_length=120)),
                (
                    "community",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="streets", to="communities.community"
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Building",
            fields=base_fields()
            + [
                ("label", models.CharField(max_length=40)),
                ("slug", models.SlugField(max_length=40)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "street",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="buildings", to="communities.street"
                    ),
                ),
            ],
            options={"ordering": ["label"]},
        ),
        migrations.AddConstraint(
            model_name="locality",
            constraint=models.UniqueConstraint(fields=("region", "name"), name="communities_locality_unique_name"),
        ),
        migrations.AddConstraint(
            model_name="community",
            constraint=models.UniqueConstraint(fields=("locality", "slug"), name="communities_community_unique_slug"),
        ),
        migrations.AddConstraint(
            model_name="community",
            constraint=models.UniqueConstraint(fields=("locality", "name"), name="communities_community_unique_name"),
        ),
        migrations.AddConstraint(
            model_name="street",
            constraint=models.UniqueConstraint(fields=("community", "name"), name="communities_street_unique_name"),
        ),
        migrations.AddConstraint(
            model_name="building",
            constraint=models.UniqueConstraint(fields=("street", "slug"), name="communities_building_unique_slug"),
        ),
        migrations.AddConstraint(
            model_name="building",
            constraint=models.UniqueConstraint(fields=("street", "label"), name="communities_building_unique_label"),
        ),
    ]
