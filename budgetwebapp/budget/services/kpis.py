from budget.services.dashboard_filters import DashboardFilters
from core.dashboard import kpi_reading, kpi_saving

from core.logger import logger

def get_kpis(dashboard_filters: DashboardFilters) -> tuple[dict, tuple | None]:
    """
    Calculate and return KPI data for the 'cards_row' only.

    Args:
        dashboard_filters (DashboardFilters): Filter object containing all row filters.

    Returns:
        tuple:
            dict: KPI values
            tuple | None: start/end dates for KPI calculation
    """
    row_filters = dashboard_filters.get_row("cards_row") or {}

    # Recalculate daily KPIs if requested via HTMX POST
    if dashboard_filters.is_htmx and row_filters.get("refresh_kpis"):
        kpi_saving.calculate_daily_kpis()

    return kpi_reading.get_kpis(
        granularity=row_filters.get("aggregation"),
        date_for=row_filters.get("date_for"),
        date_from=row_filters.get("date_from"),
        date_to=row_filters.get("date_to"),
        apply_date_filters=row_filters.get("apply_date_filters", False),
        apply_filters=row_filters.get("apply_filters", False),
        transaction_types=row_filters.get("transaction_types"),
        parent_categories=row_filters.get("parent_categories"),
        categories=row_filters.get("categories"),
    )