from django.contrib import admin
from django.utils.html import format_html

from .models import Dashboard, BaseWidget


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in Dashboard._meta.get_fields()
        if not (field.many_to_many or field.one_to_many) and field.name != "created_at"
    ]


@admin.register(BaseWidget)
class BaseWidgetAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in BaseWidget._meta.get_fields()
        if field.name not in ("created_at")
    ]

    # ordering = ['row', 'column']  # ascending order
