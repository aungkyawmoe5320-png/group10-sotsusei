from django.test import TestCase
from django.urls import reverse

from .models import Facility, User

PASSWORD = "Mimamori-2026!"


class SignUpTests(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(facility_code="F-0012", name="テスト施設")

    def test_user_signup_creates_account(self):
        res = self.client.post(reverse("account_new"), {
            "role": "user", "name": "山田 太郎", "email": "Taro@Example.jp", "password": PASSWORD,
        })
        self.assertRedirects(res, reverse("login", args=["user"]))
        user = User.objects.get(email="taro@example.jp")  # メールは小文字で保存
        self.assertEqual(user.role, "user")
        self.assertIsNone(user.facility)
        self.assertNotEqual(user.password, PASSWORD)  # 平文で保存されていない

    def test_caregiver_signup_requires_valid_facility(self):
        res = self.client.post(reverse("account_new"), {
            "role": "caregiver", "name": "介護 花子", "email": "hanako@example.jp",
            "password": PASSWORD, "facility_code": "F-9999",
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "この施設IDは登録されていません。")
        self.assertFalse(User.objects.filter(email="hanako@example.jp").exists())

    def test_caregiver_signup_with_facility(self):
        self.client.post(reverse("account_new"), {
            "role": "caregiver", "name": "介護 花子", "email": "hanako@example.jp",
            "password": PASSWORD, "facility_code": "F-0012",
        })
        self.assertEqual(User.objects.get(email="hanako@example.jp").facility, self.facility)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="既存")
        res = self.client.post(reverse("account_new"), {
            "role": "user", "name": "山田 太郎", "email": "taro@example.jp", "password": PASSWORD,
        })
        self.assertContains(res, "既に登録されています")

    def test_weak_password_is_rejected(self):
        res = self.client.post(reverse("account_new"), {
            "role": "user", "name": "山田 太郎", "email": "taro@example.jp", "password": "12345678",
        })
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(email="taro@example.jp").exists())


class LoginTests(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(facility_code="F-0012", name="テスト施設")
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.caregiver = User.objects.create_user(
            email="hanako@example.jp", password=PASSWORD, name="介護 花子",
            role=User.Role.CAREGIVER, facility=self.facility,
        )

    def test_user_login_success(self):
        res = self.client.post(reverse("login", args=["user"]), {"email": "taro@example.jp", "password": PASSWORD})
        self.assertRedirects(res, reverse("dashboard"))
        self.assertContains(self.client.get(reverse("dashboard")), "今日のようす")

    def test_wrong_password_fails(self):
        res = self.client.post(reverse("login", args=["user"]), {"email": "taro@example.jp", "password": "wrong"})
        self.assertContains(res, "正しくありません")

    def test_user_cannot_login_on_caregiver_page(self):
        res = self.client.post(reverse("login", args=["caregiver"]), {
            "email": "taro@example.jp", "password": PASSWORD, "facility_code": "F-0012",
        })
        self.assertContains(res, "正しくありません")

    def test_caregiver_login_needs_matching_facility(self):
        res = self.client.post(reverse("login", args=["caregiver"]), {
            "email": "hanako@example.jp", "password": PASSWORD, "facility_code": "F-0020",
        })
        self.assertContains(res, "正しくありません")
        res = self.client.post(reverse("login", args=["caregiver"]), {
            "email": "hanako@example.jp", "password": PASSWORD, "facility_code": "F-0012",
        })
        self.assertRedirects(res, reverse("dashboard"))
        self.assertContains(self.client.get(reverse("dashboard")), "入所者一覧")

    def test_dashboard_requires_login(self):
        res = self.client.get(reverse("dashboard"))
        self.assertRedirects(res, reverse("index") + "?next=" + reverse("dashboard"), fetch_redirect_response=False)

    def test_logout(self):
        self.client.force_login(self.user)
        res = self.client.post(reverse("logout"))
        self.assertRedirects(res, reverse("index"))
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
        self.assertRedirects(res, reverse("index"))
        self.assertFalse(User.objects.filter(email="taro@example.jp").exists())
