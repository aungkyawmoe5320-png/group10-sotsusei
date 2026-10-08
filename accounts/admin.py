from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Facility, User


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("facility_code", "name")
    search_fields = ("facility_code", "name")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "name", "role", "facility", "is_staff")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("基本情報", {"fields": ("name", "role", "facility")}),
        ("権限", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("日時", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "name", "role", "facility", "password1", "password2")}),
    )
