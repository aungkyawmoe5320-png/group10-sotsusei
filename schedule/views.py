import json
from .models import AlertSetting, PushLog, PushSubscription, Schedule
from django.http import JsonResponse
from django.conf import settings as django_settings
from .models import PushSubscription
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import user_required

from .forms import AlertSettingForm, ScheduleForm
from .models import AlertSetting, Schedule

MSG_ADDED = "予定を追加しました。"
MSG_UPDATED = "予定を更新しました。"
MSG_DELETED = "予定「{title}」を削除しました。"
MSG_ALERT_SAVED = "アラート設定を保存しました。"


def _own_schedule(request, pk):
    """ログイン中の本人の予定だけを返す。他人のもの・存在しないものは None。"""
    return Schedule.objects.filter(pk=pk, user=request.user).first()


def _form_page(request, form, mode):
    for error in form.error_list():
        messages.error(request, error)
    return render(request, "schedule/form.html", {"form": form, "mode": mode})


@user_required
def schedule_list(request):
    # Opened from a notification (?ack=<id>): mark that alert as acknowledged.
    # Filtering by the user keeps people from touching each other's logs.
    ack = request.GET.get("ack")
    if ack and ack.isdigit():
        PushLog.objects.filter(pk=int(ack), schedule__user=request.user).update(
            acknowledged=True
        )
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


@user_required
def alert_settings(request):
    setting, _ = AlertSetting.objects.get_or_create(user=request.user)
    schedules = list(Schedule.objects.filter(user=request.user))
    if request.method == "POST":
        form = AlertSettingForm(request.POST, instance=setting)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                for s in schedules:
                    s.alert = f"item_{s.pk}" in request.POST
                Schedule.objects.bulk_update(schedules, ["alert"])
            messages.success(request, MSG_ALERT_SAVED)
            return redirect("schedule")
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    else:
        form = AlertSettingForm(instance=setting)
    return render(request, "schedule/alert_settings.html", {
        "form": form,
        "schedules": schedules,
        "vapid_public_key": django_settings.VAPID_PUBLIC_KEY,
    })
@user_required
@require_POST
def push_subscribe(request):
    """ブラウザから届いた通知の送り先を保存する"""
    try:
        data = json.loads(request.body)
        endpoint = data["endpoint"]
        p256dh = data["keys"]["p256dh"]
        auth = data["keys"]["auth"]
    except (ValueError, KeyError, TypeError):
        # Broken or missing data: tell the browser "bad request" (400)
        return JsonResponse({"ok": False}, status=400)

    # If this device is already saved, update it; otherwise create it
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={"user": request.user, "p256dh": p256dh, "auth": auth},
    )
    return JsonResponse({"ok": True})