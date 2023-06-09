# Generated by Django 4.2.2 on 2023-06-08 09:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0002_rename_budgetentry_budgetexpenseentry'),
    ]

    operations = [
        migrations.CreateModel(
            name='MoneyAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('balance', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='budgetexpenseentry',
            name='destination',
            field=models.CharField(choices=[('ING', 'ING'), ('PKO', 'PKO'), ('CASH', 'CASH'), ('OUT', 'OUT')], max_length=255),
        ),
        migrations.AlterField(
            model_name='budgetexpenseentry',
            name='origin',
            field=models.CharField(choices=[('ING', 'ING'), ('PKO', 'PKO'), ('CASH', 'CASH'), ('OUT', 'OUT')], max_length=255),
        ),
    ]
