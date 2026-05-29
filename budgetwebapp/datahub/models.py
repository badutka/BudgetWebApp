from django.db import models


class Dataset(models.Model):
    """
    Logical data product
    """

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    # owner = models.CharField(max_length=255)
    # schema_json = models.JSONField(null=True, blank=True)
    # tags = models.JSONField(default=list, blank=True)

    # pointer to current version of data, eventually can migrate to ID
    # current_artifact_id = models.IntegerField(null=True, blank=True)
    current_artifact = models.ForeignKey(
        "workbench.Artifact",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    # artifact_uri = "artifact://run/123/output/1"

    # optional direct warehouse pointer (useful later)
    warehouse_table = models.CharField(max_length=255, blank=True)
    # warehouse_uri = "sqlite:///warehouse.sqlite3#table=run_123_output"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# class DatasetVersion(models.Model):
#     dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

#     version = models.IntegerField()

#     artifact_id = models.IntegerField()

#     created_at = models.DateTimeField(auto_now_add=True)

#     comment = models.TextField(blank=True)