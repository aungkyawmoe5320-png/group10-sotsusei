import json
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from pywebpush import WebPushException, webpush

from schedule.models import AlertTiming, PushLog, Renotify, Schedule

from django.db.models import F
class Command(BaseCommand):
    help = "今送るべきアラートをプッシュ通知で送る(毎分実行する)"

    # If the timer was late, still send within 3 minutes. Older than that = skip.
    WINDOW = timedelta(minutes=3)

    def handle(self, *args, **options):
        if not settings.VAPID_PRIVATE_KEY:
            self.stderr.write("VAPID_PRIVATE_KEY が設定されていません。")
            return

        now = timezone.localtime()
        today = now.date()
        self.send_first(now, today)
        self.send_again(now, today)

    # ---------- 1st notification ----------
    def send_first(self, now, today):
        schedules = (
            Schedule.objects.filter(
                alert=True, user__push_subscriptions__isnull=False
            )
            .select_related("user")
            .distinct()
        )
        for s in schedules:
            # Users who never opened the settings page have no row: use defaults
            setting = getattr(s.user, "alert_setting", None)
            enabled = setting.enabled if setting else True
            timing = setting.timing if setting else AlertTiming.BEFORE_10
            if not enabled:
                continue

            fire_at = timezone.make_aware(
                datetime.combine(today, s.time)
            ) - timedelta(minutes=timing)
            if not (fire_at <= now < fire_at + self.WINDOW):
                continue

            # Claim "sent today": the unique constraint makes this safe
            log, created = PushLog.objects.get_or_create(schedule=s, date=today, time=s.time)
            if not created:
                continue

            if timing == 0:
                body = f"{s.time:%H:%M} {s.title} の時間です"
            else:
                body = f"{timing}分後({s.time:%H:%M}) {s.title}"
            self.send_to_user(s, setting, body, log)

    # ---------- reminder if not acknowledged ----------
    def send_again(self, now, today):
        logs = (
            PushLog.objects.filter(
                date=today,
                acknowledged=False,
                renotified=False,
                schedule__alert=True,
                schedule__user__push_subscriptions__isnull=False,
                time=F("schedule__time"),
            )
            .select_related("schedule__user")
            .distinct()
        )
        for log in logs:
            s = log.schedule
            setting = getattr(s.user, "alert_setting", None)
            enabled = setting.enabled if setting else True
            again = setting.renotify if setting else Renotify.AFTER_5
            if not enabled or again == Renotify.NEVER:
                continue

            due = log.sent_at + timedelta(minutes=again)
            if not (due <= now < due + self.WINDOW):
                continue

            # Claim the reminder (only one run can win this update)
            claimed = PushLog.objects.filter(pk=log.pk, renotified=False).update(
                renotified=True
            )
            if not claimed:
                continue

            body = f"もう一度お知らせ: {s.time:%H:%M} {s.title}"
            self.send_to_user(s, setting, body, log)

    # ---------- helpers ----------
    def send_to_user(self, s, setting, body, log):
        use_vibration = setting.use_vibration if setting else False
        use_sound = setting.use_sound if setting else True
        payload = json.dumps({
            "title": "予定のお知らせ",
            "body": body,
            "tag": f"schedule-{s.pk}",
            # Tapping the notification opens this URL, which marks the log acknowledged
            "url": f"/schedule/?ack={log.pk}",
            "vibrate": [300, 150, 300] if use_vibration else None,
            "silent": not use_sound and not use_vibration,
        })
        for sub in s.user.push_subscriptions.all():
            self.send_one(sub, payload)

    def send_one(self, sub, payload):
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
            self.stdout.write(f"送信OK: {sub}")
        except WebPushException as e:
            self.stderr.write(f"送信失敗: {sub} / {e}")
            if e.response is not None and e.response.status_code in (404, 410):
                sub.delete()