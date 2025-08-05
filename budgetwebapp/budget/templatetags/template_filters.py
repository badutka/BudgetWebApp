from django.template.defaulttags import register
from django import template
from django.utils.safestring import mark_safe
from urllib.parse import urlencode
import calendar
from django.urls import reverse


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
