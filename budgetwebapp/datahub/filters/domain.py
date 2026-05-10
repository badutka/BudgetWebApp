# datahub/filters/domain.py

from pydantic import BaseModel
from typing import Any, Optional, List
from .operators import OPERATOR_MAP
from core.logger import logger

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
    
    def __repr__(self):
        params = [f"field={self.field!r}", f"operator={self.operator!r}"]
        
        if self.value is not None:
            params.append(f"value={self.value!r}")
        if self.min_value is not None:
            params.append(f"min_value={self.min_value!r}")
        if self.max_value is not None:
            params.append(f"max_value={self.max_value!r}")
        if self.targets:
            params.append(f"targets={self.targets!r}")
            
        return f"Filter({', '.join(params)})"