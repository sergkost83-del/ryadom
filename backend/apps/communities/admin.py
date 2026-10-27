from django.contrib import admin

from .models import Building, Community, Locality, Region, Street


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    search_fields = ("name",)


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "locality", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(Street)
class StreetAdmin(admin.ModelAdmin):
    list_display = ("name", "community")
    search_fields = ("name",)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("label", "street", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("label", "street__name")
