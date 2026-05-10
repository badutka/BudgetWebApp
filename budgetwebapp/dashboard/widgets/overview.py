# dashboard/widgets/overview.py

from budgetwebapp.dashboard.core.registry import register_widget
from budgetwebapp.dashboard.widgets.base import BaseWidgetLogic
from budgetwebapp.dashboard.widgets.schemas import OverviewConfig


@register_widget("overview", label='Overview')
class OverviewWidgetLogic(BaseWidgetLogic):

    CONFIG_SCHEMA = OverviewConfig

    def update_data(self, config, state, filters=None):
        return {
            "metrics": [1, 2, 3],
            "compare": [1, 2, 3]
        }