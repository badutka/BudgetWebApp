from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.template.loader import render_to_string
from django.http import HttpResponse

from .models import Dashboard, BaseWidget
from budgetwebapp.dashboard.core.services import build_filters
from .core.services import WidgetService
from core.logger import logger


def index(request):
    return render(request, "dashboard/index.html")


def dashboard_view(request, slug):
    dashboard = get_object_or_404(Dashboard, slug=slug)

    widgets = BaseWidget.objects.filter(dashboard=dashboard)
    # account_type = request.GET.get('account_type')

    filters = build_filters(widgets)

    # service = DashboardService(dashboard)
    # widgets = service.get_widgets_data(request_params=request.GET)

    # if account_type:
    #     widgets = widgets.filter(config__account_type=account_type)

    widget_list = []

    for widget in widgets:
        data = WidgetService(widget).get_data(filters)
        widget.widget_data = data
        widget_list.append(widget)

    context = {
        "widgets": widget_list,
        "dashboard": dashboard,
        "enable_account_details_visit": dashboard.slug == "portfolio-overview",
    }

    return render(request, "dashboard/dashboard.html", context)


def dashboard_sidebar_content(request, widget_id):
    widget = BaseWidget.objects.get(id=widget_id)

    template_map = {
        "filter:select": "dashboard/sidebar/select_filter.html",
    }

    key = f"{widget.widget_type}:{widget.subtype}"
    template = template_map.get(key)
    context = {
        "widget": widget
    }
    return render(request, template, context)


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
