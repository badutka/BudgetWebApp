# dashboard/widgets/chart.py

from budgetwebapp.dashboard.core.registry import register_widget
from budgetwebapp.dashboard.widgets.schemas import TimeSeriesConfig, TimeSeriesOutput
from budgetwebapp.dashboard.widgets.base import BaseWidgetLogic


@register_widget("chart", "timeseries", label='Time Series')
class TimeSeriesChartLogic(BaseWidgetLogic):
    CONFIG_SCHEMA = TimeSeriesConfig
    OUTPUT_SCHEMA = TimeSeriesOutput

    def update_data(self, config):
        mock_data = {
            "date": [
                "2026-01-01",
                "2026-02-01",
                "2026-03-01",
                "2026-04-01",
                "2026-05-01",
            ],
            "series": {
                "invested_value": [1000, 1200, 1400, 1600, 1800],
                "portfolio_value": [1100, 1250, 1500, 1700, 2000],
                "net_gain": [100, 50, 100, 100, 200],
                "portfolio_value_2": [330, 375, 450, 510, 600],
                "portfolio_value_3": [550, 625, 750, 850, 1000],
            },
            "series_meta": {
                "invested_value": {"name": "Invested Value"},
                "portfolio_value": {"name": "Total Value"},
                "portfolio_value_2": {"name": "Invested Value 2"},
                "portfolio_value_3": {"name": "Invested Value 3"},
                "net_gain": {"name": "Net Gain"},
            }
        }

        return mock_data
