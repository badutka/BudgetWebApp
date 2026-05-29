from django.contrib import admin

from budgetwebapp.workbench.models import Notebook, Run, Artifact


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in Notebook._meta.get_fields()
        if field.name != 'run'
    ]

@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in Run._meta.get_fields()
        if field.name not in ['artifact', 'notebook']
    ]

@admin.register(Artifact)
class ArtifactAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in Artifact._meta.get_fields()
        if field.name not in ['run', 'dataset']
    ]