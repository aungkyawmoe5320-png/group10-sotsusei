from django.conf import settings
from django.db import models


class Schedule(models.Model):
    """ スケジュール(毎日の予定を1件ずつ登録する)。 """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="登録した人",
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    time = models.TimeField("予定時刻")
    title = models.CharField("予定内容", max_length=50)
    alert = models.BooleanField("アラート", default=True)

    class Meta:
        verbose_name = "スケジュール"
        verbose_name_plural = "スケジュール"
        ordering = ["time", "id"]

    def __str__(self):
        return f"{self.time:%H:%M} {self.title}"


class AlertTiming(models.IntegerChoices):
    """いつ知らせるか。左が保存される値（分前）、右が画面に出る名前。"""

    ON_TIME = 0, "予定の時刻ちょうど"
    BEFORE_5 = 5, "5分前"
    BEFORE_10 = 10, "10分前"
    BEFORE_30 = 30, "30分前"


class Renotify(models.IntegerChoices):
    """対応しなかったとき、もう一度知らせるか。"""

    NEVER = 0, "もう一度は知らせない"
    AFTER_5 = 5, "5分後にもう一度知らせる"
    AFTER_10 = 10, "10分後にもう一度知らせる"


class AlertSetting(models.Model):
    """アラート設定（ユーザーごとに1件）。"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="設定した人",
        on_delete=models.CASCADE,
        related_name="alert_setting",
    )
    enabled = models.BooleanField("アラートを使う", default=True)
    timing = models.PositiveSmallIntegerField(
        "いつ知らせるか", choices=AlertTiming.choices, default=AlertTiming.BEFORE_10
    )
    use_sound = models.BooleanField("音", default=True)
    use_vibration = models.BooleanField("バイブレーション", default=False)
    use_screen = models.BooleanField("画面に表示", default=True)
    renotify = models.PositiveSmallIntegerField(
        "対応しなかったとき", choices=Renotify.choices, default=Renotify.AFTER_5
    )

    class Meta:
        verbose_name = "アラート設定"
        verbose_name_plural = "アラート設定"

    def __str__(self):
        return f"{self.user} のアラート設定"


class PushSubscription(models.Model):
    """プッシュ通知の送り先(ユーザーの端末ごとに1件)"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="登録した人",
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.TextField("送信先URL", unique=True)
    p256dh = models.CharField("暗号化用の公開鍵", max_length=255)
    auth = models.CharField("認証キー", max_length=255)
    created_at = models.DateTimeField("登録日時", auto_now_add=True)

    class Meta:
        verbose_name = "プッシュ通知の送り先"
        verbose_name_plural = "プッシュ通知の送り先"

    def __str__(self):
        return f"{self.user} ({self.endpoint[:30]}...)"


class PushLog(models.Model):
    """その日、その予定の通知を送ったか(二重送信を防ぐための記録)"""

    schedule = models.ForeignKey(
        Schedule, on_delete=models.CASCADE, related_name="push_logs"
    )
    date = models.DateField("送った日")
    sent_at = models.DateTimeField("送信日時", auto_now_add=True)

    class Meta:
        constraints = [
            # Same schedule on the same day can only be logged once
            models.UniqueConstraint(
                fields=["schedule", "date"], name="unique_push_per_schedule_day"
            ),
        ]