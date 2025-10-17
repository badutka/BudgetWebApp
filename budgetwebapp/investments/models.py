from django.db import models
import uuid


class Position(models.Model):
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


class Instrument(models.Model):
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

    logo_url = models.URLField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.logo_url and self.symbol:
            formatted_symbol = self.symbol.lower().replace('.', '_')
            self.logo_url = f"https://logos.xtb.com/{formatted_symbol}.svg"

        super().save(*args, **kwargs)

    def __str__(self):
        display_name = self.name or self.symbol
        return f"{display_name} ({self.instrument_type or 'Unknown'})"


class CashOperation(models.Model):
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
