from django.contrib import admin
from django.utils.html import format_html

from .models import Position, CashOperation, Instrument


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    # Automatically include all model fields in list_display
    list_display = [
        field.name for field in Position._meta.get_fields()
        if field.name not in ("created_at",)
    ]
    list_filter = ("status", "account_type", "instrument_type", "direction")
    search_fields = ("symbol", "position_id")


@admin.register(CashOperation)
class PositionAdmin(admin.ModelAdmin):
    # Automatically include all model fields in list_display
    list_display = [
        field.name for field in CashOperation._meta.get_fields()
        if field.name not in ("created_at",)
    ]


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ("symbol", "instrument_type", "logo_tag", "isin")

    def logo_tag(self, obj):
        if obj.logo_url:
            return format_html('<img src="{}" width="40" height="40" />', obj.logo_url)
        return "-"

    logo_tag.short_description = "Logo"
