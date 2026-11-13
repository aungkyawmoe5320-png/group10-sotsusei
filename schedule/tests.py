import datetime

from django.test import TestCase
from django.urls import reverse

from accounts.models import CareRecipient, User

from .models import AlertSetting, PushLog, Schedule

PASSWORD = "Mimamori-2026!"


def make_schedule(user, title="朝の薬", at=datetime.time(8, 0), recipient=None, **kwargs):
    recipient = recipient or user.recipients.order_by("id").first()
    return Schedule.objects.create(user=user, care_recipient=recipient, time=at, title=title, **kwargs)


class ScheduleTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.other = User.objects.create_user(email="jiro@example.jp", password=PASSWORD, name="山田 次郎")
        self.hanako = CareRecipient.objects.create(user=self.user, name="山田 花子")
        self.other_recipient = CareRecipient.objects.create(user=self.other, name="佐藤 和子")
        self.client.force_login(self.user)  # 要介護者が1人なら、自動で選ばれる


class AccessTests(ScheduleTestBase):
    URLS = ["schedule", "schedule_new", "alert_settings"]

    def test_anonymous_is_sent_to_top(self):
        self.client.logout()
        for name in self.URLS:
            self.assertRedirects(
                self.client.get(reverse(name)), reverse("index"), msg_prefix=name, fetch_redirect_response=False
            )

class ListTests(ScheduleTestBase):
    def test_only_own_schedules_are_listed(self):
        make_schedule(self.user, title="自分の予定")
        make_schedule(self.other, title="他人の予定")
        res = self.client.get(reverse("schedule"))
        self.assertContains(res, "自分の予定")
        self.assertNotContains(res, "他人の予定")

    def test_ack_marks_own_log_only(self):
        mine = PushLog.objects.create(schedule=make_schedule(self.user), date=datetime.date.today())
        theirs = PushLog.objects.create(schedule=make_schedule(self.other), date=datetime.date.today())
        self.client.get(reverse("schedule") + f"?ack={mine.pk}")
        self.client.get(reverse("schedule") + f"?ack={theirs.pk}")
        mine.refresh_from_db()
        theirs.refresh_from_db()
        self.assertTrue(mine.acknowledged)
        self.assertFalse(theirs.acknowledged)


class CreateTests(ScheduleTestBase):
    def test_create_belongs_to_user_and_selected_recipient(self):
        res = self.client.post(reverse("schedule_new"), {"time": "08:00", "title": "朝の薬", "alert": "on"})
        self.assertRedirects(res, reverse("schedule"))
        s = Schedule.objects.get()
        self.assertEqual((s.user, s.care_recipient, s.title, s.alert), (self.user, self.hanako, "朝の薬", True))
        self.assertEqual(s.time, datetime.time(8, 0))

    def test_alert_off_when_unchecked(self):
        self.client.post(reverse("schedule_new"), {"time": "08:00", "title": "朝の薬"})
        self.assertFalse(Schedule.objects.get().alert)

    def test_required_and_length(self):
        for data, message in [
            ({"time": "", "title": "朝の薬"}, "時刻を入力してください。"),
            ({"time": "08:00", "title": ""}, "予定内容を入力してください。"),
            ({"time": "08:00", "title": "あ" * 51}, "予定内容は50文字以内で入力してください。"),
        ]:
            with self.subTest(data=data):
                res = self.client.post(reverse("schedule_new"), data)
                self.assertContains(res, message)
                self.assertEqual(Schedule.objects.count(), 0)


class UpdateAndDeleteTests(ScheduleTestBase):
    def setUp(self):
        super().setUp()
        self.schedule = make_schedule(self.user, title="朝の薬")

    def test_edit_changes_fields(self):
        res = self.client.post(
            reverse("schedule_edit", args=[self.schedule.pk]), {"time": "09:30", "title": "散歩", "alert": "on"}
        )
        self.assertRedirects(res, reverse("schedule"))
        self.schedule.refresh_from_db()
        self.assertEqual((self.schedule.title, self.schedule.time), ("散歩", datetime.time(9, 30)))

    def test_cannot_edit_or_delete_other_users_schedule(self):
        theirs = make_schedule(self.other, title="他人の予定")
        self.client.post(reverse("schedule_edit", args=[theirs.pk]), {"time": "10:00", "title": "乗っ取り"})
        self.client.post(reverse("schedule_delete", args=[theirs.pk]))
        theirs.refresh_from_db()
        self.assertEqual(theirs.title, "他人の予定")

    def test_delete_removes_schedule(self):
        res = self.client.post(reverse("schedule_delete", args=[self.schedule.pk]), follow=True)
        self.assertRedirects(res, reverse("schedule"))
        self.assertContains(res, "予定「朝の薬」を削除しました。")
        self.assertFalse(Schedule.objects.exists())

    def test_delete_needs_post(self):
        self.assertEqual(self.client.get(reverse("schedule_delete", args=[self.schedule.pk])).status_code, 405)
        self.assertTrue(Schedule.objects.exists())


class RecipientScopeTests(ScheduleTestBase):
    """予定は、選択中の要介護者ごとに分かれる。"""

    def setUp(self):
        super().setUp()
        self.jiro = CareRecipient.objects.create(user=self.user, name="山田 次郎")
        self.select(self.hanako)

    def select(self, recipient):
        self.client.post(reverse("care_recipient_select"), {"recipient_id": recipient.pk})

    def test_list_shows_only_selected_recipients_schedules(self):
        make_schedule(self.user, title="花子の予定", recipient=self.hanako)
        make_schedule(self.user, title="次郎の予定", recipient=self.jiro)
        res = self.client.get(reverse("schedule"))
        self.assertContains(res, "花子の予定")
        self.assertNotContains(res, "次郎の予定")
        self.select(self.jiro)
        res = self.client.get(reverse("schedule"))
        self.assertContains(res, "次郎の予定")
        self.assertNotContains(res, "花子の予定")

    def test_new_schedule_belongs_to_selected_recipient(self):
        self.select(self.jiro)
        self.client.post(reverse("schedule_new"), {"time": "08:00", "title": "朝の薬"})
        s = Schedule.objects.get()
        self.assertEqual((s.user, s.care_recipient), (self.user, self.jiro))

    def test_cannot_touch_schedule_of_another_recipient_in_same_account(self):
        theirs = make_schedule(self.user, title="次郎の予定", recipient=self.jiro)
        res = self.client.get(reverse("schedule_edit", args=[theirs.pk]))
        self.assertRedirects(res, reverse("schedule"))
        self.client.post(reverse("schedule_edit", args=[theirs.pk]), {"time": "10:00", "title": "乗っ取り"})
        self.client.post(reverse("schedule_delete", args=[theirs.pk]))
        theirs.refresh_from_db()
        self.assertEqual(theirs.title, "次郎の予定")

    def test_alert_settings_lists_and_changes_only_selected_recipients_schedules(self):
        mine = make_schedule(self.user, title="花子の予定", recipient=self.hanako)
        theirs = make_schedule(self.user, title="次郎の予定", recipient=self.jiro)
        res = self.client.get(reverse("alert_settings"))
        self.assertContains(res, "花子の予定")
        self.assertNotContains(res, "次郎の予定")
        # 花子の予定のスイッチを切って保存しても、次郎の予定は変わらない
        res = self.client.post(reverse("alert_settings"), {"enabled": "on", "timing": "10", "renotify": "5"})
        self.assertRedirects(res, reverse("schedule"))
        mine.refresh_from_db()
        theirs.refresh_from_db()
        self.assertFalse(mine.alert)
        self.assertTrue(theirs.alert)

    def test_alert_setting_is_per_account(self):
        self.client.post(reverse("alert_settings"), {"timing": "30", "renotify": "0"})
        self.select(self.jiro)
        self.assertEqual(AlertSetting.objects.get(user=self.user).timing, 30)
        self.assertEqual(AlertSetting.objects.filter(user=self.user).count(), 1)

    def test_not_selected_goes_to_select_screen(self):
        self.client.logout()
        self.client.force_login(self.user)  # 新しいログイン = まだ選んでいない
        res = self.client.get(reverse("schedule"))
        self.assertRedirects(res, reverse("care_recipient_select"), fetch_redirect_response=False)

    def test_deleting_a_recipient_removes_their_schedules(self):
        make_schedule(self.user, recipient=self.jiro)
        self.client.post(reverse("care_recipient_delete", args=[self.jiro.pk]))
        self.assertFalse(Schedule.objects.exists())