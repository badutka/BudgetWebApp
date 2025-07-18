from collections import defaultdict


def get_summary_detailed(parent_categories, monthly_parent_category_summaries, monthly_category_summaries,
                         summary_type):
    summary = {}
    summary_types = {"income": ['INNER', 'INCOMING'], "expense": ['INNER', 'OUTGOING']}

    for pc in parent_categories:
        parent_name = pc['name']

        # Initialize data structures
        totals = [0.0] * 12
        categories = defaultdict(lambda: [0.0] * 12)

        # Filter relevant data
        parent_category_summaries = [x for x in monthly_parent_category_summaries if
                                     x['parent_category_name'] == parent_name]
        category_summaries = [x for x in monthly_category_summaries if x['parent_category_name'] == parent_name]

        # Fill totals (parent-level)
        for entry in parent_category_summaries:
            month = entry['month'] - 1  # convert 1-indexed to 0-indexed
            totals[month] = float(entry['amount'])

        # Append 13th value as sum
        totals.append(round(sum(totals), 2))

        # Fill category breakdowns (child-level)
        for entry in category_summaries:
            if entry['transaction_type'] in summary_types[summary_type]:
                category = entry['category_name']
                month = entry['month'] - 1
                categories[category][month] = float(entry['amount'])

        # Add 13th value to each category
        for cat, vals in categories.items():
            vals.append(round(sum(vals), 2))

        summary[parent_name] = {
            "totals": totals,
            "categories": dict(categories)
        }

    return summary


def get_filtered_parent_categories(request, parent_categories):
    parent_category_ids = list(map(int, request.GET.getlist('parent_category')))
    return [
        p for p in parent_categories
        if not parent_category_ids or p['id'] in parent_category_ids
    ]
