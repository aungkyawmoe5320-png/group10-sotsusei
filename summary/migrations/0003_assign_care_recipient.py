from django.db import migrations


def assign_first_recipient(apps, schema_editor):
    """今あるまとめPDFを、持ち主の最初の要介護者のものにする。"""
    User = apps.get_model("accounts", "User")
    SummaryPdf = apps.get_model("summary", "SummaryPdf")
    for user in User.objects.filter(recipients__isnull=False).distinct():
        first = user.recipients.order_by("id").first()
        SummaryPdf.objects.filter(user=user, care_recipient__isnull=True).update(care_recipient=first)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_create_first_recipients"),
        ("summary", "0002_summarypdf_care_recipient"),
    ]

    operations = [
        migrations.RunPython(assign_first_recipient, migrations.RunPython.noop),
    ]