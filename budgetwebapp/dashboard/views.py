from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
import json

from budgetwebapp.dashboard.models import Dashboard, BaseWidget
from budgetwebapp.dashboard.core.services import build_filters, DashboardService
from core.logger import logger


def index(request):
    return render(request, "dashboard/index.html")


def dashboard_view(request, slug):
    dashboard = get_object_or_404(Dashboard, slug=slug)
    # todo eventually move filters to dashboard.get_runtime_context(), to avoid repeated rebuilding
    # stop "detecting filters" and instead make filters first-class outputs of widgets
    widgets = DashboardService(dashboard).execute()

    return render(request, "dashboard/dashboard.html", {
        "widgets": widgets,
        "dashboard": dashboard,
        "enable_account_details_visit": dashboard.slug == "portfolio-overview",
    })


def dashboard_sidebar_content(request, widget_id):
    widget = BaseWidget.objects.get(id=widget_id)

    definition = widget.get_definition()

    config_schema = definition.config_schema
    state_schema = definition.state_schema

    context = {
        "widget": widget,
        "config": config_schema(**widget.config).model_dump()
                  if config_schema else widget.config,
        "state": state_schema(**widget.state).model_dump()
                 if state_schema else widget.state,
        "ui": definition.ui_schema,
    }

    template_map = {
        "filter:select": "dashboard/sidebar/select_filter.html",
    }

    template = template_map.get(f"{widget.widget_type}:{widget.subtype}")

    return render(request, template, context)


def update_widget(request, widget_id):
    widget = get_object_or_404(BaseWidget, id=widget_id)
    logger.debug('Updating widget: %s', widget_id)

    definition = widget.get_definition()

    config_updates = {}
    state_updates = {}

    for key, value in request.POST.items():
        if key == "csrfmiddlewaretoken":
            continue

        if definition.config_schema and key in definition.config_schema.model_fields:
            config_updates[key] = value
        else:
            state_updates[key] = value

    logger.debug(f"{config_updates = }")
    logger.debug(f"{state_updates = }")

    # ------------------
    # CONFIG UPDATE
    # ------------------
    if config_updates:
        merged = {**(widget.config or {}), **config_updates}
        widget.config = (
            definition.config_schema(**merged).model_dump()
            if definition.config_schema else merged
        )

    # ------------------
    # STATE UPDATE
    # ------------------
    if state_updates:
        merged = {**(widget.state or {}), **state_updates}
        widget.state = (
            definition.state_schema(**merged).model_dump()
            if definition.state_schema else merged
        )

    widget.save()

    # ------------------
    # RE-EXECUTE SINGLE WIDGET
    # ------------------
    executor = widget.get_executor()

    # IMPORTANT:
    # reuse SAME dashboard filters (no recompute here)
    dashboard_widgets = BaseWidget.objects.filter(dashboard=widget.dashboard)
    filters = build_filters([w for w in dashboard_widgets if w.widget_type == "filter"])

    widget.widget_data = executor.run(filters=filters)
    widget.ui_schema = definition.ui_schema
    widget.template = definition.template

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
