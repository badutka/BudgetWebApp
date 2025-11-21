from django.contrib import admin
from django.utils.html import format_html

from .models import (Position, CashOperation, Instrument, Dashboard, OverviewWidget, ChartWidget,
                     DashboardWidget, Account)


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


@admin.register(OverviewWidget)
class OverviewWidgetAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in OverviewWidget._meta.get_fields()
        if field.name not in ("created_at", "dashboardwidget")
    ]

    # ordering = ['row', 'column']  # ascending order


@admin.register(ChartWidget)
class ChartWidgetAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in ChartWidget._meta.get_fields()
        if field.name not in ("created_at", 'dashboardwidget', 'data')
    ]

    # ordering = ['row', 'column']  # ascending order


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in DashboardWidget._meta.get_fields()
        if field.name not in ("created_at",)
    ]

    ordering = ['dashboard', 'row', 'column']  # ascending order

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Account._meta.get_fields()]
