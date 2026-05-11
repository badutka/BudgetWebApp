from django.core.cache import cache
from abc import ABC, abstractmethod

from core.logger import logger


class BaseWidgetLogic(ABC):
    """
    Core widget execution layer:
    - config/state validation
    - caching
    - runtime execution
    - UI schema + runtime hooks (optional overrides)
    """

    CONFIG_SCHEMA = None
    STATE_SCHEMA = None
    OUTPUT_SCHEMA = None
    TEMPLATE_MAP = {
        # (context, widget_type, subtype)
        ("dashboard", "overview", None): "dashboard/widgets/widget_overview_partial.html",
        ("dashboard", "table", None): "dashboard/widgets/widget_table_partial.html",
        ("dashboard", "chart", None): "dashboard/widgets/widget_generic_chart_partial.html",

        ("dashboard", "filter", "select"): "dashboard/widgets/select_filter_widget.html",
        ("dashboard", "filter", "date"): "dashboard/widgets/select_filter_widget.html",
        # ("dashboard", "filter", None): "dashboard/widgets/filter_base.html",
    }
    DEFAULT_TEMPLATE = "dashboard/widgets/widget_generic_chart_partial.html"

    def __init__(self, widget):
        self.widget = widget

        self._validated_config = None
        self._validated_config_at = None

        self._validated_state = None
        self._validated_state_at = None


    def get_config(self):
        current_version = self.widget.updated_at

        if (
            self._validated_config is not None
            and self._validated_config_at == current_version
        ):
            return self._validated_config

        if not self.CONFIG_SCHEMA:
            return self.widget.config or {}

        cache_key = f"widget_config:{self.widget.id}:{current_version.timestamp()}"
        cached = cache.get(cache_key)

        if cached is not None:
            self._validated_config = cached
            self._validated_config_at = current_version
            return cached

        validated = self.CONFIG_SCHEMA(**(self.widget.config or {}))

        self._validated_config = validated
        self._validated_config_at = current_version

        cache.set(cache_key, validated, timeout=None)

        return validated


    def get_state(self):
        current_version = self.widget.updated_at

        if (
            self._validated_state is not None
            and self._validated_state_at == current_version
        ):
            return self._validated_state

        if not self.STATE_SCHEMA:
            return self.widget.state or {}

        validated = self.STATE_SCHEMA(**(self.widget.state or {}))

        self._validated_state = validated
        self._validated_state_at = current_version

        return validated


    def validate_output(self, data):
        if not self.OUTPUT_SCHEMA:
            return data

        return self.OUTPUT_SCHEMA(**data).model_dump()

    def run(self, filters=None):
        config = self.get_config()
        state = self.get_state()

        data = self.update_data(
            config=config,
            state=state,
            filters=filters,
        )

        return self.validate_output(data)


    def get_ui_schema(self):
        """
        Sidebar/editor schema.
        Override in widgets that need UI controls.
        """
        return {
            "controls": {},
            "meta": {
                "type": self.widget.widget_type,
                "subtype": self.widget.subtype,
            },
        }

    def get_template(self, context="dashboard"):
        """
        Resolve template based on:
        - widget type
        - subtype
        - rendering context (dashboard/sidebar/export/etc.)
        """

        widget_type = self.widget.widget_type
        subtype = self.widget.subtype

        # context-aware key builder
        key = (context, widget_type, subtype)
        if key in self.TEMPLATE_MAP:
            return self.TEMPLATE_MAP[key]

        key = (context, widget_type, None)
        if key in self.TEMPLATE_MAP:
            return self.TEMPLATE_MAP[key]

        key = (None, widget_type, subtype)
        if key in self.TEMPLATE_MAP:
            return self.TEMPLATE_MAP[key]

        key = (None, widget_type, None)
        if key in self.TEMPLATE_MAP:
            return self.TEMPLATE_MAP[key]

        return self.DEFAULT_TEMPLATE

    def get_runtime_options(self, filters=None):
        """
        Dynamic dropdown/filter options.
        Override in filter widgets.
        """
        return None

    @abstractmethod
    def update_data(self, config, state, filters=None):
        pass