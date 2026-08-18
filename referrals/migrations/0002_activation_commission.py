import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activation', '0002_remove_paymentgateway_recipient_name_and_more'),
        ('referrals', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='referralcommission',
            name='source',
            field=models.CharField(
                choices=[('plan_purchase', 'Plan purchase'), ('activation', 'Account activation')],
                default='plan_purchase',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='referralcommission',
            name='plan_purchase',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='referral_commission',
                to='plans.planpurchase',
            ),
        ),
        migrations.AddField(
            model_name='referralcommission',
            name='activation_submission',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='referral_commission',
                to='activation.activationsubmission',
            ),
        ),
    ]