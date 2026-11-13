import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import CareRecipient, Facility, User
from preregister.models import PreRegistration
from schedule.models import Schedule

from .models import SummaryPdf

PASSWORD = "Mimamori-2026!"


def make_prereg(user, recipient, condition="歩くとふらつく"):
    return PreRegistration.objects.create(user=user, care_recipient=recipient, condition=condition, notes="塩分を控える")


def make_pdf(user, recipient, items=None, survey=None):
    items = items or {"basic": True, "prereg": [], "schedule": False}
    return SummaryPdf.objects.create(user=user, care_recipient=recipient, items=items, survey=survey or {})


class SummaryTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.other = User.objects.create_user(email="jiro@example.jp", password=PASSWORD, name="山田 次郎")
        self.hanako = CareRecipient.objects.create(user=self.user, name="山田 花子", relation="母", age=80)
        self.other_recipient = CareRecipient.objects.create(user=self.other, name="佐藤 和子")
        self.client.force_login(self.user)  # 要介護者が1人なら、自動で選ばれる

    def select(self, recipient):
        self.client.post(reverse("care_recipient_select"), {"recipient_id": recipient.pk})

    def submit_survey(self):
        """項目を選び、アンケートに答えて、PDFを作成・更新する。
        アンケートの中身の検証は、survey_def 側の仕事なので、ここでは差し替えて、PDFの保存先だけを確かめる。"""
        self.client.post(reverse("summary_save"), {"basic": "on", "schedule": "on"})
        with patch("summary.views.read_survey", return_value={"signature": "山田 太郎"}), \
                patch("summary.views.survey_errors", return_value=[]):
            return self.client.post(reverse("summary_survey"), {})


class AccessTests(SummaryTestBase):
    URLS = ["summary", "summary_survey", "summary_detail", "summary_download"]

    def test_anonymous_is_sent_to_top(self):
        self.client.logout()
        for name in self.URLS:
            self.assertRedirects(
                self.client.get(reverse(name)), reverse("index"), msg_prefix=name, fetch_redirect_response=False
            )

    def test_caregiver_is_sent_to_dashboard(self):
        facility = Facility.objects.create(facility_code="F-0012", name="テスト施設")
        caregiver = User.objects.create_user(
            email="hanako@example.jp", password=PASSWORD, name="介護 花子",
            role=User.Role.CAREGIVER, facility=facility,
        )
        self.client.force_login(caregiver)
        for name in self.URLS:
            self.assertRedirects(
                self.client.get(reverse(name)), reverse("dashboard"), fetch_redirect_response=False, msg_prefix=name
            )


class SelectPageTests(SummaryTestBase):
    def test_lists_only_selected_recipients_entries(self):
        mine = make_prereg(self.user, self.hanako)
        jiro = CareRecipient.objects.create(user=self.user, name="山田 次郎")
        theirs = make_prereg(self.user, jiro)
        self.select(self.hanako)
        res = self.client.get(reverse("summary"))
        self.assertEqual([e.pk for e in res.context["prereg"]], [mine.pk])
        self.select(jiro)
        res = self.client.get(reverse("summary"))
        self.assertEqual([e.pk for e in res.context["prereg"]], [theirs.pk])

    def test_first_time_everything_is_selected(self):
        entry = make_prereg(self.user, self.hanako)
        res = self.client.get(reverse("summary"))
        self.assertEqual(res.context["form"], {"basic": True, "prereg": [entry.pk], "schedule": True})

    def test_save_keeps_only_selected_recipients_entries(self):
        mine = make_prereg(self.user, self.hanako)
        jiro = CareRecipient.objects.create(user=self.user, name="山田 次郎")
        theirs = make_prereg(self.user, jiro)
        stranger = make_prereg(self.other, self.other_recipient)
        self.select(self.hanako)
        res = self.client.post(reverse("summary_save"), {"basic": "on", "prereg": [mine.pk, theirs.pk, stranger.pk]})
        self.assertRedirects(res, reverse("summary_survey"), fetch_redirect_response=False)
        pending = self.client.session["summary_pending"]
        self.assertEqual(pending["recipient"], self.hanako.pk)
        self.assertEqual(pending["items"], {"basic": True, "prereg": [mine.pk], "schedule": False})

    def test_nothing_chosen_is_rejected(self):
        res = self.client.post(reverse("summary_save"), {})
        self.assertContains(res, "まとめる項目を1つ以上選んでください。")
        self.assertNotIn("summary_pending", self.client.session)


class SurveyFlowTests(SummaryTestBase):
    def setUp(self):
        super().setUp()
        self.jiro = CareRecipient.objects.create(user=self.user, name="山田 次郎")
        self.select(self.hanako)

    def test_survey_without_choosing_items_goes_back(self):
        res = self.client.get(reverse("summary_survey"))
        self.assertRedirects(res, reverse("summary"))

    def test_chosen_items_do_not_follow_to_another_recipient(self):
        self.client.post(reverse("summary_save"), {"basic": "on"})
        self.select(self.jiro)
        res = self.client.get(reverse("summary_survey"))
        self.assertRedirects(res, reverse("summary"))

    def test_creates_pdf_for_selected_recipient(self):
        res = self.submit_survey()
        self.assertRedirects(res, reverse("summary_detail"), fetch_redirect_response=False)
        pdf = SummaryPdf.objects.get()
        self.assertEqual((pdf.user, pdf.care_recipient), (self.user, self.hanako))
        self.assertEqual(pdf.items, {"basic": True, "prereg": [], "schedule": True})
        self.assertEqual(pdf.survey, {"signature": "山田 太郎"})

    def test_second_time_updates_the_same_pdf(self):
        self.submit_survey()
        self.submit_survey()
        self.assertEqual(SummaryPdf.objects.count(), 1)

    def test_each_recipient_has_their_own_pdf(self):
        self.submit_survey()
        self.select(self.jiro)
        self.submit_survey()
        self.assertEqual(SummaryPdf.objects.count(), 2)
        self.assertEqual(self.user.summary_pdfs.count(), 2)
        self.assertEqual(
            sorted(SummaryPdf.objects.values_list("care_recipient__name", flat=True)), ["山田 次郎", "山田 花子"]
        )


class DetailDeleteDownloadTests(SummaryTestBase):
    def setUp(self):
        super().setUp()
        self.jiro = CareRecipient.objects.create(user=self.user, name="山田 次郎")
        self.select(self.hanako)
        self.pdf = make_pdf(self.user, self.hanako)

    def test_str_uses_recipient_name(self):
        self.assertEqual(str(self.pdf), "山田 花子さんの情報まとめ")

    def test_detail_shows_selected_recipients_basic_info(self):
        res = self.client.get(reverse("summary_detail"))
        for text in ["山田 花子", "80歳", "母"]:
            self.assertContains(res, text)
        self.assertNotContains(res, "taro@example.jp")

    def test_detail_without_pdf_goes_to_select(self):
        self.select(self.jiro)
        self.assertRedirects(self.client.get(reverse("summary_detail")), reverse("summary"))

    def test_detail_and_schedule_and_prereg_belong_to_the_selected_recipient(self):
        entry = make_prereg(self.user, self.hanako, condition="花子の状況")
        make_prereg(self.user, self.jiro, condition="次郎の状況")
        Schedule.objects.create(user=self.user, care_recipient=self.hanako, time=datetime.time(8, 0), title="花子の予定")
        Schedule.objects.create(user=self.user, care_recipient=self.jiro, time=datetime.time(9, 0), title="次郎の予定")
        self.pdf.items = {"basic": True, "prereg": [entry.pk], "schedule": True}
        self.pdf.save()
        res = self.client.get(reverse("summary_detail"))
        self.assertContains(res, "花子の状況")
        self.assertContains(res, "花子の予定")
        self.assertNotContains(res, "次郎の状況")
        self.assertNotContains(res, "次郎の予定")

    def test_delete_removes_only_selected_recipients_pdf(self):
        jiros = make_pdf(self.user, self.jiro)
        res = self.client.post(reverse("summary_delete"))
        self.assertRedirects(res, reverse("summary"))
        self.assertFalse(SummaryPdf.objects.filter(pk=self.pdf.pk).exists())
        self.assertTrue(SummaryPdf.objects.filter(pk=jiros.pk).exists())

    def test_delete_needs_post(self):
        self.assertEqual(self.client.get(reverse("summary_delete")).status_code, 405)
        self.assertTrue(SummaryPdf.objects.exists())

    def test_download_returns_a_pdf_file(self):
        res = self.client.get(reverse("summary_download"))
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertIn("attachment", res["Content-Disposition"])
        self.assertTrue(b"".join(res.streaming_content).startswith(b"%PDF"))

    def test_download_without_pdf_goes_to_select(self):
        self.select(self.jiro)
        self.assertRedirects(self.client.get(reverse("summary_download")), reverse("summary"))

    def test_deleting_a_recipient_removes_their_pdf(self):
        jiros = make_pdf(self.user, self.jiro)
        self.client.post(reverse("care_recipient_delete", args=[self.jiro.pk]))
        self.assertFalse(SummaryPdf.objects.filter(pk=jiros.pk).exists())
        self.assertTrue(SummaryPdf.objects.filter(pk=self.pdf.pk).exists())

    def test_not_selected_goes_to_select_screen(self):
        self.client.logout()
        self.client.force_login(self.user)  # 新しいログイン = まだ選んでいない
        res = self.client.get(reverse("summary"))
        self.assertRedirects(res, reverse("care_recipient_select"), fetch_redirect_response=False)