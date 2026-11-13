from django.test import TestCase
from django.urls import reverse

from .models import CareRecipient, User

PASSWORD = "Mimamori-2026-Care!"


class BackButtonTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="taro@example.jp", password=PASSWORD, name="山田 太郎")
        self.recipient = CareRecipient.objects.create(user=self.user, name="山田 花子")
        self.client.force_login(self.user)

    def back(self, url_name):
        return f'href="{reverse(url_name)}"><i class="bi bi-arrow-left"></i> 戻る'

    def test_account_screen_goes_back_to_home(self):
        res = self.client.get(reverse("account_detail"))
        self.assertContains(res, self.back("dashboard"))

    def test_add_recipient_goes_back_to_account(self):
        res = self.client.get(reverse("care_recipient_new"))
        self.assertContains(res, self.back("account_detail"))

    def test_edit_recipient_goes_back_to_account(self):
        res = self.client.get(reverse("care_recipient_edit", args=[self.recipient.pk]))
        self.assertContains(res, self.back("account_detail"))