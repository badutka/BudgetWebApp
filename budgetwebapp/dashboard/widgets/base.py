# dashboard/widgets/base.py
from django.core.cache import cache
from abc import ABC, abstractmethod
from core.logger import logger


class BaseWidgetLogic(ABC):
    """
    Pure widget execution layer:
    - validates config
    - runs business logic
    - validates output

    NO caching, NO versioning, NO hashing.
    """

    CONFIG_SCHEMA = None
    OUTPUT_SCHEMA = None

    def __init__(self, widget):
        self.widget = widget

        # optional runtime cache ONLY for this instance
        self._validated_config = None
        self._validated_at = None  # tied to widget.updated_at

    def get_config(self):
        if not self.CONFIG_SCHEMA:
            return self.widget.config

        current_version = self.widget.updated_at
        cache_key = f"widget_config:{self.widget.id}:{current_version.timestamp()}"

        # cross-request cache
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"[{self.__class__.__name__}] using cached CONFIG for {self.widget.id}")
            return cached

        try:
            validated = self.CONFIG_SCHEMA(**self.widget.config)

            # store in both:
            self._validated_config = validated
            self._validated_at = current_version

            cache.set(cache_key, validated, timeout=None)

            logger.debug(f"[{self.__class__.__name__}] Config validated and cached @ {current_version}")

            return validated

        except Exception as e:
            raise ValueError(
                f"Invalid config for {self.__class__.__name__}: {e}"
            )

    def validate_output(self, data):
        if not self.OUTPUT_SCHEMA:
            return data

        try:
            return self.OUTPUT_SCHEMA(**data).model_dump()
        except Exception as e:
            raise ValueError(f"Invalid output for {self.__class__.__name__}: {e}")

    def run(self, filters=None):
        config = self.get_config()
        data = self.update_data(config, filters=filters)
        # todo: validate filters
        return self.validate_output(data)

    def extract(self):
            """
            Optional hook for widgets that produce domain objects
            (e.g. filters, actions, etc.)
            """
            return None

    @abstractmethod
    def update_data(self, config, filters=None):
        pass