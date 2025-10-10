from budget.services.dashboard_filters import DashboardRowFilters
from core.dashboard import kpis, summary_charts

from core.logger import logger


def get_kpi_data(filters_obj: DashboardRowFilters) -> tuple[dict, tuple | None]:
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
        kpis.update_kpi_data()

    return kpis.get_kpis(
        date_unit=filters_obj.get("aggregation"),
        date_for=filters_obj.get("date_for"),
        date_from=filters_obj.get("date_from"),
        date_to=filters_obj.get("date_to"),
        apply_date_filters=filters_obj.get("apply_date_filters", False),
        apply_filters=filters_obj.get("apply_filters", False),
        transaction_types=filters_obj.get("transaction_types"),
        parent_categories=filters_obj.get("parent_categories"),
        categories=filters_obj.get("categories"),
    )


def get_summary_data(filters_obj: DashboardRowFilters) -> tuple[dict, tuple | None]:

    if filters_obj.get("refresh_kpis"):
        summary_charts.update_summary_data()

    return summary_charts.get_summaries(
        date_unit=filters_obj.get("aggregation"),
        date_for=filters_obj.get("date_for"),
        date_from=filters_obj.get("date_from"),
        date_to=filters_obj.get("date_to"),
        apply_date_filters=filters_obj.get("apply_date_filters", False),
        apply_filters=filters_obj.get("apply_filters", False),
        transaction_types=filters_obj.get("transaction_types"),
        parent_categories=filters_obj.get("parent_categories"),
        categories=filters_obj.get("categories"),
    )
