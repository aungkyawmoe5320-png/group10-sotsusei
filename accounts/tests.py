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


    def test_signup_creates_first_care_recipient(self):
        self.post_signup()
        user = User.objects.get(email="taro@example.jp")
        self.assertEqual([r.name for r in user.recipients.all()], ["山田 花子"])

    def test_recipient_name_is_required(self):
        res = self.post_signup(recipient_name="")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(email="taro@example.jp").exists())
        
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
        self.assertRedirects(res, reverse("dashboard"))
        self.assertContains(self.client.get(reverse("dashboard")), "今日のようす")

    def test_wrong_password_fails(self):
        res = self.client.post(reverse("login"), {"email": "taro@example.jp", "password": "wrong"})
        self.assertContains(res, "正しくありません")

    def test_dashboard_requires_login(self):
        res = self.client.get(reverse("dashboard"))
        self.assertRedirects(res, reverse("index") + "?next=" + reverse("dashboard"), fetch_redirect_response=False)

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

    def test_edit_updates_name(self):
        res = self.client.post(reverse("account_edit"), {"name": "山田 次郎", "email": "taro@example.jp"})
        self.assertRedirects(res, reverse("account_detail"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "山田 次郎")

    def test_delete_removes_account(self):
        res = self.client.post(reverse("account_delete"))
        self.assertRedirects(res, reverse("login"))
        self.assertFalse(User.objects.filter(email="taro@example.jp").exists())