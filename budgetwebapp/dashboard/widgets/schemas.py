# dashboard/widgets/schemas.py

from pydantic import BaseModel, ConfigDict
from typing import Dict, TypedDict, Literal, List, Any, Optional


class TimeSeriesConfig(BaseModel):
    # model_config = ConfigDict(extra="forbid")

    query: Dict
    field_config: Dict


class TimeSeriesOutput(BaseModel):
    # model_config = ConfigDict(extra="forbid")

    class SeriesMetaItem(BaseModel):
        name: str

    columns: Dict[str, List]
    meta: Dict[str, Dict[str, str]]


class OverviewConfig(BaseModel):
    # model_config = ConfigDict(extra="forbid")
    pass


class SelectFilterConfig(BaseModel):
    field: str
    operator: Literal["eq", "in"] = "eq"
    value: Any
    options: Optional[List[Any]] = []
    targets: Optional[List[str]] = None


class RangeFilterConfig(BaseModel):
    field: str
    operator: Literal["gt", "lt", "between"]
    value: Optional[Any] = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    targets: Optional[list[str]] = None


class DateFilterConfig(BaseModel):
    field: str

    # how the filter behaves
    mode: Literal["absolute", "relative"]

    # --- absolute ---
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # --- relative ---
    last_n: Optional[int] = None
    unit: Optional[Literal["day", "week", "month", "year"]] = None

    targets: Optional[list[str]] = None