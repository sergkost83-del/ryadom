"""Иерархия: регион → населённый пункт → ЖК → улица → дом.

Идентификаторы — UUID: их нельзя перебирать подряд.
Связи PROTECT: случайное удаление родителя не удалит всё дерево.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


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


class Membership(BaseModel):
    """Принадлежность жителя дому. Доступ к закрытым данным дома определяется только подтверждённым членством."""

    ROLE_RESIDENT = "resident"
    ROLE_CHOICES = [(ROLE_RESIDENT, "Житель")]

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_REJECTED = "rejected"
    STATUS_ENDED = "ended"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает подтверждения"),
        (STATUS_CONFIRMED, "Подтверждён"),
        (STATUS_REJECTED, "Отклонён"),
        (STATUS_ENDED, "Завершён"),
    ]
    ACTIVE_STATUSES = [STATUS_PENDING, STATUS_CONFIRMED]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_RESIDENT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # На MVP у жителя один активный адрес; смена — через завершение старого и новую заявку.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status__in=["pending", "confirmed"]),
                name="communities_membership_one_active_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} → {self.building_id} ({self.status})"
