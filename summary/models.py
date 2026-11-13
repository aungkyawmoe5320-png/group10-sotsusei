from django.conf import settings
from django.db import models


class SummaryPdf(models.Model):
    """まとめPDF（要介護者1人につき1つ。作成後は同じPDFを更新する）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="作成した人",
        on_delete=models.CASCADE,  # アカウントを消したら、PDFも消す
        related_name="summary_pdfs",
    )
    care_recipient = models.OneToOneField(
        "accounts.CareRecipient",
        verbose_name="要介護者",
        on_delete=models.CASCADE,  # 要介護者を削除したら、その人のPDFも消す
        related_name="summary_pdf",
    )
    # まとめる項目 例: {"basic": true, "prereg": [1, 3], "schedule": false}
    items = models.JSONField("まとめる項目", default=dict)
    # アンケートの答え。PDFを削除すると、一緒に消える
    survey = models.JSONField("アンケートの答え", default=dict)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("最終更新日時", auto_now=True)

    class Meta:
        verbose_name = "まとめPDF"
        verbose_name_plural = "まとめPDF"

    def __str__(self):
        owner = self.care_recipient or self.user
        return f"{owner.name}さんの情報まとめ"