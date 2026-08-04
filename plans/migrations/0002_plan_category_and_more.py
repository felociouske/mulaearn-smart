import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='category',
            # Default 'chat' only applies to rows that already exist from the old
            # single-category Plan model — go recategorize any pre-existing plans
            # in admin after this migration runs, this default is just to satisfy
            # the NOT NULL constraint on existing rows.
            field=models.CharField(
                choices=[
                    ('app_review', 'App Reviews'),
                    ('movie_review', 'Movie Reviews'),
                    ('chat', 'Chat with Foreigners'),
                ],
                default='chat',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='plan',
            name='cashback_percentage',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=5, null=True,
                help_text="Optional headline cashback %, e.g. 5.00 for '5% cashback'. Leave blank if none.",
            ),
        ),
        migrations.RenameField(
            model_name='plan',
            old_name='unlocked_profile_count',
            new_name='unlocked_item_count',
        ),
        migrations.RemoveField(model_name='plan', name='unlocks_surveys'),
        migrations.RemoveField(model_name='plan', name='unlocks_videos'),
        migrations.RemoveField(model_name='plan', name='unlocks_reviews'),
        migrations.RemoveField(model_name='plan', name='unlocks_ebooks'),
        migrations.RemoveField(model_name='plan', name='unlocks_ads'),
        migrations.AlterField(
            model_name='plan',
            name='tier_order',
            # No longer globally unique — uniqueness is now per-category, see
            # AlterUniqueTogether below (App-review tier 1 and Chat tier 1 can coexist).
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterModelOptions(
            name='plan',
            options={'ordering': ['category', 'tier_order']},
        ),
        migrations.AlterUniqueTogether(
            name='plan',
            unique_together={('category', 'tier_order')},
        ),
        migrations.CreateModel(
            name='PlanFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=200)),
                ('order', models.PositiveIntegerField(default=0)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='features', to='plans.plan')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]