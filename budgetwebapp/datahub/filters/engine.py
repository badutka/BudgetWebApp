# datahub/filters/engine.py

from typing import List
from budgetwebapp.datahub.filters.domain import Filter
from core.logger import logger


class FilterEngine:
    """
    Applies filters to row-based datasets.
    """

    def apply(self, rows: list[dict], filters: List[Filter]):
        if not filters:
            return rows

        result = []

        for row in rows:
            if self._matches(row, filters):
                result.append(row)

        return result

    def _matches(self, row: dict, filters: List[Filter]) -> bool:
        for f in filters:
            value = self._get_value(row, f.field)

            if not f.apply(value):
                return False

        return True

    def _get_value(self, row: dict, field: str):
        """
        Supports flat and structured rows
        """

        if field in row:
            return row[field]

        if "dimensions" in row and field in row["dimensions"]:
            return row["dimensions"][field]

        if "metrics" in row and field in row["metrics"]:
            return row["metrics"][field]

        return None

