# dashboard/widgets/filter.py
from datetime import datetime, timedelta

from budgetwebapp.dashboard.core.registry import register_widget
from budgetwebapp.dashboard.widgets.base import BaseWidgetLogic
from budgetwebapp.datahub.filters.domain import Filter
from budgetwebapp.dashboard.widgets.schemas import SelectFilterConfig, RangeFilterConfig, DateFilterConfig


@register_widget("filter", "select", label="Select Filter")
class SelectFilterLogic(BaseWidgetLogic):
    CONFIG_SCHEMA = SelectFilterConfig

    def update_data(self, config, filters=None):
        return {
            "field": config.field,
            "operator": config.operator,
            "value": config.value,
            "options": config.options,
            "targets": config.targets,
        }

    def to_filter(self, config: SelectFilterConfig) -> Filter:
        # if not config.field or not config.value:
        #     return None
    
        return Filter(
            field=config.field,
            operator=config.operator,
            value=config.value,
            targets=config.targets,
        )


@register_widget("filter", "range", label="Range Filter")
class RangeFilterLogic(BaseWidgetLogic):
    CONFIG_SCHEMA = RangeFilterConfig

    def update_data(self, config, filters=None):
        return {
            "field": config.field,
            "operator": config.operator,
            "value": config.value,
            "min_value": config.min_value,
            "max_value": config.max_value,
            "targets": config.targets,
        }

    def to_filter(self, config: RangeFilterConfig) -> Filter:
        return Filter(
            field=config.field,
            operator=config.operator,
            value=config.value,
            min_value=config.min_value,
            max_value=config.max_value,
            targets=config.targets,
        )
    

@register_widget("filter", "date", label="Date Filter")
class DateFilterLogic(BaseWidgetLogic):
    CONFIG_SCHEMA = DateFilterConfig

    def update_data(self, config, filters=None):
        return {
            "field": config.field,
            "mode": config.mode,
            "operator": "between",
            "targets": config.targets,
            "start_date": getattr(config, "start_date", None),
            "end_date": getattr(config, "end_date", None),
            "unit": getattr(config, "unit", None),
            "last_n": getattr(config, "last_n", None),
        }

    def to_filter(self, config: DateFilterConfig) -> Filter:

        if config.mode == "absolute":
            return Filter(
                field=config.field,
                operator="between",
                min_value=config.start_date,
                max_value=config.end_date,
                targets=config.targets,
            )

        if config.mode == "relative":
            now = datetime.utcnow()

            if config.unit == "day":
                delta = timedelta(days=config.last_n)
            elif config.unit == "week":
                delta = timedelta(weeks=config.last_n)
            elif config.unit == "month":
                delta = timedelta(days=30 * config.last_n)
            elif config.unit == "year":
                delta = timedelta(days=365 * config.last_n)
            else:
                raise ValueError("Invalid unit")

            start = now - delta

            return Filter(
                field=config.field,
                operator="between",
                min_value=start.isoformat(),
                max_value=now.isoformat(),
                targets=config.targets,
            )

        raise ValueError(f"Unsupported mode: {config.mode}")