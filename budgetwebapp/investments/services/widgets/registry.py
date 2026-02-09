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


_DATASET_LOADERS = {}


def register_dataset(name):
    def wrapper(fn):
        _DATASET_LOADERS[name] = fn
        return fn

    return wrapper


def load_dataset(name: str, **kwargs):
    """Load a dataset by name, calling the registered loader."""
    loader = _DATASET_LOADERS.get(name)
    if not loader:
        raise ValueError(f"No dataset loader registered for '{name}'")
    return loader(**kwargs)
