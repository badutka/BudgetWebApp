from typing import Any, Callable


def op_eq(row_value, value, **kwargs):
    return row_value == value


def op_in(row_value, value, **kwargs):
    return row_value in value


def op_gt(row_value, value, **kwargs):
    return row_value is not None and row_value > value


def op_lt(row_value, value, **kwargs):
    return row_value is not None and row_value < value


def op_between(row_value, min_value=None, max_value=None, **kwargs):
    if row_value is None:
        return False
    return min_value <= row_value <= max_value


OPERATOR_MAP: dict[str, Callable[..., bool]] = {
    "eq": op_eq,
    "in": op_in,
    "gt": op_gt,
    "lt": op_lt,
    "between": op_between,
}