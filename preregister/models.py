from django.conf import settings
from django.db import models


class CareLevel(models.TextChoices):
    """要介護度。左が保存される値、右が画面に出る名前。"""

    SUPPORT_1 = "要支援1", "要支援1"
    SUPPORT_2 = "要支援2", "要支援2"
    CARE_1 = "要介護1", "要介護1"
    CARE_2 = "要介護2", "要介護2"
    CARE_3 = "要介護3", "要介護3"
    CARE_4 = "要介護4", "要介護4"
    CARE_5 = "要介護5", "要介護5"


class Timing(models.TextChoices):
    """薬を飲むタイミング。"""

    BEFORE_BREAKFAST = "朝食前", "朝食前"
    AFTER_BREAKFAST = "朝食後", "朝食後"
    BEFORE_LUNCH = "昼食前", "昼食前"
    AFTER_LUNCH = "昼食後", "昼食後"
    BEFORE_DINNER = "夕食前", "夕食前"
    AFTER_DINNER = "夕食後", "夕食後"
    BEFORE_SLEEP = "就寝前", "就寝前"
    AS_NEEDED = "必要なとき", "必要なとき"


class PreRegistration(models.Model):
    """事前登録（身体の状況ごとに1件）。
    必須: 注意事項・身体状況 / 任意: 病名・病院・要介護度・薬
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # このプロジェクトの User（accounts.User）を指す
        verbose_name="登録した人",
        on_delete=models.CASCADE,  # アカウントを消したら、その人の事前登録も消す
        related_name="pre_registrations",
    )
    diagnosis = models.CharField("病名", max_length=50, blank=True)
    hospital = models.CharField("病院", max_length=50, blank=True)
    care_level = models.CharField("要介護度", max_length=10, choices=CareLevel.choices, blank=True)
    notes = models.CharField("注意事項", max_length=500)  # blank=True が無い = 必須
    condition = models.CharField("身体状況", max_length=50)  # 一覧・詳細の見出しになる
    created_at = models.DateTimeField("登録日時", auto_now_add=True)  # 作ったときに1回だけ入る
    updated_at = models.DateTimeField("更新日時", auto_now=True)  # 保存するたびに更新される

    class Meta:
        verbose_name = "事前登録"
        verbose_name_plural = "事前登録"
        ordering = ["id"]  # 登録した順に並べる

    def __str__(self):
        return self.condition


class Medication(models.Model):
    """事前登録に含まれる薬。1件の事前登録に、薬は何件でも付けられる。"""

    pre_registration = models.ForeignKey(
        PreRegistration,
        verbose_name="事前登録",
        on_delete=models.CASCADE,  # 事前登録を消したら、その薬も消す
        related_name="medications",  # entry.medications.all() で薬の一覧を取れる
    )
    name = models.CharField("薬の名前", max_length=50)
    timing = models.CharField("飲むタイミング", max_length=10, choices=Timing.choices, default=Timing.BEFORE_BREAKFAST)

    class Meta:
        verbose_name = "薬"
        verbose_name_plural = "薬"
        ordering = ["id"]  # 入力した順に並べる

    def __str__(self):
        return f"{self.name}（{self.timing}）"