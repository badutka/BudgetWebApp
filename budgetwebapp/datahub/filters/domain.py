# datahub/filters/domain.py

from pydantic import BaseModel
from typing import Any, Optional, List

class Filter:
    def __init__(self, field, operator, value=None, min_value=None, max_value=None, targets=None):
        self.field = field
        self.operator = operator
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.targets = targets or []

    def apply(self, row_value):
        if self.operator == "eq":
            return row_value == self.value

        if self.operator == "in":
            return row_value in self.value

        if self.operator == "gt":
            return row_value is not None and row_value > self.value

        if self.operator == "lt":
            return row_value is not None and row_value < self.value

        if self.operator == "between":
            return (
                row_value is not None
                and self.min_value <= row_value <= self.max_value
            )

        raise ValueError(f"Unsupported operator: {self.operator}")