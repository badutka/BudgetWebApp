# Generated by Django 4.2.2 on 2023-06-17 15:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0019_remove_budgetexpenseentry_balance_history_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='balancehistory',
            name='budget_entry',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budget.budgetexpenseentry'),
        ),
    ]
