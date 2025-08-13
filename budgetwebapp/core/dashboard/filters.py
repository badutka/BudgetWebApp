from budget import models


def not_none_filters(filters_tuple):
    return any(lst is not None for lst in filters_tuple)


def not_empty_filters(filters_tuple):
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
