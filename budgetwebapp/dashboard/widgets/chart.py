# dashboard/widgets/chart.py

from budgetwebapp.dashboard.core.registry import register_widget
from budgetwebapp.dashboard.widgets.schemas import TimeSeriesConfig, TimeSeriesOutput
from budgetwebapp.dashboard.widgets.base import BaseWidgetLogic
from budgetwebapp.datahub.services import data_service
from core.logger import logger


@register_widget("chart", "timeseries2", label="Time Series")
class TimeSeriesChartLogic(BaseWidgetLogic):
    CONFIG_SCHEMA = TimeSeriesConfig
    OUTPUT_SCHEMA = TimeSeriesOutput

    def update_data(self, config, filters=None):
        rows = data_service.get(
            source="timeseries",
            query=config.query,
            filters=filters,
            widget_id=str(self.widget.id),
        )

        return self.to_dataset(rows, config)

    def to_dataset(self, rows, config):
        if not rows:
            return {"columns": {}, "meta": {}}

        # build columnar dataset
        columns = {
            key: [r.get(key) for r in rows]
            for key in rows[0].keys()
        }

        # infer backend meta
        meta = {
            key: self._infer_type(key, values)
            for key, values in columns.items()
        }

        # apply UI overrides
        field_config = getattr(config, "field_config", {}) or {}

        final_meta = {}

        for key in columns.keys():
            final_meta[key] = {
                **meta.get(key, {}),
                **field_config.get(key, {})   # UI overrides backend
            }

        return {
            "columns": columns,
            "meta": final_meta
        }

    def _infer_type(self, key, values):
        """
        Simple heuristic for now (can improve later)
        """

        sample = next((v for v in values if v is not None), None)

        # temporal detection
        if isinstance(sample, str) and "-" in sample:
            return {"type": "temporal"}

        # numeric to metric
        if isinstance(sample, (int, float)):
            return {"type": "metric"}

        # fallback to dimension
        return {"type": "dimension"}