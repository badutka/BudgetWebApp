from django.apps import AppConfig


class BudgetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budgetwebapp.budget'

    def ready(self):
        import budgetwebapp.budget.signals