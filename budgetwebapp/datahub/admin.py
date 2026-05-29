from django.contrib import admin
from budgetwebapp.datahub.models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in Dataset._meta.get_fields()
    ]
