# dashboard/core/services.py

from django.core.cache import cache
from .registry import get_widget_handler, get_widget_metadata
from core.logger import logger


class WidgetService:

    def __init__(self, widget):
        self.widget = widget
        self._memory_cache = None

    def get_data(self, force_refresh=False):
        """
        Returns widget data using:
        L1 (memory) → L2 (cache) → L3 (compute)
        """

        cache_key = (
            f"widget:{self.widget.id}:"
            f"{self.widget.updated_at.isoformat()}:data"
        )

        # --- L1 CACHE ---
        if not force_refresh and self._memory_cache:
            logger.debug(f"L1 HIT: Zero-latency return for {self.widget.id}")
            return self._memory_cache

        # --- L2 CACHE ---
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info(f"L2 HIT: Retrieved 'widget_data' cache for {self.widget.id}")
                self._memory_cache = cached
                return cached

        # subtype = self.widget.config.get("subtype")

        # resolve handler
        handler_cls = get_widget_handler(
            self.widget.widget_type,
            self.widget.subtype
        )
        # metadata = get_widget_metadata()
        # logger.debug(f'{metadata = }')

        if not handler_cls:
            raise ValueError(f"No handler registered for {self.widget.widget_type}:{self.widget.subtype}")

        # --- EXECUTION (L3) ---
        handler = handler_cls(self.widget)

        # Use safe execution wrapper
        data = handler.run()

        # cache store
        cache.set(cache_key, data, timeout=None)
        self._memory_cache = data

        logger.info(f"L3 COMPUTE: Fresh data generated and cached for {self.widget.id}")

        return data
