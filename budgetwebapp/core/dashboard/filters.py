from budget import models
from typing import Any

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


def get_parent_categories_names_list(parent_categories_pks):
    if parent_categories_pks is None:
        return None
    if not parent_categories_pks:  # empty list
        return []

    # parent_categories_pks is a list of PK strings
    # Fetch only the ParentCategory objects with those PKs
    parent_categories = models.ParentCategory.objects.filter(pk__in=parent_categories_pks)

    # Create a dict mapping pk -> name
    pk_to_name = {str(cat.pk): cat.name for cat in parent_categories}

    # Map the input list of PKs to their corresponding names,
    # preserving the original order and ignoring missing PKs
    names_list = [pk_to_name.get(pk) for pk in parent_categories_pks if pk in pk_to_name]

    return names_list
