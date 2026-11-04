from .models import AlertSetting, Schedule

from django import forms

from .models import Schedule


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ["time", "title", "alert"]
        error_messages = {
            "time": {
                "required": "時刻を入力してください。",
                "invalid": "時刻を正しく入力してください。",
            },
            "title": {
                "required": "予定内容を入力してください。",
                "max_length": "予定内容は50文字以内で入力してください。",
            },
        }
        widgets = {
            "time": forms.TimeInput(
                format="%H:%M",
                attrs={"type": "time", "class": "form-control form-control-lg", "required": True},
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def error_list(self):
        return [str(e) for errors in self.errors.values() for e in errors]

    def save(self, commit=True):
        schedule = super().save(commit=False)
        if schedule.pk is None:
            schedule.user = self.user
        if commit:
            schedule.save()
        return schedule

class AlertSettingForm(forms.ModelForm):
    class Meta:
        model = AlertSetting
        fields = ["enabled", "timing", "use_sound", "use_vibration", "use_screen", "renotify"]
        widgets = {
            "enabled": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
            "timing": forms.Select(attrs={"class": "form-select form-select-lg"}),
            "use_sound": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "use_vibration": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "use_screen": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "renotify": forms.Select(attrs={"class": "form-select form-select-lg"}),
        }