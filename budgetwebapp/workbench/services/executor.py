import sqlite3
import pandas as pd

from budgetwebapp.workbench.models import Run, Artifact 


def start_run(run_id: int):
    run = Run.objects.get(id=run_id)
    run.status = Run.Status.RUNNING
    run.save()


def load_notebook(path: str):
    with open(path, "r") as f:
        code = f.read()
    return code


def execute_code(code: str, context: dict):
    local_vars = {}

    exec(code, context, local_vars)

    return local_vars


def write_to_warehouse(df, table_name):
    conn = sqlite3.connect("warehouse.sqlite3")

    df.to_sql(
        table_name,
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()


def create_artifact(run, table_name):
    return Artifact.objects.create(
        run=run,
        type="table",
        table_name=table_name
    )

def run_notebook(run_id: int):
    run = Run.objects.get(id=run_id)

    try:
        code = load_notebook(run.notebook.file_path)

        result = execute_code(code, {"pd": pd})

        df = result.get("output_df")

        table_name = f"run_{run.id}_output"

        write_to_warehouse(df, table_name)

        artifact = create_artifact(run, table_name)

        run.status = Run.Status.SUCCESS
        run.save()

        return artifact

    except Exception as e:
        run.status = Run.Status.FAILED
        run.error_message = str(e)
        run.save()
        raise