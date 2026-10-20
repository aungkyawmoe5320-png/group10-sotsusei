from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import user_required

from .forms import ScheduleForm
from .models import AlertSetting, Schedule

MSG_ADDED = "予定を追加しました。"
MSG_UPDATED = "予定を更新しました。"
MSG_DELETED = "予定「{title}」を削除しました。"


def _own_schedule(request, pk):
    """ログイン中の本人の予定だけを返す。他人のもの・存在しないものは None。"""
    return Schedule.objects.filter(pk=pk, user=request.user).first()


def _form_page(request, form, mode):
    for error in form.error_list():
        messages.error(request, error)
    return render(request, "schedule/form.html", {"form": form, "mode": mode})


@user_required
def schedule_list(request):
    schedules = Schedule.objects.filter(user=request.user)
    alert_setting, _ = AlertSetting.objects.get_or_create(user=request.user)
    return render(request, "schedule/list.html", {
        "schedules": schedules,
        "alert_on": alert_setting.enabled,
    })


@user_required
def schedule_new(request):
    if request.method == "POST":
        form = ScheduleForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, MSG_ADDED)
            return redirect("schedule")
    else:
        form = ScheduleForm(user=request.user)
    return _form_page(request, form, "new")


@user_required
def schedule_edit(request, pk):
    schedule = _own_schedule(request, pk)
    if schedule is None:
        return redirect("schedule")
    if request.method == "POST":
        form = ScheduleForm(request.POST, instance=schedule, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, MSG_UPDATED)
            return redirect("schedule")
    else:
        form = ScheduleForm(instance=schedule, user=request.user)
    return _form_page(request, form, "edit")


@user_required
@require_POST
def schedule_delete(request, pk):
    schedule = _own_schedule(request, pk)
    if schedule is not None:
        title = schedule.title
        schedule.delete()
        messages.info(request, MSG_DELETED.format(title=title))
    return redirect("schedule")