from django.core.cache import cache
from abc import ABC, abstractmethod

from core.logger import logger


class BaseWidgetLogic(ABC):
    """
    Pure widget execution layer:
    - validates config
    - validates state
    - runs business logic
    - validates output

    NO external orchestration, NO versioning logic outside cache boundaries.
    """

    CONFIG_SCHEMA = None
    STATE_SCHEMA = None
    OUTPUT_SCHEMA = None

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
            logger.debug(f"[{self.__class__.__name__}] using in-memory CONFIG cache for {self.widget}")
            return self._validated_config

        if not self.CONFIG_SCHEMA:
            return self.widget.config or {}

        cache_key = f"widget_config:{self.widget.id}:{current_version.timestamp()}"
        cached = cache.get(cache_key)

        if cached is not None:
            logger.debug(f"[{self.__class__.__name__}] using Django CONFIG cache for {self.widget}")
            self._validated_config = cached
            self._validated_config_at = current_version
            return cached

        try:
            validated = self.CONFIG_SCHEMA(**(self.widget.config or {}))

            self._validated_config = validated
            self._validated_config_at = current_version

            cache.set(cache_key, validated, timeout=None)

            logger.debug(f"[{self.__class__.__name__}] config validated + cached for {self.widget}")

            return validated

        except Exception as e:
            raise ValueError(f"Invalid config for {self.__class__.__name__}: {e}")


    def get_state(self):
        current_version = self.widget.updated_at

        if (
            self._validated_state is not None
            and self._validated_state_at == current_version
        ):
            logger.debug(f"[{self.__class__.__name__}] using in-memory STATE cache for {self.widget}")
            return self._validated_state

        if not self.STATE_SCHEMA:
            return self.widget.state or {}

        try:
            validated = self.STATE_SCHEMA(**(self.widget.state or {}))

            self._validated_state = validated
            self._validated_state_at = current_version

            logger.debug(f"[{self.__class__.__name__}] state validated for {self.widget}")

            return validated

        except Exception as e:
            raise ValueError(f"Invalid state for {self.__class__.__name__}: {e}")


    def validate_output(self, data):
        if not self.OUTPUT_SCHEMA:
            logger.debug(f"[{self.__class__.__name__}] no output schema for {self.widget}, returning raw data")
            return data

        try:
            validated = self.OUTPUT_SCHEMA(**data).model_dump()
            logger.debug(f"[{self.__class__.__name__}] output validated for {self.widget}")
            return validated

        except Exception as e:
            raise ValueError(f"Invalid output for {self.__class__.__name__}: {e}")


    def run(self, filters=None):
        config = self.get_config()
        state = self.get_state()

        data = self.update_data(
            config=config,
            state=state,
            filters=filters,
        )

        return self.validate_output(data)


    @abstractmethod
    def update_data(self, config, state, filters=None):
        pass