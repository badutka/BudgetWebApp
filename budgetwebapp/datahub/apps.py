from django.apps import AppConfig


class DatahubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budgetwebapp.datahub'

    def ready(self):
        import budgetwebapp.datahub.sources.timeseries
        import budgetwebapp.datahub.sources.dataset
