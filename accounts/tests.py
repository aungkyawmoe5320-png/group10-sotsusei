from django.test import TestCase
from django.urls import reverse

from .models import CareRecipient, User

PASSWORD = "Mimamori-2026-Care!"  # 16文字以上・英字・数字・記号


class SignUpTests(TestCase):
    def post_signup(self, **overrides):
        data = {
            "name": "山田 太郎",
            "recipient_name": "山田 花子",
            "email": "Taro@Example.jp",
            "password": PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse("account_new"), data)

    def test_signup_creates_account_and_logs_in(self):
        res = self.post_signup()
        self.assertRedirects(res, reverse("dashboard"))
        user = User.objects.get(email="taro@example.jp")  # メールは小文字で保存
        self.assertEqual(user.role, "user")
        self.assertNotEqual(user.password, PASSWORD)  # 平文で保存されていない
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)  # そのままログイン

    def test_signup_shows_message(self):
        res = self.post_signup()
        res = self.client.get(res.url)
        self.assertContains(res, "アカウントを登録しました。")

    def test_signup_creates_first_care_recipient(self):
        self.post_signup()
        user = User.objects.get(email="taro@example.jp")
        self.assertEqual([r.name for r in user.recipients.all()], ["山田 花子"])

    def test_recipient_name_is_required(self):
        res = self.post_signup(recipient_name="")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(email="taro@example.jp").exists())

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="既存")
        res = self.post_signup()
        self.assertContains(res, "既に登録されています")

    def test_password_rule_is_enforced(self):
        weak = [
            "Short-1!",                 # 短い
            "abcdefghijklmnopqrst",     # 英字だけ
            "12345678901234567890",     # 数字だけ
            "abcdefgh12345678",         # 記号なし
            "abcdefgh-ijklmnop",        # 数字なし
            "12345678-90123456",        # 英字なし
        ]
        for password in weak:
            with self.subTest(password=password):
                res = self.post_signup(password=password)
                self.assertContains(res, "16文字以上の英字、数字、記号")
                self.assertFalse(User.objects.filter(email="taro@example.jp").exists())


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")

    def test_user_login_success(self):
        res = self.client.post(reverse("login"), {"email": "taro@example.jp", "password": PASSWORD})
        self.assertRedirects(res, reverse("care_recipient_select"), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("dashboard")), "今日のようす")

    def test_wrong_password_fails(self):
        res = self.client.post(reverse("login"), {"email": "taro@example.jp", "password": "wrong"})
        self.assertContains(res, "正しくありません")

    def test_dashboard_requires_login(self):
        res = self.client.get(reverse("dashboard"))
        self.assertRedirects(res, reverse("login") + "?next=" + reverse("dashboard"), fetch_redirect_response=False)

    def test_index_redirects_to_login(self):
        res = self.client.get(reverse("index"))
        self.assertRedirects(res, reverse("login"))

    def test_logout(self):
        self.client.force_login(self.user)
        res = self.client.post(reverse("logout"))
        self.assertRedirects(res, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class AccountCrudTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.client.force_login(self.user)

    def test_detail_shows_own_info(self):
        res = self.client.get(reverse("account_detail"))
        self.assertContains(res, "山田 太郎")
        self.assertContains(res, "taro@example.jp")

    def test_detail_lists_care_recipients(self):
        CareRecipient.objects.create(user=self.user, name="山田 花子", relation="母", age=80)
        res = self.client.get(reverse("account_detail"))
        self.assertContains(res, "山田 花子")
        self.assertContains(res, "母")
        self.assertContains(res, "80歳")

    def test_edit_updates_name(self):
        res = self.client.post(reverse("account_edit"), {"name": "山田 次郎", "email": "taro@example.jp"})
        self.assertRedirects(res, reverse("account_detail"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "山田 次郎")

    def post_edit(self, **overrides):
        data = {"name": "山田 太郎", "email": "taro@example.jp", "phone": ""}
        data.update(overrides)
        return self.client.post(reverse("account_edit"), data)

    def test_phone_is_saved_and_shown(self):
        res = self.post_edit(phone="090-1234-5678")
        self.assertRedirects(res, reverse("account_detail"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "090-1234-5678")
        self.assertContains(self.client.get(reverse("account_detail")), "090-1234-5678")

    def test_phone_unregistered_is_shown_when_empty(self):
        self.post_edit(phone="")
        self.assertContains(self.client.get(reverse("account_detail")), "未登録")

    def test_full_width_phone_is_converted(self):
        self.post_edit(phone="０９０－１２３４－５６７８")
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "090-1234-5678")

    def test_invalid_phone_is_rejected(self):
        for phone in ["12345789", "abc", "090-1234-567", "090--1234-5678", "+81-90-1234-5678"]:
            with self.subTest(phone=phone):
                res = self.post_edit(phone=phone)
                self.assertContains(res, "電話番号は、数字とハイフンで入力してください（例: 090-1234-5678）。")
                self.user.refresh_from_db()
                self.assertEqual(self.user.phone, "")

    def test_japanese_email_is_rejected(self):
        res = self.post_edit(email="山田@example.jp")
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "taro@example.jp")

    def test_signup_screen_has_no_phone_field(self):
        res = self.client.get(reverse("account_new"))
        self.assertNotContains(res, 'name="phone"')


    def test_delete_removes_account(self):
        res = self.client.post(reverse("account_delete"))
        self.assertRedirects(res, reverse("login"))
        self.assertFalse(User.objects.filter(email="taro@example.jp").exists())


class CareRecipientAddTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.client.force_login(self.user)

    def post_new(self, **overrides):
        data = {"name": "山田 次郎", "age": "", "birthday": "", "relation": ""}
        data.update(overrides)
        return self.client.post(reverse("care_recipient_new"), data)

    def test_add_with_name_only(self):
        res = self.post_new()
        self.assertRedirects(res, reverse("account_detail"))
        recipient = self.user.recipients.get()
        self.assertEqual(
            (recipient.name, recipient.age, recipient.birthday, recipient.relation),
            ("山田 次郎", None, None, ""),
        )

    def test_add_with_age_and_relation(self):
        self.post_new(age="80", relation="母")
        recipient = self.user.recipients.get()
        self.assertEqual((recipient.age, recipient.relation), (80, "母"))

    def test_birthday_replaces_typed_age(self):
        self.post_new(age="50", birthday="1946-03-15")
        recipient = self.user.recipients.get()
        self.assertIsNone(recipient.age)
        self.assertGreaterEqual(recipient.display_age, 79)

    def test_duplicate_name_is_rejected(self):
        CareRecipient.objects.create(user=self.user, name="山田 次郎")
        res = self.post_new()
        self.assertContains(res, "同じ氏名の要介護者がすでに登録されています。")
        self.assertEqual(self.user.recipients.count(), 1)

    def test_same_name_is_ok_for_another_account(self):
        other = User.objects.create_user(email="other@example.jp", password=PASSWORD, name="他の人")
        CareRecipient.objects.create(user=other, name="山田 次郎")
        self.post_new()
        self.assertEqual(self.user.recipients.count(), 1)

    def test_invalid_values_are_rejected(self):
        for overrides, message in [
            ({"name": ""}, "このフィールドは必須です"),
            ({"age": "131"}, "年齢は0〜130の数字で入力してください。"),
            ({"age": "-1"}, "年齢は0〜130の数字で入力してください。"),
            ({"birthday": "2999-01-01"}, "誕生日を正しく入力してください。"),
            ({"birthday": "1800-01-01"}, "誕生日を正しく入力してください。"),
            ({"birthday": "abc"}, "誕生日を正しく入力してください。"),
            ({"relation": "ともだち"}, "は候補にありません"),
        ]:
            with self.subTest(overrides=overrides):
                res = self.post_new(**overrides)
                self.assertEqual(res.status_code, 200)
                self.assertContains(res, message)
                self.assertEqual(self.user.recipients.count(), 0)

    def test_add_screen_requires_login(self):
        self.client.logout()
        res = self.client.get(reverse("care_recipient_new"))
        self.assertEqual(res.status_code, 302)


class CareRecipientEditDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.client.force_login(self.user)
        self.hanako = CareRecipient.objects.create(user=self.user, name="山田 花子", relation="母", age=80)

    def edit_url(self, recipient):
        return reverse("care_recipient_edit", args=[recipient.pk])

    def delete_url(self, recipient):
        return reverse("care_recipient_delete", args=[recipient.pk])

    def test_edit_screen_shows_saved_values(self):
        res = self.client.get(self.edit_url(self.hanako))
        self.assertContains(res, "山田 花子")
        self.assertContains(res, 'value="80"')

    def test_edit_updates_values(self):
        res = self.client.post(self.edit_url(self.hanako), {
            "name": "山田 花子", "age": "", "birthday": "1946-03-15", "relation": "祖母",
        })
        self.assertRedirects(res, reverse("account_detail"))
        self.hanako.refresh_from_db()
        self.assertEqual(self.hanako.relation, "祖母")
        self.assertIsNone(self.hanako.age)
        self.assertGreaterEqual(self.hanako.display_age, 79)

    def test_edit_can_keep_same_name(self):
        res = self.client.post(self.edit_url(self.hanako), {
            "name": "山田 花子", "age": "81", "birthday": "", "relation": "母",
        })
        self.assertRedirects(res, reverse("account_detail"))
        self.hanako.refresh_from_db()
        self.assertEqual(self.hanako.age, 81)

    def test_edit_rejects_name_of_another_recipient(self):
        CareRecipient.objects.create(user=self.user, name="山田 次郎")
        res = self.client.post(self.edit_url(self.hanako), {
            "name": "山田 次郎", "age": "", "birthday": "", "relation": "",
        })
        self.assertContains(res, "同じ氏名の要介護者がすでに登録されています。")

    def test_cannot_touch_other_accounts_recipient(self):
        other = User.objects.create_user(email="other@example.jp", password=PASSWORD, name="他の人")
        theirs = CareRecipient.objects.create(user=other, name="佐藤 和子")
        self.assertEqual(self.client.get(self.edit_url(theirs)).status_code, 404)
        self.assertEqual(self.client.post(self.delete_url(theirs)).status_code, 404)
        self.assertTrue(CareRecipient.objects.filter(pk=theirs.pk).exists())

    def test_delete_removes_recipient_when_two_or_more(self):
        jiro = CareRecipient.objects.create(user=self.user, name="山田 次郎")
        res = self.client.post(self.delete_url(jiro))
        self.assertRedirects(res, reverse("account_detail"))
        self.assertFalse(CareRecipient.objects.filter(pk=jiro.pk).exists())

    def test_cannot_delete_the_only_recipient(self):
        res = self.client.post(self.delete_url(self.hanako))
        self.assertRedirects(res, self.edit_url(self.hanako))
        self.assertTrue(CareRecipient.objects.filter(pk=self.hanako.pk).exists())

    def test_delete_needs_post(self):
        CareRecipient.objects.create(user=self.user, name="山田 次郎")
        self.assertEqual(self.client.get(self.delete_url(self.hanako)).status_code, 405)

    def test_delete_card_depends_on_number_of_recipients(self):
        self.assertContains(self.client.get(self.edit_url(self.hanako)), "1人だけのときは、削除できません")
        CareRecipient.objects.create(user=self.user, name="山田 次郎")
        res = self.client.get(self.edit_url(self.hanako))
        self.assertContains(res, "削除する")
        self.assertContains(res, "元に戻せません。よろしいですか？")

class CareRecipientSelectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.client.force_login(self.user)
        self.hanako = CareRecipient.objects.create(user=self.user, name="山田 花子")

    def add_jiro(self):
        return CareRecipient.objects.create(user=self.user, name="山田 次郎")

    def test_one_recipient_is_selected_automatically(self):
        res = self.client.get(reverse("care_recipient_select"))
        self.assertRedirects(res, reverse("dashboard"))
        self.assertEqual(self.client.session["care_recipient_id"], self.hanako.pk)

    def test_screen_lists_all_when_two_or_more(self):
        self.add_jiro()
        res = self.client.get(reverse("care_recipient_select"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "山田 花子")
        self.assertContains(res, "山田 次郎")

    def test_choosing_stores_selection(self):
        jiro = self.add_jiro()
        res = self.client.post(reverse("care_recipient_select"), {"recipient_id": jiro.pk})
        self.assertRedirects(res, reverse("dashboard"))
        self.assertEqual(self.client.session["care_recipient_id"], jiro.pk)

    def test_cannot_choose_other_accounts_recipient(self):
        self.add_jiro()
        other = User.objects.create_user(email="other@example.jp", password=PASSWORD, name="他の人")
        theirs = CareRecipient.objects.create(user=other, name="佐藤 和子")
        res = self.client.post(reverse("care_recipient_select"), {"recipient_id": theirs.pk})
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("care_recipient_id", self.client.session)

    def test_account_screen_shows_badge_and_switch_button(self):
        jiro = self.add_jiro()
        self.client.post(reverse("care_recipient_select"), {"recipient_id": jiro.pk})
        html = self.client.get(reverse("account_detail")).content.decode()
        self.assertEqual(html.count("選択中"), 1)
        self.assertEqual(html.count(">切り替える</button>"), 1)

    def test_no_switch_button_with_one_recipient(self):
        html = self.client.get(reverse("account_detail")).content.decode()
        self.assertEqual(html.count("選択中"), 1)
        self.assertEqual(html.count(">切り替える</button>"), 0)

    def test_deleting_selected_recipient_clears_selection(self):
        jiro = self.add_jiro()
        self.client.post(reverse("care_recipient_select"), {"recipient_id": jiro.pk})
        self.client.post(reverse("care_recipient_delete", args=[jiro.pk]))
        res = self.client.get(reverse("account_detail"))
        self.assertContains(res, "山田 花子")
        self.assertEqual(self.client.session["care_recipient_id"], self.hanako.pk)  # 1人だけ残ったので自動で選ばれる

    def test_select_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("care_recipient_select")).status_code, 302)