from budgetwebapp.datahub.models import Dataset
from budgetwebapp.workbench.models import Artifact


def promote_to_dataset(*, artifact_id: int, name: str, description: str = "") -> Dataset:
    """
    Promote a Workbench Artifact into a Datahub Dataset.
    """

    artifact = Artifact.objects.get(id=artifact_id)

    dataset, created = Dataset.objects.get_or_create(
        name=name,
        defaults={
            "description": description,
            "current_artifact": artifact,
            "warehouse_table": artifact.table_name,
        },
    )

    # If dataset already exists, update it to latest artifact
    if not created:
        dataset.current_artifact = artifact
        dataset.warehouse_table = artifact.table_name
        dataset.description = description or dataset.description
        dataset.save()

    return dataset