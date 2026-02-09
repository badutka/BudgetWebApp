import uuid
from django.db import models
from django.core.validators import MinLengthValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from polymorphic.models import PolymorphicModel

from investments.services.widgets.registry import get_widget_logic
from core.logger import logger


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


class BaseWidget(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=50, blank=True, null=True)  # optional reference

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    data = models.JSONField(default=dict, blank=True)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.title

    def update_widget_data(self):
        """
        Generic dispatcher for all widget subclasses.
        Uses registry to find the appropriate logic class and run its update method.
        """

        widget_type = getattr(self, "widget_type", None)
        if not widget_type:
            raise ValueError(f"{self.__class__.__name__} has no 'widget_type' defined")

        widget = self.get_real_instance()
        # widget = BaseWidget.objects.first()  # todo: explore PolymorphicModel approach

        subtype = getattr(widget, "chart_subtype", None)

        logic_cls = get_widget_logic(widget_type, subtype)
        if not logic_cls:
            raise ValueError(f"No logic registered for ({widget_type}, {subtype})")

        logic = logic_cls(self)
        if not hasattr(logic, "update_data"):
            raise TypeError(f"{logic_cls.__name__} must define an 'update_data()' method")

        logic.update_data()

        self.save(update_fields=["data"])

    def get_real_instance(self):
        # polymorphic down-casting from Widget to the actual subclass (ChartWidget, OverviewWidget, etc.)
        # return the "most derived" instance
        for attr in ["chartwidget", "overviewwidget"]:  # list all subclasses
            if hasattr(self, attr):
                return getattr(self, attr)
        return self


class DashboardWidget(BaseModel):
    """
    A link between a Dashboard and a reusable widget definition.
    Stores layout attributes and optional config overrides.

    Dashboard
    └── DashboardWidget
        ├── row, column, width_units, height_units
        ├── overrides
        └── widget → (OverviewWidget, PerformanceWidget, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="dashboard_widgets")
    widget = models.ForeignKey(BaseWidget, on_delete=models.CASCADE, null=True)

    # Generic FK lets you attach any widget type (OverviewWidget, etc.)
    # widget_content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    # widget_object_id = models.UUIDField()
    # widget = GenericForeignKey('widget_content_type', 'widget_object_id')

    # Layout attributes
    row = models.PositiveIntegerField(default=1)
    column = models.PositiveIntegerField(default=1)
    width_units = models.PositiveIntegerField(default=1)
    height_units = models.PositiveIntegerField(default=1)

    # Dashboard-specific overrides
    overrides = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # class Meta:
    #     unique_together = ('dashboard', 'widget_content_type', 'widget_object_id')

    def __str__(self):
        return f"{self.widget} on {self.dashboard.name}"


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
