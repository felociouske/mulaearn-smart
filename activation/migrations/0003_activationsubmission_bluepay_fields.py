from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activation", "0002_remove_paymentgateway_recipient_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="activationsubmission",
            name="bluepay_checkout_request_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="activationsubmission",
            name="bluepay_stk_request_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="activationsubmission",
            name="bluepay_receipt_number",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]