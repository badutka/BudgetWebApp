import pandas as pd

from core.logger import logger

def standardize_datetime_by_period(
        data: pd.Series | pd.DataFrame | pd.Index,
        period: str
) -> pd.Series | pd.DataFrame | pd.Index:
    """
    Standardize datetime values or index by period.

    - Removes timezone information.
    - If period == '1d', normalizes to midnight (00:00:00).
    - If period == '1h', keeps hour/minute but removes tz.

    Parameters
    ----------
    data : pd.Series | pd.DataFrame | pd.Index
        Object containing datetimes (either as values or index).
    period : str
        Period string ('1d' or '1h').

    Returns
    -------
    pd.Series | pd.DataFrame | pd.Index
        Object with standardized datetimes.
    """

    def _standardize(dt_index: pd.DatetimeIndex) -> pd.DatetimeIndex:
        dt_index = dt_index.tz_localize(None)  # remove timezone
        if period == "1d":
            return dt_index.normalize()  # set to midnight
        elif period == "1h":
            return dt_index  # keep hour precision
        else:
            raise ValueError(f"Invalid period: {period}")

    # Handle DatetimeIndex
    if isinstance(data, pd.DatetimeIndex):
        return _standardize(data)

    # Handle Series of datetimes
    elif isinstance(data, pd.Series) and pd.api.types.is_datetime64_any_dtype(data):
        dt_index = pd.DatetimeIndex(data)
        standardized_index = _standardize(dt_index)
        return pd.Series(standardized_index, index=data.index, name=data.name)

    # Handle DataFrame with datetime index
    elif isinstance(data, pd.DataFrame) and isinstance(data.index, pd.DatetimeIndex):
        data = data.copy()
        data.index = _standardize(data.index)
        return data

    else:
        raise TypeError(
            "Input must be a pandas Series, DataFrame with DatetimeIndex, or DatetimeIndex."
        )
