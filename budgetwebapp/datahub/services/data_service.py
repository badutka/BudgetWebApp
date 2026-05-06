# datahub/services/data_service.py

import hashlib
import json
from django.core.cache import cache
from budgetwebapp.datahub.sources.registry import get_data_source
from budgetwebapp.datahub.filters.engine import FilterEngine
from core.logger import logger


def make_cache_key(prefix: str, data: dict | str):
    if isinstance(data, dict):
        raw = json.dumps(data, sort_keys=True)
    else:
        raw = str(data)

    hashed = hashlib.md5(raw.encode()).hexdigest()

    return f"{prefix}:{hashed}"

class DataService:
    """
    Responsible for:
    - fetching data
    - caching query-level results
    - applying filters (post-cache)
    """

    def __init__(self):
        self.filter_engine = FilterEngine()

    def get(
        self,
        source: str,
        query: dict | None = None,
        filters: list | None = None,
        widget_id: str | None = None,
        context: dict | None = None,
    ):
        query = query or {}
        filters = filters or []
        context = context or {}

        raw_cache_key = {"source": source, "query": query}
        cache_key = make_cache_key("data", raw_cache_key)

        # L2 cache (Redis / Django cache)
        rows = cache.get(cache_key)

        if rows is None:
            source_cls = get_data_source(source)

            if not source_cls:
                raise ValueError(f"No data source: {source}")

            rows = source_cls().fetch(query=query, context=context)

            # cache indefinitely (or set TTL if needed)
            cache.set(cache_key, rows, timeout=None)
            logger.debug(f"[{self.__class__.__name__}] cached results for {widget_id}")
        else:
            logger.debug(f"[{self.__class__.__name__}] using cached results for {widget_id}")

        # filters applied after l2 cache
        if filters:
            applicable_filters = self._resolve_filters(filters, widget_id)
            logger.debug(f"[{self.__class__.__name__}] Applying filters for {widget_id}")
            rows = self.filter_engine.apply(rows, applicable_filters)

        return rows

    def _resolve_filters(self, filters, widget_id):
        return [
            f for f in filters
            if f.targets is None or widget_id in f.targets
        ]
