# datahub/filters/domain.py

from pydantic import BaseModel
from typing import Any, Optional, List
from .operators import OPERATOR_MAP


class Filter:
    def __init__(
        self,
        field: str,
        operator: str,
        value=None,
        min_value=None,
        max_value=None,
        targets=None,
    ):
        self.field = field
        self.operator = operator
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.targets = targets or []

    def apply(self, row_value) -> bool:
        handler = OPERATOR_MAP.get(self.operator)

        if not handler:
            raise ValueError(f"Unsupported operator: {self.operator}")

        return handler(
            row_value,
            value=self.value,
            min_value=self.min_value,
            max_value=self.max_value,
        )

        raise ValueError(f"Unsupported operator: {self.operator}")