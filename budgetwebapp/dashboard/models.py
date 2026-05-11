# dashboard/models.py
import uuid
from django.db import models
from django.utils.text import slugify

from budgetwebapp.dashboard.widgets.factory import create_default_config
from budgetwebapp.dashboard.core.registry import get_widget_handler
# from budgetwebapp.dashboard.core.services import WidgetService
from core.logger import logger

class BaseModel(models.Model):
    """Abstract base class to satisfy Pycharm type checking."""
    objects = models.Manager()

    class Meta:
        abstract = True


class Dashboard(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    grid_columns = models.PositiveIntegerField(default=32)
    max_width_px = models.PositiveIntegerField(default=1400)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            # ensure uniqueness
            while Dashboard.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    # def get_widgets(self):
    #     return self.dashboard_widgets.select_related('widget_content_type')


class BaseWidget(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    dashboard = models.ForeignKey(
        "Dashboard",
        on_delete=models.CASCADE,
        related_name="widgets"
    )

    title = models.CharField(max_length=100)

    widget_type = models.CharField(max_length=50)
    subtype = models.CharField(max_length=50, null=True, blank=True)

    config = models.JSONField(default=dict, blank=True)
    state = models.JSONField(default=dict, blank=True)

    row = models.PositiveIntegerField(default=1)
    column = models.PositiveIntegerField(default=1)
    width_units = models.PositiveIntegerField(default=1)
    height_units = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def handler(self):
        if not hasattr(self, "_handler"):
            handler_cls = get_widget_handler(
                self.widget_type,
                self.subtype,
            )

            if not handler_cls:
                raise ValueError(f"No handler for {self.widget_type}:{self.subtype}")

            self._handler = handler_cls(self)
            logger.warn(f'Created new handler instance for {str(self)}')

        return self._handler

    def save(self, *args, **kwargs):
        
        if not self.config:
            self.config = create_default_config(self.handler)

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'<{self.title}>:<{self.widget_type}>:<{self.subtype}>:<{self.id}>'

    # def get_data(self, force_refresh=False):
    #     return WidgetService(self).get_data(force_refresh)
