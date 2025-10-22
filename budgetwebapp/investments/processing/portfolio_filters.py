from django.db.models import Sum

from investments.models import Position, CashOperation, Instrument, Widget


class PortfolioDetails:
    def __init__(self):
        # Base querysets
        self.open_positions = Position.objects.filter(status="open")
        self.closed_positions = Position.objects.filter(status="close")
        self.cash_operations = CashOperation.objects.all()

    # Entry point for chaining
    def get_ops(self, type='positions'):
        if type == 'positions':
            return PortfolioQS(self.open_positions, self.closed_positions)
        elif type == 'open_pos':
            return PortfolioQS(self.open_positions)
        elif type == 'closed_pos':
            return PortfolioQS(self.closed_positions)
        elif type == 'cash_ops':
            return PortfolioQS(self.cash_operations)
        else:
            raise ValueError(f"Unknown type {type}")


class PortfolioQS:
    """
    Wraps a queryset (or multiple querysets) and provides chainable methods.
    """

    def __init__(self, *querysets):
        self.qs_list = list(querysets)
        # Start with first queryset by default for operations
        self.qs = self.qs_list[0] if self.qs_list else None

    # ------------------------
    # Filters
    # ------------------------
    def get_acc_pos(self, account_type):
        if self.qs is not None:
            self.qs = self.qs.filter(account_type=account_type)
        return self

    def get_instrument_pos(self, instrument):
        if self.qs is not None:
            self.qs = self.qs.filter(symbol=instrument)
        return self

    def get_cfd(self):
        if self.qs is not None:
            self.qs = self.qs.filter(instrument_type="CFD")
        return self

    def get_non_cfd(self):
        if self.qs is not None:
            self.qs = self.qs.exclude(instrument_type="CFD")
        return self

    def get_interest(self):
        if self.qs is not None:
            self.qs = self.qs.filter(type="Free-funds Interest")
        return self

    def get_interest_tax(self):
        if self.qs is not None:
            self.qs = self.qs.filter(type="Free-funds Interest Tax")
        return self

    def get_deposit(self):
        if self.qs is not None:
            self.qs = self.qs.filter(type__in=["deposit", "IKE Deposit", "IKZE Deposit"])
        return self

    # ------------------------
    # Aggregations / Computations
    # ------------------------
    # def free_funds(self):
    #     if self.qs is None:
    #         return 0
    #     return self.compute_purchase_value() + self.compute_profit() or 0

    # def uninvested_deposit(self):
    #     if self.qs is None:
    #         return 0
    #     return self.agg_deposit() - self.compute_purchase_value() or 0

    def agg_deposit(self):
        if self.qs is None:
            return 0
        return self.qs.aggregate(total=Sum("amount"))["total"] or 0

    def compute_purchase_value(self):
        if self.qs is None:
            return 0
        return self.qs.aggregate(total=Sum("purchase_value"))["total"] or 0

    def compute_profit(self):
        if self.qs is None:
            return 0
        return self.qs.aggregate(total=Sum("gross_pl"))["total"] or 0

    def compute_current_value(self):
        if self.qs is None:
            return 0
        return self.compute_purchase_value() + self.compute_profit() or 0

    def compute_cfd_gain(self):
        if self.qs is None:
            return 0
        agg = self.qs.aggregate(gross=Sum("gross_pl"), swap=Sum("swap"))
        return (agg["gross"] or 0) + (agg["swap"] or 0)

    def compute_non_cfd_gain(self):
        if self.qs is None:
            return 0
        agg = self.qs.aggregate(gross=Sum("gross_pl"), swap=Sum("swap"))
        return (agg["gross"] or 0) + (agg["swap"] or 0)
