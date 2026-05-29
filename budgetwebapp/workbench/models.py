from django.db import models


class Notebook(models.Model):
    """
    A marimo notebook definition.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # path to .py marimo file
    file_path = models.CharField(max_length=500)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Run(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        SUCCESS = "success"
        FAILED = "failed"

    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # optional debugging
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Run {self.id} ({self.status})"
    

class Artifact(models.Model):
    class Type(models.TextChoices):
        TABLE = "table"
        FILE = "file"
        MODEL = "model"

    run = models.ForeignKey(Run, on_delete=models.CASCADE)

    type = models.CharField(max_length=20, choices=Type.choices)

    # IMPORTANT: pointer to warehouse object
    table_name = models.CharField(max_length=255)

    # optional: schema info for debugging/UX
    schema_json = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def warehouse_sql(self):
        return f"SELECT * FROM {self.table_name}"