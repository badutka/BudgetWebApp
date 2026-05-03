from django.apps import AppConfig
import importlib
import pkgutil

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budgetwebapp.dashboard'

    def ready(self):
        """
        Optionally do this instead (explicit registry hook):

        # widgets/__init__.py
        from core.registry import auto_discover_widgets
        auto_discover_widgets()

        """
        import budgetwebapp.dashboard.widgets

        package = budgetwebapp.dashboard.widgets

        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            importlib.import_module(f"{package.__name__}.{module_name}")