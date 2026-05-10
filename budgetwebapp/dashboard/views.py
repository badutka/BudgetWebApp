from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.http import HttpResponse
from pydantic import ValidationError
import json

from .models import Dashboard, BaseWidget
from budgetwebapp.dashboard.core.services import build_filters, WidgetSidebarService
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
    data_widgets = [w for w in widgets if w.widget_type != "filter"]

    filters = build_filters(filter_widgets)

    # service = DashboardService(dashboard)
    # widgets = service.get_widgets_data(request_params=request.GET)

    # if account_type:
    #     widgets = widgets.filter(config__account_type=account_type)

    widget_list = []

    for widget in data_widgets:
        data = WidgetService(widget).get_data(filters)
        widget.widget_data = data
        # widget_list.append(widget)
    widget_list = data_widgets + filter_widgets

    context = {
        "widgets": widget_list,
        "dashboard": dashboard,
        "enable_account_details_visit": dashboard.slug == "portfolio-overview",
    }

    return render(request, "dashboard/dashboard.html", context)


def dashboard_sidebar_content(request, widget_id):
    widget = BaseWidget.objects.get(id=widget_id)
    service = WidgetSidebarService()

    context = service.build_context(widget)

    logger.info(context)
    template_map = {
        "filter:select": "dashboard/sidebar/select_filter.html",
    }
    key = f"{widget.widget_type}:{widget.subtype}"
    template = template_map.get(key)

    return render(request, template, context)


def update_config(request, widget_id):
    widget = get_object_or_404(BaseWidget, id=widget_id)

    current_config = widget.config or {}

    updates = {}

    for key, value in request.POST.items():
        if key == "csrfmiddlewaretoken":
            continue

        updates[key] = value

    # merge existing + incoming
    merged = {
        **current_config,
        **updates,
    }

    try:
        validated = SelectFilterConfig(**merged)

    except ValidationError as e:
        return JsonResponse({
            "ok": False,
            "errors": e.errors(),
        }, status=400)

    widget.config = validated.model_dump()
    widget.save()

    return JsonResponse({
        "ok": True,
        "config": widget.config,
    })

def update_state(request, widget_id):
    widget = get_object_or_404(BaseWidget, id=widget_id)

    handler_cls = get_widget_handler(
        widget.widget_type,
        widget.subtype,
    )

    state_schema = handler_cls.STATE_SCHEMA

    current_state = widget.state or {}

    updates = {}

    for key, value in request.POST.items():
        if key == "csrfmiddlewaretoken":
            continue

        updates[key] = value

    merged = {
        **current_state,
        **updates,
    }

    try:
        validated = state_schema(**merged)

    except ValidationError as e:
        return JsonResponse({
            "ok": False,
            "errors": e.errors(),
        }, status=400)

    widget.state = validated.model_dump()
    widget.save(update_fields=["state"])

    return JsonResponse({
        "ok": True,
        "state": widget.state,
    })

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
