from budget.services.dashboard_filters import DashboardFilters
from core.dashboard import kpi_reading, kpi_saving

def get_kpis(filters: DashboardFilters) -> tuple[dict, tuple | None]:
    """
    Calculate and return KPI data.

    If HTMX POST signals a refresh, daily KPIs are recalculated.

    Args:
        filters (DashboardFilters): DashboardFilters object with applied filters and date range.

    Returns:
        tuple:
            dict: Dictionary of KPI values.
            tuple | None: Start and end dates, or None if not applicable.
    """
    if filters.is_htmx and filters.refresh_kpis:
        kpi_saving.calculate_daily_kpis()

    return kpi_reading.get_kpis(
        filters.aggregation,
        filters.date_for,
        filters.date_from,
        filters.date_to,
        filters.apply_date_filters,
        filters.apply_filters,
        filters.cards_row_transaction_types,
        filters.cards_row_parent_category,
        filters.cards_row_category
    )