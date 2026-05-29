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

    r = requests.get("http://127.0.0.1:2718")
    print(r)
    response = HttpResponse(
        r.content,
        status=r.status_code,
    )

    response["X-Frame-Options"] = "SAMEORIGIN"
    # response.pop("Content-Security-Policy", None)

    return render(request, "workbench/index.html")

