from django.apps import AppConfig


class InvestmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budgetwebapp.investments'

    def ready(self):
        # Import all widget logic so registration decorators run
        from .services.widgets import chart_logic  # , kpi_logic, overview_logic
