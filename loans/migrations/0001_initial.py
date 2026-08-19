import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LoanPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("min_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("max_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("order", models.PositiveIntegerField()),
                ("repayment_period_days", models.PositiveIntegerField(default=30)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="LoanPlanPurchase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price_paid", models.DecimalField(decimal_places=2, max_digits=10)),
                ("purchased_at", models.DateTimeField(auto_now_add=True)),
                ("loan_plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchases", to="loans.loanplan")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="loan_plan_purchases", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-purchased_at"]},
        ),
        migrations.CreateModel(
            name="LoanApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("phone_number", models.CharField(max_length=20)),
                ("country_name", models.CharField(max_length=50)),
                ("full_name", models.CharField(max_length=150)),
                ("age", models.PositiveIntegerField()),
                ("source_of_income", models.CharField(max_length=200)),
                ("repayment_method", models.CharField(max_length=200)),
                ("security", models.CharField(blank=True, max_length=200)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("amount_owed", models.DecimalField(decimal_places=2, max_digits=12)),
                ("due_date", models.DateField()),
                (
                    "repayment_status",
                    models.CharField(
                        choices=[("owing", "Owing"), ("paid", "Paid"), ("written_off", "Written off")],
                        default="owing",
                        max_length=15,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("loan_plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="applications", to="loans.loanplan")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="loan_applications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]