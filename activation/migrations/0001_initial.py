import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0003_country_activation_fee_user_is_activated_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentGateway',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method_type', models.CharField(choices=[
                    ('kenya_till_automatic', 'Kenya — M-Pesa Till (Automatic / Daraja)'),
                    ('kenya_till_manual', 'Kenya — M-Pesa Till (Manual)'),
                    ('mtn_manual', 'MTN Mobile Money (Manual, send to Kenya)'),
                    ('airtel_manual', 'Airtel Money (Manual, send to Kenya)'),
                    ('eversend_manual', 'Eversend (Manual)'),
                    ('other_manual', 'Other (Manual)'),
                ], max_length=25)),
                ('display_name', models.CharField(help_text="Shown as the option label on the activation page, e.g. 'Pay via M-Pesa Till (Instant)'.", max_length=100)),
                ('is_automatic', models.BooleanField(default=False, help_text='On = STK push flow (Daraja, Kenya only for now). Off = manual proof-submission flow.')),
                ('till_number', models.CharField(blank=True, max_length=20)),
                ('paybill_number', models.CharField(blank=True, max_length=20)),
                ('account_reference', models.CharField(blank=True, max_length=50)),
                ('recipient_name', models.CharField(blank=True, max_length=100)),
                ('recipient_phone', models.CharField(blank=True, max_length=20)),
                ('instructions', models.TextField(help_text='Step-by-step guide shown to the user exactly as typed here — e.g. numbered steps for an MTN/Airtel send-money-to-Kenya flow. Plain text, one step per line.')),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0, help_text='Lower numbers show first when a country has more than one option.')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_gateways', to='accounts.country')),
            ],
            options={
                'ordering': ['country', 'order'],
            },
        ),
        migrations.CreateModel(
            name='ActivationSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method_type', models.CharField(choices=[
                    ('kenya_till_automatic', 'Kenya — M-Pesa Till (Automatic / Daraja)'),
                    ('kenya_till_manual', 'Kenya — M-Pesa Till (Manual)'),
                    ('mtn_manual', 'MTN Mobile Money (Manual, send to Kenya)'),
                    ('airtel_manual', 'Airtel Money (Manual, send to Kenya)'),
                    ('eversend_manual', 'Eversend (Manual)'),
                    ('other_manual', 'Other (Manual)'),
                ], max_length=25)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency_code', models.CharField(max_length=5)),
                ('reference_code', models.CharField(blank=True, help_text='M-Pesa code / transaction reference the user submitted.', max_length=100)),
                ('proof_message', models.TextField(blank=True)),
                ('daraja_checkout_request_id', models.CharField(blank=True, max_length=100)),
                ('daraja_receipt_number', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('admin_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('gateway', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submissions', to='activation.paymentgateway')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activations_reviewed', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activation_submissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
