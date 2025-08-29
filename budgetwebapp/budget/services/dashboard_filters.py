from django.http import HttpRequest
from django.http import QueryDict
from core.dashboard import filters as dsb_filters

from core.logger import logger


class DashboardFilters:
    """
    Encapsulates dashboard filter logic for a specific row of widgets.
    Each row has its own independent filter state.

    Attributes:
        request (HttpRequest): The original Django request object.
        method (str): Request method ("GET" or "POST").
        is_htmx (bool): True if request is an HTMX request.
        rows dict[str, dict]: dictionary containing filter parameters by filter row name.
    """

    def __init__(self, request: HttpRequest):
        self.request: HttpRequest = request
        self.method: str = request.method
        self.is_htmx: bool = bool(request.headers.get("HX-Request"))
        self.rows: dict[str, dict] = {}  # row_name -> filter state
        self._parse_request()

    def _parse_request(self):
        query_data = self.request.POST if self.is_htmx and self.method == "POST" else self.request.GET

        # Prepopulate default rows even if nothing in request
        default_rows = ["cards_row", "summary_row"]  # extendable
        for row_name in default_rows:
            if row_name == "cards_row":
                self.rows[row_name] = self._parse_cards_row(query_data)
            elif row_name == "summary_row":
                self.rows[row_name] = self._parse_summary_row(query_data)
            # future rows can be added here

    # --- Row parsers ---
    def _parse_cards_row(self, query_data) -> dict:
        prefix = "cards_row"
        row = {}
        row["dsb_row_filter"] = self._get_dsb_row_filter(query_data, prefix)
        row["transaction_types"] = self._get_transaction_types(query_data, prefix)
        row["parent_categories"] = self._get_parent_categories(query_data, prefix)
        row["categories"] = self._get_categories(query_data, prefix)
        row["aggregation"] = self._get_aggregation(query_data, prefix)
        row["date_for"] = self._get_date_for(query_data, prefix, row["aggregation"])
        row["date_from"] = self._get_date_from(query_data, prefix)
        row["date_to"] = self._get_date_to(query_data, prefix)
        row["apply_filters"] = self._get_apply_filters(row["categories"], row["parent_categories"], row["transaction_types"])
        row["apply_date_filters"] = self._get_apply_date_filters(row["date_from"], row["date_to"])
        row["refresh_kpis"] = self._get_refresh_kpis(query_data, prefix)
        return row

    def _parse_summary_row(self, query_data) -> dict:
        prefix = "summary_row"
        row = {}
        row["dsb_row_filter"] = self._get_dsb_row_filter(query_data, prefix)
        row["transaction_types"] = self._get_transaction_types(query_data, prefix)
        row["parent_categories"] = self._get_parent_categories(query_data, prefix)
        row["categories"] = self._get_categories(query_data, prefix)
        row["date_from"] = self._get_date_from(query_data, prefix)
        row["date_to"] = self._get_date_to(query_data, prefix)
        row["apply_filters"] = self._get_apply_filters(row["categories"], row["parent_categories"], row["transaction_types"])
        row["apply_date_filters"] = self._get_apply_date_filters(row["date_from"], row["date_to"])
        row["refresh_kpis"] = self._get_refresh_kpis(query_data, prefix)
        # summary_row does not use aggregation/date_for
        return row

    # --- Private parameter methods ---
    def _get_dsb_row_filter(self, query_data, prefix: str) -> str:
        return query_data.get(f"{prefix}_filter") or prefix

    def _get_transaction_types(self, query_data, prefix: str):
        return dsb_filters.get_dsb_filter_param_or_none(query_data, f"{prefix}_transaction_type", prefix)

    def _get_parent_categories(self, query_data, prefix: str):
        categories = dsb_filters.get_dsb_filter_param_or_none(query_data, f"{prefix}_parent_category", prefix)
        return dsb_filters.get_parent_categories_names_list(categories)

    def _get_categories(self, query_data, prefix: str):
        categories = dsb_filters.get_dsb_filter_param_or_none(query_data, f"{prefix}_category", prefix)
        return dsb_filters.get_categories_names_list(categories)

    def _get_aggregation(self, query_data, prefix: str) -> str:
        return query_data.get(f"{prefix}_aggregation", "month")

    def _get_date_for(self, query_data, prefix: str, aggregation: str):
        date_for = query_data.get(f"{prefix}_date_for")
        return dsb_filters.parse_date(date_for, mode=aggregation) if aggregation != "all_time" else None

    def _get_date_from(self, query_data, prefix: str):
        return query_data.get(f"{prefix}_date_from") or None

    def _get_date_to(self, query_data, prefix: str):
        return query_data.get(f"{prefix}_date_to") or None

    def _get_apply_filters(self, categories, parent_categories, transaction_types):
        return dsb_filters.not_none_filters((categories, parent_categories, transaction_types))

    def _get_apply_date_filters(self, date_from, date_to):
        return dsb_filters.not_none_filters((date_from, date_to))

    def _get_refresh_kpis(self, query_data, prefix: str) -> bool:
        return query_data.get(f"{prefix}_refresh") == "true"

    # --- Public API ---
    def get_row(self, row_name: str) -> dict | None:
        """Get the filter dict for a specific row."""
        return self.rows.get(row_name)

    def all_rows(self) -> dict[str, dict]:
        """Return all row filters."""
        return self.rows
