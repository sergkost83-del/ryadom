"""Иерархия: регион → населённый пункт → ЖК → улица → дом.

Идентификаторы — UUID: их нельзя перебирать подряд.
Связи PROTECT: случайное удаление родителя не удалит всё дерево.
"""

import uuid

from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Region(BaseModel):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Locality(BaseModel):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="localities")
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["region", "name"], name="communities_locality_unique_name"),
        ]

    def __str__(self):
        return self.name


class Community(BaseModel):
    """Жилой комплекс."""

    locality = models.ForeignKey(Locality, on_delete=models.PROTECT, related_name="communities")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["locality", "slug"], name="communities_community_unique_slug"),
            models.UniqueConstraint(fields=["locality", "name"], name="communities_community_unique_name"),
        ]

    def __str__(self):
        return self.name


class Street(BaseModel):
    community = models.ForeignKey(Community, on_delete=models.PROTECT, related_name="streets")
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["community", "name"], name="communities_street_unique_name"),
        ]

    def __str__(self):
        return self.name


class Building(BaseModel):
    """Дом (корпус). Основная единица, по которой разграничивается доступ жителей."""

    street = models.ForeignKey(Street, on_delete=models.PROTECT, related_name="buildings")
    label = models.CharField(max_length=40)
    slug = models.SlugField(max_length=40)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["label"]
        constraints = [
            models.UniqueConstraint(fields=["street", "slug"], name="communities_building_unique_slug"),
            models.UniqueConstraint(fields=["street", "label"], name="communities_building_unique_label"),
        ]

    @property
    def community(self):
        return self.street.community

    def __str__(self):
        return f"{self.street.name}, {self.label}"
