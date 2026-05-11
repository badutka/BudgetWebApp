from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.http import HttpResponse
from pydantic import ValidationError
import json

from .models import Dashboard, BaseWidget
from budgetwebapp.dashboard.core.services import build_filters
from budgetwebapp.dashboard.widgets.schemas import SelectFilterConfig

from .core.services import WidgetService
from core.logger import logger


def index(request):
    return render(request, "dashboard/index.html")


def dashboard_view(request, slug):
    dashboard = get_object_or_404(Dashboard, slug=slug)

    widgets = BaseWidget.objects.filter(dashboard=dashboard)
    # account_type = request.GET.get('account_type')

    filter_widgets = [w for w in widgets if w.widget_type == "filter"]
    filters = build_filters(filter_widgets)

    # service = DashboardService(dashboard)
    # widgets = service.get_widgets_data(request_params=request.GET)

    # if account_type:
    #     widgets = widgets.filter(config__account_type=account_type)

    widget_list = []

    for widget in widgets:
        widget.widget_data = widget.handler.run(filters=filters)
        widget.ui_schema = widget.handler.get_ui_schema()
        widget.template = widget.handler.get_template(context="dashboard")

        widget_list.append(widget)
        logger.error(widget.id)
        logger.info(f'{widget.widget_data = }')
        logger.info(f'{widget.ui_schema = }')

    context = {
        "widgets": widget_list,
        "dashboard": dashboard,
        "enable_account_details_visit": dashboard.slug == "portfolio-overview",
    }

    return render(request, "dashboard/dashboard.html", context)


def dashboard_sidebar_content(request, widget_id):
    widget = BaseWidget.objects.get(id=widget_id)

    handler = widget.handler

    context = {
        "widget": widget,
        "config": handler.get_config().model_dump(),
        "state": handler.get_state().model_dump(),
        "ui": handler.get_ui_schema(),
    }

    template_map = {
        "filter:select": "dashboard/sidebar/select_filter.html",
    }

    print(context)
    key = f"{widget.widget_type}:{widget.subtype}"
    template = template_map.get(key)

    return render(request, template, context)


def update_widget(request, widget_id):
    widget = get_object_or_404(BaseWidget, id=widget_id)
    handler = widget.handler
    logger.debug('Updating widget: %s', widget_id)
    config_updates = {}
    state_updates = {}

    for key, value in request.POST.items():
        if key == "csrfmiddlewaretoken":
            continue

        if hasattr(handler.CONFIG_SCHEMA, "model_fields") and key in handler.CONFIG_SCHEMA.model_fields:
            config_updates[key] = value
        else:
            state_updates[key] = value

    logger.debug(f'{state_updates = }')
    logger.debug(f'{config_updates = }')

    # config
    if config_updates:
        merged = {**(widget.config or {}), **config_updates}
        widget.config = handler.CONFIG_SCHEMA(**merged).model_dump()

    # state
    if state_updates:
        merged = {**(widget.state or {}), **state_updates}
        widget.state = handler.STATE_SCHEMA(**merged).model_dump()

    widget.save()

    # recompute filters
    dashboard_widgets = BaseWidget.objects.filter(dashboard=widget.dashboard)
    filters = build_filters([w for w in dashboard_widgets if w.widget_type == "filter"])

    # recompute widget
    widget.widget_data = handler.run(filters=filters)
    widget.ui_schema = handler.get_ui_schema()

    widget.template = handler.get_template(context="dashboard")

    context = {
        "widget": widget,
    }

    return render(request, widget.template, context)


@require_POST
def update_widget_layout(request):
    data = json.loads(request.body)
    widgets = data.get("widgets", [])

    for w in widgets:
        try:
            widget = BaseWidget.objects.get(id=w["id"])
            widget.column = w["x"] + 1  # gridstack is 0-based
            widget.row = w["y"] + 1
            widget.width_units = w["w"]
            widget.height_units = w["h"]
            widget.save(update_fields=["column", "row", "width_units", "height_units"])
        except BaseWidget.DoesNotExist:
            continue

    return JsonResponse({"status": "ok"})
