import uuid
from django.db import models
from django.core.validators import MinLengthValidator
from django.core.cache import cache
from django.utils.functional import cached_property
from django.contrib.contenttypes.fields import GenericForeignKey
from polymorphic.models import PolymorphicModel

from investments.services.widgets.registry import get_widget_logic
from core.logger import logger

import traceback


class BaseModel(models.Model):
    """Abstract base class to satisfy Pycharm type checking."""
    objects = models.Manager()

    class Meta:
        abstract = True


class Dashboard(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    # def get_widgets(self):
    #     return self.dashboard_widgets.select_related('widget_content_type')


class BaseWidget(models.Model):
    """
    BaseWidget serves as the core orchestrator for the dashboard system.
    It implements a Multi-Level Caching strategy (L1-L2-L3).

    ### I. The 3-Level Caching Architecture Diagram

    ```mermaid
    graph TD
        A[Request: get_data] --> B{L1: Instance Cache}
        B -- "Hit (RAM Reference)" --> C[Return immediately]
        B -- "Miss (None)" --> D{L2: Django Cache}

        D -- "Hit (Pickle/Redis)" --> E[Deserialize + Store in L1]
        E --> F[Return Data]

        D -- "Miss (Expired/None)" --> G{L3: DataStore/Logic}
        G -- "DataStore HIT" --> H[Read from RAM-cached File]
        G -- "DataStore MISS" --> I[Read from Disk - CSV/Parquet]

        H & I --> J[Run Logic Calculations]
        J --> K[Save to L2 Cache + Store in L1]
        K --> L[Return Fresh Data]
    ```

    ### II. Caching Layers Breakdown

    *   **L1 - Instance Cache (Local RAM):**
        Lives for the duration of a single Python object in RAM.
        *Problem solved:* Template Redundancy. Prevents expensive "Pickle" deserialization
        when the same widget is called multiple times (8-16x) in one HTML template.

    *   **L2 - Django Cache (Shared/Persistent):**
        Cross-request and cross-user storage (e.g., Redis or LocMem).
        *Problem solved:* Computational Load. Prevents re-calculating heavy financial
        metrics like CAGR or TWR for every single page refresh.

    *   **L3 - DataStore Cache (File RAM):**
        Global singleton managing raw dataframes.
        *Problem solved:* I/O Bottleneck. Prevents redundant disk reads of large
        historical CSV/Parquet files when multiple widgets use the same source.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=50, blank=True, null=True)
    dashboard = models.ForeignKey(
        'Dashboard', on_delete=models.CASCADE,
        related_name="dashboard_widgets", null=True
    )

    # Layout and Timestamp fields
    row = models.PositiveIntegerField(default=1)
    column = models.PositiveIntegerField(default=1)
    width_units = models.PositiveIntegerField(default=1)
    height_units = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    config = models.JSONField(default=dict, blank=True)

    # Global Caching Configuration
    CACHE_TIMEOUT = None  # Persistent in L2 until manual refresh or server restart

    # Internal L1 Cache Storage
    _instance_cache = None  # persist as long as the Python object exists during a single Request/Response cycle.

    def __str__(self):
        return self.title

    @property
    def concrete(self):
        """Returns the specific subclass instance (e.g., OverviewWidget, ChartWidget)."""
        return self.get_concrete()

    @property
    def subtype(self):
        """Helper to get chart_subtype from the concrete child model."""
        return getattr(self.concrete, "chart_subtype", None)

    @property
    def widget_data(self):
        """
        The primary entry point for Templates.
        Usage: {{ widget.widget_data }}
        """
        return self.get_data()

    def get_data(self, force_refresh=False):
        """
        Retrieves widget data using the L1-L2-L3 caching pipeline.

        Args:
            force_refresh (bool): If True, bypasses L1 and L2 to recompute L3.
                                  Useful for manual 'Update' actions.
        """
        cache_key = f"widget_data:{self.id}"

        # --- LAYER 1: Instance Cache (Local RAM) ---
        # CASE: Template calls the widget multiple times (e.g. for Desktop/Mobile views).
        # We return the raw Python object immediately, avoiding L2 deserialization.
        if not force_refresh and self._instance_cache is not None:
            logger.debug(f"L1 HIT: Zero-latency return for {self.id}")
            return self._instance_cache

        # --- LAYER 2: Django Cache (Shared / Persistent) ---
        # CASE: A user refreshes the page or a different user views the dashboard.
        # We avoid running complex financial logic (_compute_data).
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                self._instance_cache = cached  # Populate L1 for future calls in this request
                logger.info(f"L2 HIT: Retrieved 'widget_data' cache for {self.id}")
                return cached

        # --- LAYER 3: Computation & DataStore (Source of Truth) ---
        # CASE: Cache is empty or user clicked "Refresh".
        # This triggers DataStore to load files (L3) and runs Logic classes.
        data = self._compute_data()

        # Update both layers
        cache.set(cache_key, data, timeout=self.CACHE_TIMEOUT)
        self._instance_cache = data  # Populate L1 to protect the rest of the template render
        logger.info(f"L3 COMPUTE: Fresh data generated and cached for {self.id}")

        return data

    def _compute_data(self):
        """
        Internal dispatcher that finds the appropriate Logic class
        based on widget_type and subtype.
        """
        widget_type = getattr(self, "widget_type", None)
        widget = self.get_concrete()
        subtype = getattr(widget, "chart_subtype", None)

        logic_cls = get_widget_logic(widget_type, subtype)
        if not logic_cls:
            raise ValueError(f"No logic registered for {widget_type}:{subtype}")

        # Instantiate logic with the CONCRETE widget (so logic has access to child fields)
        logic = logic_cls(widget)

        if not hasattr(logic, "update_data"):
            raise TypeError(f"Logic {logic_cls} must implement update_data()")

        return logic.update_data()

    def get_concrete(self):
        """
        Down-casts (polymorphic down-casting) the BaseWidget instance to its actual subclass
            (ChartWidget, OverviewWidget, etc.).

        This is required because Django's multi-table inheritance
        returns BaseWidget instances by default.
        """

        for attr in ["chartwidget", "overviewwidget"]:  # list all subclasses
            if hasattr(self, attr):
                return getattr(self, attr)

        return self


class ChartWidget(BaseWidget):
    # chart_subtype_choices =
    widget_type = 'chart'
    chart_subtype = models.CharField(max_length=50, choices=[
        ('timeseries', 'Time Series'),
        ('pie', 'Pie Chart'),
        ('sunburst', 'Sunburst'),
        ('pareto', 'Pareto'),
        ('bar', 'Bar Chart'),
    ])
    # variant = models.CharField(max_length=50, blank=True, null=True)  # e.g. "portfolio_value", "sector_allocation"


class OverviewWidget(BaseWidget):
    widget_type = 'overview'
    # widget_type = models.CharField(max_length=50, default='overview')


class TableWidget(BaseWidget):
    widget_type = 'table'


class Position(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    symbol = models.CharField(max_length=50)
    status = models.CharField(max_length=10)  # 'open' or 'closed'
    account_type = models.CharField(max_length=10)  # 'main', 'ike', 'ikze'

    open_time = models.DateTimeField()
    close_price = models.FloatField(null=True, blank=True)
    open_price = models.FloatField(null=True, blank=True)
    market_price = models.FloatField(null=True, blank=True)

    volume = models.FloatField()
    purchase_value = models.FloatField()
    gross_pl = models.FloatField(verbose_name="Gross P/L")
    gross_pl_perc = models.FloatField(null=True, blank=True)
    swap = models.FloatField(default=0.0)

    direction = models.CharField(max_length=100, null=True, blank=True)
    position_id = models.CharField(max_length=100, null=True, blank=True)
    instrument_type = models.CharField(max_length=20, null=True, blank=True)  # 'CFD', 'ETF', etc.

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["symbol", "account_type", "status"]),
        ]
        verbose_name_plural = "Positions"
        ordering = ["-open_time"]

    def __str__(self):
        return f"{self.id} ({self.symbol}) {self.open_time}, {self.purchase_value})"


class Instrument(BaseModel):
    CFD = 'CFD'
    ETF = 'ETF'
    ETC = 'ETC'
    STOCK = 'STOCK'

    INSTRUMENT_TYPES = [
        (CFD, 'CFD'),
        (ETF, 'ETF'),
        (ETC, 'ETC'),
        (STOCK, 'Stock'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    symbol = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    isin = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        unique=True,
        help_text="International Securities Identification Number (ISIN)"
    )
    instrument_type = models.CharField(
        max_length=20,
        choices=INSTRUMENT_TYPES,
        blank=True,
        null=True,
    )
    currency = models.CharField(
        max_length=3,
        validators=[MinLengthValidator(3)],
        blank=True,
        null=True,
        help_text="Currency of the instrument (e.g. USD, EUR)"
    )

    logo_url = models.URLField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.logo_url and self.symbol:
            formatted_symbol = self.symbol.lower().replace('.', '_')
            self.logo_url = f"https://logos.xtb.com/{formatted_symbol}.svg"

        if self.currency:
            self.currency = self.currency.upper()

        super().save(*args, **kwargs)

    def __str__(self):
        display_name = self.name or self.symbol
        return f"{display_name} ({self.instrument_type or 'Unknown'})"


class TransferOperation(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    timestamp_out = models.DateTimeField()
    timestamp_in = models.DateTimeField()

    amount_out = models.FloatField()
    currency_out = models.CharField(max_length=10)
    account_out = models.CharField(max_length=50)
    xtb_id_out = models.BigIntegerField()

    amount_in = models.FloatField()
    currency_in = models.CharField(max_length=10)
    account_in = models.CharField(max_length=50)
    xtb_id_in = models.BigIntegerField()

    exchange_rate = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["currency_out", "timestamp_in"]),
        ]
        verbose_name_plural = "TransferOperations"
        ordering = ["-timestamp_in"]

    def __str__(self):
        return f"{self.account_out} ({self.amount_out}) -> {self.account_in} ({self.amount_in}))"


class CashOperation(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    xtb_id = models.CharField(max_length=50, unique=True)

    time = models.DateTimeField()
    symbol = models.CharField(max_length=50, null=True, blank=True)
    type = models.CharField(max_length=100)
    amount = models.FloatField()
    account_type = models.CharField(max_length=10)  # 'main', 'ike', 'ikze'

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["account_type", "time"]),
        ]
        verbose_name_plural = "CashOperations"
        ordering = ["-time"]

    def __str__(self):
        return f"{self.id} ({self.xtb_id}) {self.time}, {self.symbol})"


class Account(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=12, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
