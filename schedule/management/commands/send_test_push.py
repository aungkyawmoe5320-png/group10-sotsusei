import json

from django.conf import settings
from django.core.management.base import BaseCommand
from pywebpush import WebPushException, webpush

from schedule.models import PushSubscription


class Command(BaseCommand):
    help = "登録済みの全端末にテスト通知を1件送る"

    def handle(self, *args, **options):
        if not settings.VAPID_PRIVATE_KEY:
            self.stderr.write("VAPID_PRIVATE_KEY が設定されていません。")
            return

        payload = json.dumps({
            "title": "みまもりケアリング",
            "body": "テスト通知です。届いていれば成功!",
            "url": "/schedule/",
        })

        for sub in PushSubscription.objects.all():
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": settings.VAPID_SUBJECT},
                )
                self.stdout.write(f"送信OK: {sub}")
            except WebPushException as e:
                self.stderr.write(f"送信失敗: {sub} / {e}")
                # 404/410 = this device no longer exists, so remove it
                if e.response is not None and e.response.status_code in (404, 410):
                    sub.delete()