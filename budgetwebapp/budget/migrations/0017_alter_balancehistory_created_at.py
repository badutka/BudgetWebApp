# Generated by Django 4.2.2 on 2023-06-17 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0016_balancehistory_budget_entry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='balancehistory',
            name='created_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
