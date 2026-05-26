# dashboard/core/registry.py

from typing import Dict, Type

from .definition import WidgetDefinition

_WIDGET_REGISTRY: Dict[str, Dict[str, dict]] = {}


from typing import Dict
from .definition import WidgetDefinition

_WIDGET_REGISTRY: Dict[str, Dict[str, dict]] = {}


def register_widget(widget_type: str, subtype: str = None, label: str = None):
    def wrapper(cls):
        cls.WIDGET_TYPE = widget_type
        cls.SUBTYPE = subtype
        cls.LABEL = label or subtype or widget_type

        definition = WidgetDefinition.from_executor(cls)

        _WIDGET_REGISTRY.setdefault(widget_type, {})[subtype] = {
            "definition": definition,
            "executor": cls,
        }

        return cls
    return wrapper


def get_entry(widget_type: str, subtype: str = None):
    entry = _WIDGET_REGISTRY.get(widget_type, {}).get(subtype)
    if not entry:
        raise ValueError(f"No widget for {widget_type}:{subtype}")
    return entry


def get_widget_definition(widget_type: str, subtype: str = None):
    return get_entry(widget_type, subtype)["definition"]


def get_widget_executor(widget_type: str, subtype: str = None):
    return get_entry(widget_type, subtype)["executor"]