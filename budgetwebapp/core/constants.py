# =============================================================================
# Frequency and date format mappings
# =============================================================================
# FREQ_MAP:
#   Maps human-readable frequency names (e.g. "daily", "monthly") to
#   Pandas-compatible frequency codes used for period and date grouping.
#
# FMT_MAP:
#   Maps Pandas frequency codes to default date display formats (strftime-style).
#   These are used for generating compact date range labels, e.g.:
#     - FREQ_MAP["month"] -> "M"
#     - FMT_MAP["M"]      -> "%m.%Y"   → "09.2025"
#
# Used in: date utilities, KPI calculations, and reporting functions.
# =============================================================================


FREQ_MAP = {
    "day": "D",
    "daily": "D",
    "month": "M",
    "monthly": "M",
    "year": "Y",
    "yearly": "Y",
    "week": "W",
    "weekly": "W",
}

FMT_MAP = {
    "D": "%d.%m.%Y",
    "W": "%d.%m.%Y",
    "M": "%m.%Y",
    "Q": "Q%q %Y",
    "Y": "%Y",
}

KPI_COLS = ['income', 'expenses', 'inner', 'num_transactions', 'net_savings', 'accounts_balance']
