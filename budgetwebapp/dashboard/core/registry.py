# dashboard/core/registry.py

from typing import Dict, Type

_WIDGET_REGISTRY: Dict[str, Dict[str, Type["BaseWidgetLogic"]]] = {}


# def register_widget(widget_type: str, subtype: str = None):
#     def wrapper(cls):
#         _WIDGET_REGISTRY.setdefault(widget_type, {})[subtype] = cls
#         return cls
#
#     return wrapper

def register_widget(widget_type: str, subtype: str = None, label: str = None):
    def wrapper(cls):
        cls.WIDGET_TYPE = widget_type
        cls.SUBTYPE = subtype
        cls.LABEL = label or subtype or widget_type

        _WIDGET_REGISTRY.setdefault(widget_type, {})[subtype] = cls
        return cls

    return wrapper


def get_widget_handler(widget_type: str, subtype: str = None):
    group = _WIDGET_REGISTRY.get(widget_type)

    if not group:
        return None

    if subtype in group:
        return group[subtype]

    # explicit fallback ONLY if subtype is None
    if subtype is None:
        return group.get(None)

    raise ValueError(f"No handler for {widget_type}:{subtype}")


def get_subtypes(widget_type: str):
    group = _WIDGET_REGISTRY.get(widget_type, {})
    return [k for k in group.keys() if k is not None]


def get_widget_types():
    return list(_WIDGET_REGISTRY.keys())


def get_widget_metadata():
    result = {}

    for widget_type, subtypes in _WIDGET_REGISTRY.items():
        result[widget_type] = []

        for subtype, cls in subtypes.items():
            result[widget_type].append({
                "subtype": subtype,
                "label": cls.LABEL,
                "config_schema": (
                    cls.CONFIG_SCHEMA.model_json_schema()
                    if cls.CONFIG_SCHEMA else None
                ),
                "output_schema": (
                    cls.OUTPUT_SCHEMA.model_json_schema()
                    if cls.OUTPUT_SCHEMA else None
                ),
            })

    return result
