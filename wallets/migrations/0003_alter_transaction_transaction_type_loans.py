from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wallets", "0002_alter_transaction_transaction_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="transaction_type",
            field=models.CharField(
                choices=[
                    ("deposit_manual", "Manual deposit (admin-approved)"),
                    ("deposit_automatic", "Automatic deposit (Daraja)"),
                    ("withdrawal", "Withdrawal"),
                    ("chat_earning", "Chat earning"),
                    ("survey_earning", "Survey earning"),
                    ("wheel_earning", "Wheel spin earning"),
                    ("app_review_earning", "App review earning"),
                    ("movie_review_earning", "Movie review earning"),
                    ("referral_commission", "Referral commission"),
                    ("plan_purchase", "Plan purchase"),
                    ("loan_plan_purchase", "Loan plan purchase"),
                    ("loan_disbursement", "Loan disbursement"),
                    ("refund", "Refund"),
                    ("admin_adjustment", "Admin adjustment"),
                ],
                max_length=25,
            ),
        ),
    ]