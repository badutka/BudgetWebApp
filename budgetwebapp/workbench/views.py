from django.shortcuts import render
import sqlite3
import pandas as pd
from django.conf import settings


from budgetwebapp.workbench.models import Notebook, Run
from budgetwebapp.workbench.services.executor import run_notebook
from budgetwebapp.datahub.services.promotion import promote_to_dataset
from budgetwebapp.datahub.models import Dataset
import requests
from django.http import HttpResponse

from .executor import run_notebook_cell
from core.logger import logger
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

def index(request):
    conn = sqlite3.connect(settings.WAREHOUSE_DB_PATH)

    # nb = Notebook.objects.get_or_create(
    #     name="Demo Notebook",
    #     file_path="notebooks/demo.py",
    #     description="First test notebook"
    # )[0]
    # print(nb)
    # run = Run.objects.create(notebook=nb)
    # run_notebook(run.id)

    # promote_to_dataset(artifact_id=7, name="demo_2")

    dataset = Dataset.objects.get(name="demo_2")
    
    artifact = dataset.current_artifact

    table = artifact.table_name

    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    print(df)
    conn.close()

    return render(request, "workbench/index.html")


# temporary in-memory notebook store (MVP ONLY)
NOTEBOOKS = {
    "default": {
        "session_id": None,
        "cells": []
    }
}


def _get_notebook(nb_id):
    if nb_id not in NOTEBOOKS:
        NOTEBOOKS[nb_id] = {
            "session_id": None,
            "cells": []
        }
    return NOTEBOOKS[nb_id]


# =========================
# ADD CELL
# =========================
@require_POST
def add_cell(request):
    data = json.loads(request.body or "{}")
    nb_id = data.get("notebook_id", "default")

    notebook = _get_notebook(nb_id)

    cell = {
        "id": len(notebook["cells"]),
        "code": "",
        "output": "",
        "error": None,
    }

    notebook["cells"].append(cell)

    return JsonResponse(cell)


# =========================
# DELETE CELL
# =========================
@require_POST
def delete_cell(request):
    data = json.loads(request.body or "{}")
    nb_id = data.get("notebook_id", "default")
    cell_id = data.get("cell_id")

    notebook = _get_notebook(nb_id)

    notebook["cells"] = [
        c for c in notebook["cells"] if c["id"] != cell_id
    ]

    return JsonResponse({"status": "ok"})


# =========================
# RUN CELL
# =========================
@require_POST
def run_cell_view(request):
    data = json.loads(request.body or "{}")

    nb_id = data.get("notebook_id", "default")
    cell_id = data.get("cell_id")
    code = data.get("code", "")

    notebook = _get_notebook(nb_id)

    logger.debug(f"Running cell {cell_id}")

    # initialize kernel session if needed
    if notebook["session_id"] is None:
        notebook["session_id"] = None  # your executor will create it

    result = run_notebook_cell(
        session_id=notebook["session_id"],
        code=code,
        include_vars=False
    )

    notebook["session_id"] = result.get("session_id")

    # update cell output
    for cell in notebook["cells"]:
        if cell["id"] == cell_id:
            cell["output"] = result.get("output", "")
            cell["error"] = result.get("error")

    return JsonResponse({
        "cell_id": cell_id,
        "output": result.get("output", ""),
        "error": result.get("error"),
        "session_id": notebook["session_id"]
    })