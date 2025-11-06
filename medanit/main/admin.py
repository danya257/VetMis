from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json

from .models import (
    # Core domain
    Animal, Vaccination, Service, AnimalService,
    # Blog
    BlogCategory, BlogArticle,
    # Clinics and related (without Cal.com)
    Clinic, VetProfile, Appointment,
    # Pricing and availability
    ClinicService, VetAvailability,
)


def register_safe(model, admin_class=None):
    """
    Register model in admin, ignore if already registered elsewhere.
    Useful in monoliths with partial registrations.
    """
    try:
        if admin_class:
            admin.site.register(model, admin_class)
        else:
            admin.site.register(model)
    except AlreadyRegistered:
        pass


# =======================
# Inlines
# =======================

class VetProfileInline(admin.TabularInline):
    model = VetProfile
    extra = 0
    fields = ("full_name", "specialties", "user", "is_active")
    autocomplete_fields = ("user",)
    show_change_link = True


class ClinicServiceInline(admin.TabularInline):
    model = ClinicService
    extra = 0
    autocomplete_fields = ("service",)
    fields = ("service", "price", "currency", "default_duration_minutes", "is_active", "sort_order")
    show_change_link = True


# =======================
# Clinics and related
# =======================

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "is_demo",
        "timezone",
    )
    list_filter = ("is_demo", "timezone")
    search_fields = ("name", "slug", "address", "phone", "email", "owner__username", "owner__first_name", "owner__last_name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [VetProfileInline, ClinicServiceInline]

    fieldsets = (
        ("Основное", {
            "fields": ("name", "slug", "description", "address", "phone", "email", "website", "timezone", "owner", "is_demo"),
        }),
    )


@admin.register(VetProfile)
class VetProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "clinic", "specialties", "is_active", "user")
    list_filter = ("clinic", "is_active")
    search_fields = ("full_name", "specialties", "clinic__name", "user__username")
    autocomplete_fields = ("clinic", "user")


@admin.register(VetAvailability)
class VetAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("clinic", "vet", "weekday", "date", "start_time", "end_time", "slot_minutes", "is_active")
    list_filter = ("clinic", "vet", "weekday", "date", "is_active")
    search_fields = ("vet__full_name", "clinic__name")
    list_editable = ("is_active",)
    autocomplete_fields = ("clinic", "vet")


@admin.register(ClinicService)
class ClinicServiceAdmin(admin.ModelAdmin):
    list_display = ("clinic", "service", "price", "currency", "default_duration_minutes", "is_active", "sort_order")
    list_filter = ("clinic", "is_active", "currency")
    search_fields = ("service__name", "clinic__name")
    list_editable = ("price", "is_active", "sort_order")
    autocomplete_fields = ("clinic", "service")


# =======================
# Appointments
# =======================

@admin.action(description="Отметить как Завершена")
def mark_completed(modeladmin, request, queryset):
    queryset.update(status="completed")


@admin.action(description="Отметить как Отменена")
def mark_cancelled(modeladmin, request, queryset):
    queryset.update(status="cancelled")


@admin.action(description="Отметить как Перенесена")
def mark_rescheduled(modeladmin, request, queryset):
    queryset.update(status="rescheduled")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("start_at", "clinic", "vet", "animal", "booker", "status")
    list_filter = ("clinic", "vet", "status", "start_at")
    search_fields = (
        "vet__full_name",
        "clinic__name",
        "animal__name",
        "booker__username",
        "booker__first_name",
        "booker__last_name",
    )
    date_hierarchy = "start_at"
    autocomplete_fields = ("clinic", "vet", "animal", "booker")
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Основное", {"fields": ("clinic", "vet", "animal", "booker", "status", "notes")}),
        ("Время", {"fields": ("start_at", "end_at", "timezone")}),
        ("Служебные поля", {"fields": ("created_at", "updated_at")}),
    )
    actions = [mark_completed, mark_cancelled, mark_rescheduled]


# =======================
# Existing domain models (safe register)
# =======================

class AnimalAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "breed", "owner", "birthday")
    list_filter = ("species",)
    search_fields = ("name", "breed", "owner__username", "owner__first_name", "owner__last_name")
    autocomplete_fields = ("owner",)


class VaccinationAdmin(admin.ModelAdmin):
    list_display = ("name", "animal", "date")
    list_filter = ("name", "date")
    search_fields = ("name", "animal__name")
    autocomplete_fields = ("animal",)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_by")
    search_fields = ("name", "description")
    autocomplete_fields = ("created_by",)


class AnimalServiceAdmin(admin.ModelAdmin):
    list_display = ("animal", "service", "custom_service_name", "date", "clinic", "created_by", "cost", "is_custom")
    list_filter = ("clinic", "is_custom", "date", "service")
    search_fields = ("animal__name", "service__name", "custom_service_name", "created_by__username")
    autocomplete_fields = ("animal", "service", "created_by", "clinic")


class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class BlogArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "slug", "author", "is_published", "created_at")
    list_filter = ("category", "is_published", "created_at")
    search_fields = ("title", "slug", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "author")


# Safe registrations (in case some were registered in migrations or elsewhere)
register_safe(Animal, AnimalAdmin)
register_safe(Vaccination, VaccinationAdmin)
register_safe(Service, ServiceAdmin)
register_safe(AnimalService, AnimalServiceAdmin)
register_safe(BlogCategory, BlogCategoryAdmin)
register_safe(BlogArticle, BlogArticleAdmin)


# =======================
# Admin branding (optional)
# =======================
admin.site.site_header = "Админка VetMis"
admin.site.site_title = "Админка VetMis"
admin.site.index_title = "Управление данными"

