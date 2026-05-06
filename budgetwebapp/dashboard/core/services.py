# dashboard/core/services.py

from django.core.cache import cache
from .registry import get_widget_handler, get_widget_metadata
# from budgetwebapp.datahub.filters.filters import Filter
from core.logger import logger


class WidgetService:
    """
    Responsible for:
    - orchestrating widget execution
    - calling DataService
    - returning final widget data

    NO caching here (intentionally)
    """

    def __init__(self, widget):
        self.widget = widget

    def get_data(self, filters=None):
        handler_cls = get_widget_handler(
            self.widget.widget_type,
            self.widget.subtype
        )

        if not handler_cls:
            raise ValueError(
                f"No handler for {self.widget.widget_type}:{self.widget.subtype}"
            )

        handler = handler_cls(self.widget)

        data = handler.run(filters=filters)

        # logger.debug(f"[WidgetService] widget={self.widget.id} data computed")

        return data


def build_filters(widgets):
    filters: list[Filter] = []

    for widget in widgets:
        if widget.widget_type != "filter":
            continue

        handler_cls = get_widget_handler(
            widget.widget_type,
            widget.subtype
        )

        if not handler_cls:
            continue

        handler = handler_cls(widget)

        # validated config (cached, consistent)
        config = handler.get_config()

        # convert via widget logic
        if hasattr(handler, "to_filter"):
            filters.append(handler.to_filter(config))

    return filters


class DashboardService:

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def get_widgets_data(self):
        widgets = list(self.dashboard.widgets.all())

        # build filters once
        filters = build_filters(widgets)

        result = []

        for widget in widgets:
            data = WidgetService(widget).get_data(filters=filters)

            result.append({
                "id": str(widget.id),
                "type": widget.widget_type,
                "subtype": widget.subtype,
                "data": data,
            })

        return result
