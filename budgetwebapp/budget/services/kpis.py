from budget.services.dashboard_filters import DashboardRowFilters
from core.dashboard import kpi_reading, kpi_saving

from core.logger import logger

def get_kpis(filters_obj: DashboardRowFilters) -> tuple[dict, tuple | None]:
    """
    Calculate and return KPI data for the 'cards_row' only.

    Args:
        filters_obj (DashboardRowFilters): Filter object containing all row filters.

    Returns:
        tuple:
            dict: KPI values
            tuple | None: start/end dates for KPI calculation
    """

    # Recalculate daily KPIs if requested via HTMX
    if filters_obj.get("refresh_kpis"):
        kpi_saving.calculate_daily_kpis()

    return kpi_reading.get_kpis(
        granularity=filters_obj.get("aggregation"),
        date_for=filters_obj.get("date_for"),
        date_from=filters_obj.get("date_from"),
        date_to=filters_obj.get("date_to"),
        apply_date_filters=filters_obj.get("apply_date_filters", False),
        apply_filters=filters_obj.get("apply_filters", False),
        transaction_types=filters_obj.get("transaction_types"),
        parent_categories=filters_obj.get("parent_categories"),
        categories=filters_obj.get("categories"),
    )