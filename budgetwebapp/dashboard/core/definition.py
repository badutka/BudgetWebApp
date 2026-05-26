# dashboard/core/definition.py

from dataclasses import dataclass
from typing import Any, Dict, Optional, Type


@dataclass
class WidgetDefinition:
    config_schema: Type | None = None
    state_schema: Type | None = None
    output_schema: Type | None = None

    ui_schema: dict | None = None
    template: str | None = None

    default_config: dict | None = None
    label: str | None = None

    @classmethod
    def from_executor(cls, executor_cls: Type) -> "WidgetDefinition":
        """
        Build a static widget definition from an executor class.
        This is the ONLY place where reflection happens.
        """

        return cls(
            config_schema=getattr(executor_cls, "CONFIG_SCHEMA", None),
            state_schema=getattr(executor_cls, "STATE_SCHEMA", None),
            output_schema=getattr(executor_cls, "OUTPUT_SCHEMA", None),

            ui_schema=getattr(executor_cls, "UI_SCHEMA", None),
            template=getattr(executor_cls, "TEMPLATE", None),

            default_config=getattr(executor_cls, "DEFAULT_CONFIG", None),

            label=getattr(executor_cls, "LABEL", getattr(executor_cls, "WIDGET_TYPE", executor_cls.__name__)
            ),
        )

    def build_default_config(self) -> dict:
        if self.default_config is not None:
            return self.default_config

        if self.config_schema:
            return self.config_schema().model_dump()

        return {}