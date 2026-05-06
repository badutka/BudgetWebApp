# dashboard/widgets/filter.py
from budgetwebapp.dashboard.core.registry import register_widget
from budgetwebapp.dashboard.widgets.base import BaseWidgetLogic
from budgetwebapp.datahub.filters.domain import Filter
from budgetwebapp.dashboard.widgets.schemas import SelectFilterConfig, RangeFilterConfig


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
        return Filter(
            field=config.field,
            operator=config.operator,
            value=config.value,
            targets=config.targets,
        )


@register_widget("filter", "range", label="Range Filter")
class RangeFilterLogic(BaseWidgetLogic):
    CONFIG_SCHEMA = RangeFilterConfig

    def to_filter(self, config: RangeFilterConfig) -> Filter:
        return Filter(
            field=config.field,
            operator=config.operator,
            value=config.value,
            min_value=config.min_value,
            max_value=config.max_value,
            targets=config.targets,
        )