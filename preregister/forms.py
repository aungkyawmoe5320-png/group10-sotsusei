from django import forms
from django.db import transaction

from .models import CareLevel, Medication, PreRegistration, Timing

DEFAULT_TIMING = Timing.AFTER_BREAKFAST


class PreRegistrationForm(forms.ModelForm):
    class Meta:
        model = PreRegistration
        fields = ["diagnosis", "hospital", "care_level", "notes", "condition"]
        error_messages = {
            "diagnosis": {"max_length": "病名は50文字以内で入力してください。"},
            "hospital": {"max_length": "病院は50文字以内で入力してください。"},
            "care_level": {"invalid_choice": "要介護度を正しく選んでください。"},
            "notes": {
                "required": "注意事項を入力してください。",
                "max_length": "注意事項は500文字以内で入力してください。",
            },
            "condition": {
                "required": "身体状況を入力してください。",
                "max_length": "身体状況は50文字以内で入力してください。",
            },
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["care_level"].choices = [("", "選択しない"), *CareLevel.choices]
        self.fields["care_level"].required = False
        if self.is_bound:
            self.meds = self._meds_from_post()
        elif self.instance.pk:
            self.meds = [{"name": m.name, "timing": m.timing} for m in self.instance.medications.all()]
        else:
            self.meds = []

    def _meds_from_post(self):
        names = self.data.getlist("med_name")
        timings = self.data.getlist("med_timing")
        return [
            {"name": n.strip(), "timing": t if t in Timing.values else Timing.values[0]}
            for n, t in zip(names, timings)
            if n.strip()
        ]

    @property
    def med_rows(self):
        return self.meds or [{"name": "", "timing": DEFAULT_TIMING.value}]

    def clean(self):
        cleaned = super().clean()
        if any(len(m["name"]) > 50 for m in self.meds):
            self.add_error(None, "薬の名前は50文字以内で入力してください。")
        return cleaned

    def error_list(self):
        return [str(e) for errors in self.errors.values() for e in errors]

    @transaction.atomic
    def save(self, commit=True):
        entry = super().save(commit=False)
        if entry.pk is None:
            entry.user = self.user
        entry.save()
        entry.medications.all().delete()
        Medication.objects.bulk_create(
            Medication(pre_registration=entry, name=m["name"], timing=m["timing"]) for m in self.meds
        )
        return entry