from django.test import TestCase
from django.urls import reverse

from .models import CareRecipient, User

PASSWORD = "Mimamori-2026-Care!"


class HeaderTests(TestCase):
    """ヘッダーに、選択中の要介護者の名前を出す。"""

    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.hanako = CareRecipient.objects.create(user=self.user, name="山田 花子")

    def tag(self, name):
        return f'<small class="text-white fw-semibold">{name}</small>'

    def test_shows_name_when_one_recipient(self):
        self.client.force_login(self.user)  # 1人なら、自動で選ばれる
        res = self.client.get(reverse("dashboard"))
        self.assertContains(res, self.tag("山田 花子"))

    def test_no_name_when_two_recipients_and_none_selected(self):
        CareRecipient.objects.create(user=self.user, name="山田 次郎")
        self.client.force_login(self.user)
        res = self.client.get(reverse("dashboard"))
        self.assertNotContains(res, "text-white fw-semibold")

    def test_name_follows_the_selected_recipient(self):
        jiro = CareRecipient.objects.create(user=self.user, name="山田 次郎")
        self.client.force_login(self.user)
        self.client.post(reverse("care_recipient_select"), {"recipient_id": jiro.pk})
        res = self.client.get(reverse("dashboard"))
        self.assertContains(res, self.tag("山田 次郎"))
        self.assertNotContains(res, self.tag("山田 花子"))

    def test_no_name_on_login_screen(self):
        res = self.client.get(reverse("login"))
        self.assertNotContains(res, "text-white fw-semibold")