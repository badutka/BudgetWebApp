from django.template.defaulttags import register
from django import template
from django.utils.safestring import mark_safe
from urllib.parse import urlencode


# Custom template filter to get data from a dictionary using key in template

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def getlist(qdict, key):
    return qdict.getlist(key)

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