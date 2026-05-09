# dashboard/widgets/schemas.py

from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, TypedDict, Literal, List, Any, Optional


class TimeSeriesConfig(BaseModel):
    # model_config = ConfigDict(extra="forbid")

    query: Dict = Field(default_factory=dict)
    field_config: Dict = Field(default_factory=dict)


class TimeSeriesOutput(BaseModel):
    # model_config = ConfigDict(extra="forbid")

    class SeriesMetaItem(BaseModel):
        name: str

    columns: Dict[str, List] = Field(default_factory=dict)
    meta: Dict[str, Dict[str, str]] = Field(default_factory=dict)


class OverviewConfig(BaseModel):
    # model_config = ConfigDict(extra="forbid")
    pass


class SelectFilterConfig(BaseModel):
    field: str = ""
    mode: Literal[
        "single",
        "multiple",
        "date_picker",
        "text_entry",
    ] = "single"
    operator: Literal["eq", "in"] = "eq"
    value: Any = None
    options: List[Any] = Field(default_factory=list)
    targets: Optional[List[str]] = Field(default_factory=list)
    active: bool = True


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