from typing import Dict, Type
from .base import BaseDataSource

_DATA_SOURCE_REGISTRY: Dict[str, Type[BaseDataSource]] = {}


def register_data_source(name: str):
    def wrapper(cls: Type[BaseDataSource]):
        if not issubclass(cls, BaseDataSource):
            raise TypeError(f"{cls} must inherit from BaseDataSource")

        _DATA_SOURCE_REGISTRY[name] = cls
        cls.SOURCE_NAME = name

        return cls

    return wrapper


def get_data_source(name: str) -> Type[BaseDataSource] | None:
    return _DATA_SOURCE_REGISTRY.get(name)


def list_data_sources():
    return list(_DATA_SOURCE_REGISTRY.keys())
