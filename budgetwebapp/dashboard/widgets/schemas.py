# dashboard/widgets/schemas.py

from pydantic import BaseModel, ConfigDict
from typing import Dict, TypedDict, Literal, List


class TimeSeriesConfig(BaseModel):
    # model_config = ConfigDict(extra="forbid")

    account_type: str
    # interval: Literal["1d", "1h", "1w"]
    # moving_average: bool


class TimeSeriesOutput(BaseModel):
    # model_config = ConfigDict(extra="forbid")

    class SeriesMetaItem(BaseModel):
        name: str

    date: List[str]
    series: Dict[str, List[float]]
    series_meta: Dict[str, SeriesMetaItem]


class OverviewConfig(BaseModel):
    # model_config = ConfigDict(extra="forbid")
    pass
