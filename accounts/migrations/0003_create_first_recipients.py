from django.db import migrations


def create_first_recipients(apps, schema_editor):
    """要介護者が1人もいない一般ユーザーに、「要介護者」を1人つくる（あとで設定画面で名前を変えられる）。"""
    User = apps.get_model("accounts", "User")
    CareRecipient = apps.get_model("accounts", "CareRecipient")
    for user in User.objects.filter(role="user", recipients__isnull=True):
        CareRecipient.objects.create(user=user, name="要介護者")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_carerecipient"),
    ]

    operations = [
        migrations.RunPython(create_first_recipients, migrations.RunPython.noop),
    ]