from django.contrib import admin

from .models import Medication, PreRegistration

class MedicationInline(admin.TabularInline):
    model = Medication
    extra = 1

@admin.register(PreRegistration)
class PreRegistrationAdmin(admin.ModelAdmin):
    list_display = ("condition", "user", "care_level", "created_at")
    inlines = [MedicationInline]

    