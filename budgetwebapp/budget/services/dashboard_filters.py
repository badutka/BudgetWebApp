from django.http import HttpRequest
from django.http import QueryDict
from core.dashboard import filters as dsb_filters

class DashboardFilters:
    """
    Encapsulates dashboard filter logic for a specific row of widgets.

    Attributes:
        request (HttpRequest): The original Django request object.
        method (str): Request method ("GET" or "POST").
        is_htmx (bool): True if request is an HTMX request.
        dsb_row_filter (str | None): Name of the filter row (e.g., "cards_row", "spendings_row").
        refresh_kpis (bool): True if POST signals KPI refresh for this row.
        query_data (QueryDict): The request parameters (GET or POST).
        row_prefix (str): Prefix derived from dsb_row_filter (e.g., "cards_row").
        filters (dict): Dictionary of parsed filter values (transaction_types, categories, etc.).
        aggregation (str): Aggregation period ('day', 'month', 'year', 'all_time').
        date_for (str | None): Target date for KPI calculation.
        date_from (str | None): Start date for KPI calculation.
        date_to (str | None): End date for KPI calculation.
        apply_filters (bool): True if category/transaction filters should be applied.
        apply_date_filters (bool): True if date filters should be applied.
    """

    def __init__(self, request: HttpRequest):
        """
        Initialize DashboardFilters by extracting filter and date info
        for the selected row from the request.

        Args:
            request (HttpRequest): The incoming Django request object.
        """
        self.request: HttpRequest = request
        self.method: str = request.method
        self.is_htmx: bool = request.headers.get("HX-Request") is not None
        self.dsb_row_filter: str | None = None
        self.refresh_kpis: bool = False
        self.query_data: QueryDict = QueryDict()
        self.row_prefix: str = ""
        self.filters: dict = {}

        self._parse_request()

        if self.dsb_row_filter:
            self.row_prefix = f"{self.dsb_row_filter}_"

        # --- dynamically extract filters for this row ---
        self.filters["transaction_types"] = dsb_filters.get_dsb_filter_param_or_none(self.query_data, f"{self.row_prefix}transaction_type")
        self.filters["parent_categories"] = dsb_filters.get_dsb_filter_param_or_none(self.query_data, f"{self.row_prefix}parent_category")
        self.filters["categories"] = dsb_filters.get_dsb_filter_param_or_none(self.query_data, f"{self.row_prefix}category")

        # normalize names
        self.filters["parent_categories"] = dsb_filters.get_parent_categories_names_list(self.filters["parent_categories"])
        self.filters["categories"] = dsb_filters.get_categories_names_list(self.filters["categories"])

        # --- aggregation and dates ---
        self.aggregation: str = self.query_data.get(f"{self.row_prefix}aggregation", "month")
        self.date_for: str | None = self.query_data.get(f"{self.row_prefix}date_for")
        self.date_for = dsb_filters.parse_date(self.date_for, mode=self.aggregation)if self.aggregation != "all_time"else None
        self.date_from: str | None = self.query_data.get(f"{self.row_prefix}date_from") or None
        self.date_to: str | None = self.query_data.get(f"{self.row_prefix}date_to") or None

        self.apply_filters: bool = dsb_filters.not_none_filters(
            (self.filters["categories"], self.filters["parent_categories"], self.filters["transaction_types"])
        )
        self.apply_date_filters: bool = dsb_filters.not_none_filters((self.date_from, self.date_to))

    def _parse_request(self) -> None:
        """
        Determine query_data, dsb_row_filter, and refresh flag from request.
        """
        if self.is_htmx and self.method == "POST":
            self.dsb_row_filter = self.request.POST.get("dsb_row_filter")
            self.refresh_kpis = self.request.POST.get("cards_row_refresh") == "true"
            self.query_data = self.request.POST
        else:
            self.query_data = self.request.GET
            self.dsb_row_filter = self.query_data.get("dsb_row_filter")