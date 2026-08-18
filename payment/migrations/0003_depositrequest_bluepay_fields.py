from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0002_depositrequest_gateway_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="depositrequest",
            name="method",
            field=models.CharField(
                choices=[
                    ("manual", "Manual (proof submitted, admin-approved)"),
                    ("automatic_daraja", "Automatic — Safaricom Daraja"),
                    ("automatic_bluepay", "Automatic — BluePay (M-Pesa)"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="depositrequest",
            name="bluepay_checkout_request_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="depositrequest",
            name="bluepay_stk_request_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="depositrequest",
            name="bluepay_receipt_number",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]