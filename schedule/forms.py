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