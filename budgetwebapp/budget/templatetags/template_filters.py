from django.template.defaulttags import register
from django import template
from django.utils.safestring import mark_safe
from urllib.parse import urlencode
import calendar
from django.urls import reverse

from core.logger import logger

# Custom template filter to get data from a dictionary using key in template

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def getlist(qdict, key):
    return qdict.getlist(key)


@register.filter
def month_name(month_number):
    return calendar.month_name[month_number]


@register.filter
def to_range(start, end):
    return range(start, end + 1)


@register.filter
def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


@register.filter
def abs_val(value):
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''


@register.simple_tag
def is_checked(request, param_name, value=None, default=True, prefix=None):
    """
    Determines if a checkbox should be checked.

    Args:
        request: the current request object
        param_name: GET parameter to look for (e.g., "cards_row_transaction_type")
        value: the value to check in the GET list (for checkboxes)
        default: what to return on first load (True = checked, False = unchecked)
        prefix: optional; current row/prefix to check in `submitted` or `dsb_row_filter`

    Returns:
        "checked" if the checkbox should be checked, "" otherwise.

    Logic:
    1. First load (no `submitted` and `prefix` not in `dsb_row_filter`):
       - Return `default`.
    2. If `value` is None:
       - Return checked if the parameter exists in GET.
    3. Otherwise:
       - Return checked if `value` is in the GET list for `param_name`.
    """
    # Determine if this row/prefix has been submitted
    submitted = False
    if prefix:
        submitted = prefix in request.GET.getlist('submitted') or prefix in (request.GET.get('dsb_row_filter') or '')

    # First load: no submission yet
    if not submitted:
        return "checked" if default else ""

    # If value is None, just check if param exists
    if value is None:
        return "checked" if request.GET.get(param_name) else ""

    # For checkboxes: check if value is in GET list
    if value in request.GET.getlist(param_name):
        return "checked"

    return ""

@register.simple_tag
def is_checked_depr(request, param_name, value=None, default=True):
    """
    Determines if a checkbox should be checked.

    - request: the current request object
    - param_name: GET parameter to look for (e.g., "cards_row_transaction_type")
    - value: the value to check in the GET list (for checkboxes)
    - default: what to return on first load (True = checked, False = unchecked)
    """
    # First load: no "submitted" field → return default
    if not request.GET.get("submitted"):
        return "checked" if default else ""

    # If value is None, just check if the param exists in GET
    if value is None:
        return "checked" if request.GET.get(param_name) else ""

    # For checkboxes: check if value is in GET list
    if value in request.GET.getlist(param_name):
        return "checked"

    return ""


@register.simple_tag(takes_context=True)
def htmx_pagelink(context, label, page_number, target='transaction-table-content'):
    # Get the current GET parameters from the request context
    request = context['request']
    get_params = request.GET.copy()

    # Set/override the page parameter
    get_params['page'] = page_number

    # Build query string with updated page number
    query_string = get_params.urlencode()

    url = f"?{query_string}"

    # Return a full <a> tag with HTMX attributes
    html = f'''
    <a class="page-link"
       href="{url}"
       hx-get="{url}"
       hx-target="#{target}"
       hx-push-url="true">{label}</a>
    '''

    return mark_safe(html)


@register.simple_tag
def hx_td_category(transaction):
    url = reverse('budget:transactions_by_category', args=[transaction.category_id])
    content = transaction.category
    return mark_safe(f'''
        <td class="nowrap"
            hx-get="{url}"
            hx-target="#dialog-transactions-by-cat"
            hx-trigger="click"
            style="cursor: pointer;">
            <span class="td-t9ns-text">{content}</span>
        </td>
    ''')
