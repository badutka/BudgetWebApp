from budget import models
from typing import Any

from django.http import QueryDict
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
