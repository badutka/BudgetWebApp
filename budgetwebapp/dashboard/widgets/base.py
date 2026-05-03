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
        """
        Validate config once per widget version (updated_at).
        """

        if not self.CONFIG_SCHEMA:
            return self.widget.config

        current_version = self.widget.updated_at

        # reuse if same DB version in this instance
        if self._validated_config is not None and self._validated_at == current_version:
            return self._validated_config

        try:
            validated = self.CONFIG_SCHEMA(**self.widget.config)

            self._validated_config = validated
            self._validated_at = current_version

            logger.info(
                f"[{self.__class__.__name__}] Config validated @ {current_version}"
            )

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

    def run(self):
        config = self.get_config()
        data = self.update_data(config)
        return self.validate_output(data)

    @abstractmethod
    def update_data(self, config):
        pass