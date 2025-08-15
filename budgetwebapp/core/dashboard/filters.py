from budget import models
from typing import Any
from datetime import datetime, date

from django.http import QueryDict

from core.logger import logger

# from django.db.models import Model

def not_none_filters(filters_tuple: tuple[list[Any] | None, ...]) -> bool:
    """
    Check if any of the filter lists is not None.

    Treats empty lists as valid (True). Only returns False if all lists are None.

    Example:

    | categories | parent_categories | transaction_types | result |
    |------------|-------------------|-------------------|--------|
    | []         | []                | []                | True   |
    | [1]        | []                | []                | True   |
    | None       | []                | []                | True   |
    | None       | None              | None              | False  |

    Args:
        filters_tuple (tuple[list[Any] | None, ...]): A tuple of filter lists which may be None or empty.

    Returns:
        bool: True if any filter list is not None, False if all are None.
    """
    return any(lst is not None for lst in filters_tuple)


def not_empty_filters(filters_tuple: tuple[list[Any] | None, ...]) -> bool:
    """
    Check if any of the filter lists contains at least one element.

    Treats None or empty lists as False.

    Example:

    | categories | parent_categories | transaction_types | result |
    |------------|-------------------|-------------------|--------|
    | []         | []                | []                | False  |
    | [1]        | []                | []                | True   |
    | None       | []                | []                | False  |
    | None       | None              | None              | False  |

    Args:
        filters_tuple (tuple[list[Any] | None, ...]): A tuple of filter lists which may be None or empty.

    Returns:
        bool: True if any filter list contains at least one element, False otherwise.
    """
    return any(lst for lst in filters_tuple if lst)


def get_param_by_key_or_none_depr(request_get: QueryDict, param: str) -> list[str] | None:
    """
    Deprecated: Retrieve a list of values for a query parameter from a GET request.

    Args:
        request_get (QueryDict): The request.GET object.
        param (str): The name of the query parameter.

    Returns:
        Optional[List[str]]: The list of values if the parameter exists, otherwise None.
    """
    if param in request_get:
        return request_get.getlist(param)
    return None


def get_dsb_filter_param_or_none(request_get: QueryDict, param_name: str) -> list[str] | None:
    """
    Retrieve and interpret a query parameter from a GET request for filtering logic.

    This function applies special rules depending on:
    1. Whether the parameter exists in the URL.
    2. Whether it has values.
    3. Whether the request contains the `submitted=1` flag.

    Filtering logic:
    - If `submitted=1` is present:
        * Parameter **missing from URL** → return an empty list `[]`
          (treat as "filter applied with no matches" — e.g., deselected in UI).
        * Parameter **present with values** → return the list of values.
        * Parameter **present but with no values** (e.g., `param=`) → return `None`
          (invalid, so filter is not applied for this parameter).
    - If `submitted=1` is **not present**:
        * Parameter **missing from URL** → return `None` (no filter applied).
        * Parameter **present with values** → return the list of values (filter applied).
        * Parameter **present but with no values** → return `None` (invalid, no filter applied).

    Args:
        request_get (QueryDict):
            The `request.GET` object containing query parameters.
        param_name (str):
            The name of the query parameter to retrieve.

    Returns:
        list[str] | None:
            - A list of strings if the parameter exists and has values.
            - An empty list `[]` if the parameter is missing but `submitted=1` is present.
            - `None` if the parameter is present but empty, or missing without `submitted=1`.
    """
    submitted: bool = request_get.get('submitted') == '1'

    if param_name in request_get:
        # Parameter exists in URL
        values: list[str] = [v for v in request_get.getlist(param_name) if v]
        return values or None  # Empty string → None
    elif submitted:
        # Param missing but form was submitted → treat as empty list
        return []
    return None  # Param missing and form not submitted


def get_names_list_by_pks(pks: list[str] | None, model: type[models.BaseModel]) -> list[str] | None:
    """Return a list of names for the given primary keys of a Django model.

    Fetches objects from the given model whose primary keys are in `pks`,
    preserves the order of `pks`, and ignores missing objects.

    Note:
        We use `type[models.BaseModel]` instead of `type[models.Model]` so
        that IDEs like PyCharm can reliably detect the `objects` manager,
        since `BaseModel` explicitly defines `objects = models.Manager()`.
        This helps with static type checking and autocompletion.

    Args:
        pks (list[str] | None): List of primary key strings. Can be None.
        model (type[models.BaseModel]): Django model class to query.

    Returns:
        list[str] | None: List of names corresponding to the given PKs.
            Returns None if `pks` is None, or an empty list if `pks` is empty.
    """
    if pks is None:
        return None
    if not pks:
        return []

    objects = model.objects.filter(pk__in=pks)
    pk_to_name = {str(obj.pk): obj.name for obj in objects}

    return [pk_to_name.get(pk) for pk in pks if pk in pk_to_name]


def get_parent_categories_names_list(parent_categories_pks: list[str] | None) -> list[str] | None:
    """Return the names of ParentCategory objects for the given primary keys.

    Args:
        parent_categories_pks (list[str] | None): List of ParentCategory PKs.

    Returns:
        list[str] | None: List of ParentCategory names. Returns None if input is None,
            or an empty list if the input is empty.
    """
    return get_names_list_by_pks(parent_categories_pks, models.ParentCategory)


def get_categories_names_list(categories_pks: list[str] | None) -> list[str] | None:
    """Return the names of Category objects for the given primary keys.

    Args:
        categories_pks (list[str] | None): List of Category PKs.

    Returns:
        list[str] | None: List of Category names. Returns None if input is None,
            or an empty list if the input is empty.
    """
    return get_names_list_by_pks(categories_pks, models.Category)


def parse_date(date_str: str | date | datetime | None, mode: str = 'month') -> datetime | None:
    """
    Normalize a date to a specific granularity or return None for 'all_time'.

    Converts the input to a datetime object if it is not already one, then
    adjusts the date according to the requested mode.

    Args:
        date_str (str | date | datetime | None): The input date to normalize. Can be:
            - None: Defaults to the current datetime.
            - str: In ISO format 'YYYY-MM-DD', 'YYYY-MM', or 'YYYY'.
            - date: datetime.date object.
            - datetime: datetime.datetime object.
        mode (str): Determines the level of granularity. One of:
            - 'day': Return the exact date and time.
            - 'month': Return the first day of the month at 00:00:00.
            - 'year': Return January 1st of the year at 00:00:00.
            - 'all_time': Return None (represents unbounded time).

    Returns:
        datetime | None: The normalized datetime object, or None for 'all_time'.

    Raises:
        ValueError: If the mode is not one of 'day', 'month', 'year', or 'all_time'.

    Examples:
        >>> parse_date('2025-07-15', 'month')
        datetime.datetime(2025, 7, 1, 0, 0)

        >>> parse_date('2025-07', 'month')
        datetime.datetime(2025, 7, 1, 0, 0)

        >>> parse_date(date(2025, 7, 15), 'year')
        datetime.datetime(2025, 1, 1, 0, 0)

        >>> parse_date(None, 'all_time')
        None
    """
    # Step 1: Convert input to datetime if necessary
    if not date_str:
        date_obj = datetime.today()
    elif isinstance(date_str, str):
        parsed_date: datetime | None = None
        # Try parsing full date, then year-month, then just year
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        if parsed_date is None:
            logger.error(f"Invalid date string format: {date_str}")
            raise ValueError(f"Invalid date string format: {date_str}")
        date_obj = parsed_date
    elif isinstance(date_str, date) and not isinstance(date_str, datetime):
        date_obj = datetime.combine(date_str, datetime.min.time())
    else:
        date_obj = date_str

    # Step 2: Adjust datetime based on the mode
    if mode == 'day':
        return date_obj
    elif mode == 'month':
        return date_obj.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif mode == 'year':
        return date_obj.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif mode == 'all_time':
        return None
    else:
        logger.error("Mode must be 'day', 'month', 'year' or 'all_time'.")
        raise ValueError("Mode must be 'day', 'month', 'year' or 'all_time'.")

# def denormalize_date

def parse_date_DEPR(date_str=None, mode='month'):
    if date_str:
        try:
            if mode == 'day':
                return datetime.strptime(date_str, '%d.%m.%Y')
            elif mode == 'month':
                return datetime.strptime(date_str, '%m.%Y')
            elif mode == 'year':
                return datetime.strptime(date_str, '%Y')
            elif mode == 'all_time':
                return None
            else:
                logger.error("Mode must be 'day', 'month', or 'year'.")
                raise ValueError("Mode must be 'day', 'month', or 'year'.")
        except ValueError:
            logger.error(f"Invalid date format for mode '{mode}'. Expected format: "
                         f"'dd.mm.yyyy' for day, 'mm.yyyy' for month, or 'yyyy' for year.")
            raise ValueError(f"Invalid date format for mode '{mode}'. Expected format: "
                             f"'dd.mm.yyyy' for day, 'mm.yyyy' for month, or 'yyyy' for year.")
    else:
        now = datetime.today()
        if mode == 'day':
            return now
        elif mode == 'month':
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif mode == 'year':
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif mode == 'all_time':
            return None
        else:
            logger.error("Mode must be 'day', 'month', or 'year'.")
            raise ValueError("Mode must be 'day', 'month', or 'year'.")
