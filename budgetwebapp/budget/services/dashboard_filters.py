from django.http import HttpRequest
from django.http import QueryDict
from core.dashboard import filters as dsb_filters

class DashboardFilters:
    """
    Encapsulates all dashboard filter logic from GET or POST requests.

    Attributes:
        request (HttpRequest): The original Django request object.
        method (str): Request method ("GET" or "POST").
        is_htmx (bool): True if request is an HTMX request.
        dsb_row_filter (str | None): Name of the filter row (e.g., "cards_row").
        refresh_kpis (bool): True if POST signals KPI refresh.
        query_data (QueryDict | None): The request parameters (GET or POST).
        cards_row_transaction_types (list | None): Selected transaction types.
        cards_row_parent_category (list | None): Selected parent categories (names).
        cards_row_category (list | None): Selected categories (names).
        aggregation (str): Aggregation period ('day', 'month', 'year', 'all_time').
        date_for (str | None): Target date for KPI calculation.
        date_from (str | None): Start date for KPI calculation.
        date_to (str | None): End date for KPI calculation.
        apply_filters (bool): True if category/transaction filters should be applied.
        apply_date_filters (bool): True if date filters should be applied.
    """

    def __init__(self, request: HttpRequest):
        """
        Initializes DashboardFilters, extracting filter and date info from the request.

        Args:
            request (HttpRequest): The incoming Django request object.
        """
        self.request: HttpRequest = request
        self.method: str = request.method
        self.is_htmx: bool = request.headers.get('HX-Request') is not None
        self.dsb_row_filter: str | None = None
        self.refresh_kpis: bool = False
        self.query_data: QueryDict | None = None

        self._parse_request()

        self.cards_row_transaction_types: list | None = dsb_filters.get_dsb_filter_param_or_none(self.query_data, 'cards_row_transaction_type')
        self.cards_row_parent_category: list | None = dsb_filters.get_dsb_filter_param_or_none(self.query_data, 'cards_row_parent_category')
        self.cards_row_category: list | None = dsb_filters.get_dsb_filter_param_or_none(self.query_data, 'cards_row_category')

        self.cards_row_parent_category = dsb_filters.get_parent_categories_names_list(self.cards_row_parent_category)
        self.cards_row_category = dsb_filters.get_categories_names_list(self.cards_row_category)

        self.aggregation: str = self.query_data.get('cards_row_aggregation', 'month')
        self.date_for: str | None = self.query_data.get('cards_row_date_for')
        self.date_for = dsb_filters.parse_date(self.date_for, mode=self.aggregation) if self.aggregation != 'all_time' else None
        self.date_from: str | None = self.query_data.get('cards_row_date_from') or None
        self.date_to: str | None = self.query_data.get('cards_row_date_to') or None

        self.apply_filters: bool = dsb_filters.not_none_filters(
            (self.cards_row_category, self.cards_row_parent_category, self.cards_row_transaction_types)
        )
        self.apply_date_filters: bool = dsb_filters.not_none_filters((self.date_from, self.date_to))

    def _parse_request(self) -> None:
        """
        Determine query_data, dsb_row_filter, and refresh flag from request.
        """
        if self.is_htmx and self.method == "POST":
            self.dsb_row_filter = self.request.POST.get('dsb_row_filter')
            self.refresh_kpis = self.request.POST.get('cards_row_refresh') == "true"
            self.query_data = self.request.POST
        else:
            self.query_data = self.request.GET
            self.dsb_row_filter = self.query_data.get('dsb_row_filter')