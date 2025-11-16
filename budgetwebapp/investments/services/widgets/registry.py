from typing import Dict, Type

_WIDGET_REGISTRY = {}


def register_widget(widget_type: str, subtype: str = None):
    """Decorator to register a widget logic class."""

    def wrapper(cls):
        _WIDGET_REGISTRY.setdefault(widget_type, {})[subtype] = cls
        return cls

    return wrapper


def get_widget_logic(widget_type: str, subtype: str = None):
    """Retrieve the logic class for a given widget type and optional subtype."""
    widget_group = _WIDGET_REGISTRY.get(widget_type, {})
    return widget_group.get(subtype) or widget_group.get(None)
