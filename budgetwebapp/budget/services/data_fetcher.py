from django.http import HttpRequest
from core import utils

def fetch_categories_and_summaries(request: HttpRequest) -> tuple[list, list, list]:
    """
    Fetch monthly summaries, parent categories, and categories from the API.

    Args:
        request (HttpRequest): Django HttpRequest object.

    Returns:
        tuple:
            list: Monthly summary data.
            list: Parent category objects.
            list: Category objects.
    """
    # params = utils.flatten_querydict(query_data)
    params = list(tuple())
    monthly_summaries = utils.fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, [('year', '2025')])
    parent_categories = utils.fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)
    categories = utils.fetch_api_and_get_response(request, 'budget:categories', 200, params)
    return monthly_summaries, parent_categories, categories