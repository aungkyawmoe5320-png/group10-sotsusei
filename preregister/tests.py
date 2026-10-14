from django.test import TestCase
from django.urls import reverse

from accounts.models import Facility, User

from .models import Medication, PreRegistration

PASSWORD = "Mimamori-2026!"


def make_entry(user, condition="歩くとふらつく", notes="塩分を控える", meds=(), **kwargs):
    entry = PreRegistration.objects.create(user=user, condition=condition, notes=notes, **kwargs)
    for name, timing in meds:
        Medication.objects.create(pre_registration=entry, name=name, timing=timing)
    return entry


def post_data(**overrides):
    """登録・編集フォームに送る基本データ（薬は med_name / med_timing の並び）。"""
    data = {
        "diagnosis": "高血圧",
        "hospital": "みどり市立病院 内科",
        "care_level": "要介護3",
        "notes": "塩分を控える",
        "condition": "歩くとふらつくことがある",
        "med_name": ["血圧の薬", "胃薬"],
        "med_timing": ["朝食後", "夕食後"],
    }
    data.update(overrides)
    return data


class PreRegisterTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.other = User.objects.create_user(email="jiro@example.jp", password=PASSWORD, name="山田 次郎")
        self.client.force_login(self.user)


class AccessTests(PreRegisterTestBase):
    """ログイン済みの一般ユーザーだけが使える。"""

    URLS = ["preregister", "preregister_new"]

    def test_anonymous_is_sent_to_top(self):
        self.client.logout()
        for name in self.URLS:
            self.assertRedirects(self.client.get(reverse(name)), reverse("index"), msg_prefix=name)

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

    def test_top_page_has_preregister_button(self):
        res = self.client.get(reverse("dashboard"))
        self.assertContains(res, reverse("preregister"))


class ListTests(PreRegisterTestBase):  # 一覧表示
    def test_empty_message_and_register_button(self):
        res = self.client.get(reverse("preregister"))
        self.assertContains(res, "まだ登録がありません。")
        self.assertContains(res, reverse("preregister_new"))

    def test_heading_is_condition_and_shows_meds_count(self):
        make_entry(self.user, condition="階段がつらい", diagnosis="膝の痛み", hospital="",
                   meds=[("湿布", "必要なとき"), ("痛み止め", "朝食後")])
        res = self.client.get(reverse("preregister"))
        self.assertContains(res, "階段がつらい")
        self.assertContains(res, "病名: 膝の痛み")
        self.assertContains(res, "病院: 未登録")
        self.assertContains(res, "薬: 2件")

    def test_only_own_entries_are_listed(self):
        make_entry(self.user, condition="自分の状況")
        make_entry(self.other, condition="他人の状況")
        res = self.client.get(reverse("preregister"))
        self.assertContains(res, "自分の状況")
        self.assertNotContains(res, "他人の状況")

    def test_entries_are_in_registration_order(self):
        make_entry(self.user, condition="一件目")
        make_entry(self.user, condition="二件目")
        content = self.client.get(reverse("preregister")).content.decode()
        self.assertLess(content.index("一件目"), content.index("二件目"))


class DetailTests(PreRegisterTestBase):  # 情報表示
    def test_shows_all_fields(self):
        entry = make_entry(self.user, diagnosis="高血圧", hospital="みどり病院", care_level="要介護3",
                           notes="塩分を控える", meds=[("血圧の薬", "朝食後")])
        res = self.client.get(reverse("preregister_detail", args=[entry.pk]))
        for text in ["歩くとふらつく", "高血圧", "みどり病院", "血圧の薬（朝食後）", "要介護3", "塩分を控える"]:
            self.assertContains(res, text)

    def test_optional_fields_show_unregistered(self):
        entry = make_entry(self.user)
        res = self.client.get(reverse("preregister_detail", args=[entry.pk]))
        self.assertContains(res, "未登録")

    def test_other_users_entry_is_not_shown(self):
        entry = make_entry(self.other, condition="他人の状況")
        res = self.client.get(reverse("preregister_detail", args=[entry.pk]))
        self.assertRedirects(res, reverse("preregister"))

    def test_unknown_id_goes_back_to_list(self):
        self.assertRedirects(self.client.get(reverse("preregister_detail", args=[9999])), reverse("preregister"))


class CreateTests(PreRegisterTestBase):  # 情報登録
    def test_form_is_shown(self):
        res = self.client.get(reverse("preregister_new"))
        self.assertContains(res, "事前登録を追加")
        self.assertContains(res, 'name="med_name"')

    def test_create_with_all_fields_and_meds(self):
        res = self.client.post(reverse("preregister_new"), post_data(), follow=True)
        self.assertRedirects(res, reverse("preregister"))
        self.assertContains(res, "事前登録を追加しました。")
        entry = PreRegistration.objects.get()
        self.assertEqual(entry.user, self.user)  # 登録した本人のものになる
        self.assertEqual(entry.care_level, "要介護3")
        self.assertEqual([(m.name, m.timing) for m in entry.medications.all()],
                         [("血圧の薬", "朝食後"), ("胃薬", "夕食後")])

    def test_only_required_fields_is_enough(self):
        data = {"notes": "転倒に注意", "condition": "階段がつらい", "care_level": "", "med_name": [""], "med_timing": ["朝食後"]}
        self.client.post(reverse("preregister_new"), data)
        entry = PreRegistration.objects.get()
        self.assertEqual((entry.diagnosis, entry.hospital, entry.care_level), ("", "", ""))
        self.assertEqual(entry.medications.count(), 0)

    def test_blank_med_rows_are_ignored(self):
        data = post_data(med_name=["血圧の薬", "  ", ""], med_timing=["朝食後", "昼食後", "夕食後"])
        self.client.post(reverse("preregister_new"), data)
        self.assertEqual(Medication.objects.count(), 1)

    def test_unknown_timing_falls_back_to_first_choice(self):
        self.client.post(reverse("preregister_new"), post_data(med_name=["胃薬"], med_timing=["でたらめ"]))
        self.assertEqual(Medication.objects.get().timing, "朝食前")

    def test_notes_required(self):
        res = self.client.post(reverse("preregister_new"), post_data(notes="   "))
        self.assertContains(res, "注意事項を入力してください。")
        self.assertEqual(PreRegistration.objects.count(), 0)

    def test_condition_required(self):
        res = self.client.post(reverse("preregister_new"), post_data(condition=""))
        self.assertContains(res, "身体状況を入力してください。")
        self.assertEqual(PreRegistration.objects.count(), 0)

    def test_length_limits(self):
        res = self.client.post(reverse("preregister_new"), post_data(
            diagnosis="あ" * 51, hospital="い" * 51, condition="う" * 51, notes="え" * 501,
            med_name=["お" * 51], med_timing=["朝食後"],
        ))
        for text in ["病名は50文字以内", "病院は50文字以内", "身体状況は50文字以内", "注意事項は500文字以内", "薬の名前は50文字以内"]:
            self.assertContains(res, text)
        self.assertEqual(PreRegistration.objects.count(), 0)

    def test_invalid_care_level_is_rejected(self):
        res = self.client.post(reverse("preregister_new"), post_data(care_level="要介護9"))
        self.assertContains(res, "要介護度を正しく選んでください。")
        self.assertEqual(PreRegistration.objects.count(), 0)

    def test_input_is_kept_when_there_is_an_error(self):
        res = self.client.post(reverse("preregister_new"), post_data(condition=""))
        self.assertContains(res, "血圧の薬")
        self.assertContains(res, "みどり市立病院 内科")

    def test_script_in_input_is_escaped(self):
        entry = make_entry(self.user, condition="<script>alert(1)</script>")
        for name, args in [("preregister", []), ("preregister_detail", [entry.pk])]:
            res = self.client.get(reverse(name, args=args))
            self.assertNotContains(res, "<script>alert(1)</script>")


class UpdateTests(PreRegisterTestBase):  # 情報変更
    def setUp(self):
        super().setUp()
        self.entry = make_entry(self.user, diagnosis="高血圧", care_level="要介護3",
                                meds=[("血圧の薬", "朝食後"), ("胃薬", "夕食後")])

    def test_form_is_filled_with_current_values(self):
        res = self.client.get(reverse("preregister_edit", args=[self.entry.pk]))
        self.assertContains(res, "事前登録を編集")
        self.assertContains(res, "高血圧")
        self.assertContains(res, "血圧の薬")
        self.assertContains(res, "胃薬")

    def test_update_changes_fields_and_replaces_meds(self):
        data = post_data(condition="夜に歩き回る", med_name=["新しい薬"], med_timing=["就寝前"], care_level="")
        res = self.client.post(reverse("preregister_edit", args=[self.entry.pk]), data, follow=True)
        self.assertRedirects(res, reverse("preregister_detail", args=[self.entry.pk]))
        self.assertContains(res, "事前登録を更新しました。")
        self.entry.refresh_from_db()
        self.assertEqual((self.entry.condition, self.entry.care_level), ("夜に歩き回る", ""))
        self.assertEqual([(m.name, m.timing) for m in self.entry.medications.all()], [("新しい薬", "就寝前")])
        self.assertEqual(PreRegistration.objects.count(), 1)

    def test_validation_error_keeps_old_data(self):
        self.client.post(reverse("preregister_edit", args=[self.entry.pk]), post_data(notes=""))
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.notes, "塩分を控える")
        self.assertEqual(self.entry.medications.count(), 2)

    def test_cannot_edit_other_users_entry(self):
        theirs = make_entry(self.other, condition="他人の状況")
        res = self.client.post(reverse("preregister_edit", args=[theirs.pk]), post_data(condition="乗っ取り"))
        self.assertRedirects(res, reverse("preregister"))
        theirs.refresh_from_db()
        self.assertEqual(theirs.condition, "他人の状況")
        self.assertEqual(theirs.user, self.other)


class DeleteTests(PreRegisterTestBase):  # 情報削除
    def test_detail_has_delete_form_with_confirm_text(self):
        entry = make_entry(self.user, condition="階段がつらい")
        res = self.client.get(reverse("preregister_detail", args=[entry.pk]))
        self.assertContains(res, 'data-confirm="この事前登録（階段がつらい）を削除しますか？"')

    def test_delete_removes_entry_and_its_meds(self):
        entry = make_entry(self.user, meds=[("胃薬", "夕食後")])
        res = self.client.post(reverse("preregister_delete", args=[entry.pk]), follow=True)
        self.assertRedirects(res, reverse("preregister"))
        self.assertContains(res, "事前登録を削除しました。")
        self.assertFalse(PreRegistration.objects.exists())
        self.assertFalse(Medication.objects.exists())

    def test_get_is_not_allowed(self):
        entry = make_entry(self.user)
        self.assertEqual(self.client.get(reverse("preregister_delete", args=[entry.pk])).status_code, 405)
        self.assertTrue(PreRegistration.objects.exists())

    def test_cannot_delete_other_users_entry(self):
        theirs = make_entry(self.other)
        self.client.post(reverse("preregister_delete", args=[theirs.pk]))
        self.assertTrue(PreRegistration.objects.filter(pk=theirs.pk).exists())

    def test_deleting_account_removes_entries(self):
        make_entry(self.user, meds=[("胃薬", "夕食後")])
        self.client.post(reverse("account_delete"))
        self.assertFalse(PreRegistration.objects.exists())
        self.assertFalse(Medication.objects.exists())


class CsrfTests(PreRegisterTestBase):
    def test_post_without_csrf_token_is_rejected(self):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        res = strict.post(reverse("preregister_new"), post_data())
        self.assertEqual(res.status_code, 403)
        self.assertEqual(PreRegistration.objects.count(), 0)
