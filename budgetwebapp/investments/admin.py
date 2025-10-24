from django.contrib import admin
from django.utils.html import format_html

from .models import Position, CashOperation, Instrument, Dashboard, Widget

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in Position._meta.get_fields()
        if field.name not in ("created_at",)
    ]
    list_filter = ("status", "account_type", "instrument_type", "direction")
    search_fields = ("symbol", "position_id")


@admin.register(CashOperation)
class CashOperationAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in CashOperation._meta.get_fields()
        if field.name not in ("created_at",)
    ]
    list_filter = ("account_type", "type")


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ("symbol", "instrument_type", "logo_tag", "isin")

    def logo_tag(self, obj):
        if obj.logo_url:
            return format_html('<img src="{}" width="40" height="40" />', obj.logo_url)
        return "-"

    logo_tag.short_description = "Logo"


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in Dashboard._meta.get_fields()
        if not (field.many_to_many or field.one_to_many) and field.name != "created_at"
    ]

@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in Widget._meta.get_fields()
        if field.name not in ("created_at",)
    ]

    ordering = ['row', 'column']  # ascending order