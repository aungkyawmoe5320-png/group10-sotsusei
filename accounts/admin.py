from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CareRecipient, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "name", "phone", "is_staff")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "name", "phone")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("基本情報", {"fields": ("name", "phone")}),
        ("権限", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("日時", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "name", "password1", "password2")}),
    )


@admin.register(CareRecipient)
class CareRecipientAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "relation", "age")
    search_fields = ("name", "user__email")