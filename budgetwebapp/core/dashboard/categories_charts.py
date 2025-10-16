from core.dashboard import data_pipeline
from core.logger import logger


def get_categories_data(date_from=None, date_to=None, apply_date_filters=False,
                        apply_filters=False, transaction_types=None,
                        parent_categories=None, categories=None):
    pipeline = data_pipeline.CategoriesPipeline()
    df = pipeline.load("categories_data")
    logger.critical(apply_date_filters)
    df = pipeline.apply_filters(
        df,
        date_from=date_from, date_to=date_to,
        apply_date=apply_date_filters, apply_data=apply_filters,
        transaction_types=transaction_types,
        parent_categories=parent_categories,
        categories=categories
    )

    df_parent = df.groupby(['parent_category', 'transaction_type']).agg(
        num_transactions=('num_transactions', 'sum'),
        transactions_amount=('amount', 'sum')
    ).reset_index().sort_values(by='num_transactions', ascending=False)

    df_cat = df.groupby(['category']).agg(
        num_transactions=('num_transactions', 'sum'),
        transactions_amount=('amount', 'sum')
    ).reset_index().sort_values(by='num_transactions', ascending=False)

    sunburst_data = [{"id": "0.0", "parent": "", "name": "Total"}]
    for i, parent in enumerate(df["parent_category"].unique(), start=1):
        sunburst_data.append({"id": f"1.{i}", "parent": "0.0", "name": parent})
        subset = df[df["parent_category"] == parent]
        for j, row in enumerate(subset.itertuples(), start=1):
            sunburst_data.append({
                "id": f"2.{i}.{j}",
                "parent": f"1.{i}",
                "name": row.category,
                "value": row.num_transactions
            })

    return (
        df_parent.to_dict(orient="list"),
        df_cat.to_dict(orient="list"),
        sunburst_data
    )
