from typing import List, Tuple, Dict
import zipfile
import os
import pandas as pd
import numpy as np
from datetime import datetime

from django.db import transaction

from investments.models import Position, CashOperation
from investments import constants
from core.logger import logger


def get_xtb_file_paths(extract_dir):
    """
    Returns a dictionary with paths to main, IKE, and IKZE Excel files.
    Example:
    {
        "main": "/path/to/account_50867007_....xlsx",
        "ike": "/path/to/account_ike_....xlsx",
        "ikze": "/path/to/account_ikze_....xlsx"
    }
    """
    file_paths = {"main": '', "ike": '', "ikze": ''}

    for file_name in os.listdir(extract_dir):
        if not file_name.endswith('.xlsx'):
            continue

        file_path = os.path.join(extract_dir, file_name)
        name_lower = file_name.lower()

        if "ikze" in name_lower:
            file_paths["ikze"] = file_path
        elif "ike" in name_lower:
            file_paths["ike"] = file_path
        else:
            file_paths["main"] = file_path

    # Sanity check: ensure at least main file exists
    if file_paths["main"] == '':
        raise FileNotFoundError("No main XTB file found in the folder.")

    return file_paths


def extract_xtb_files(zip_path, extract_dir):
    for file_name in os.listdir(extract_dir):
        if file_name.endswith('.xlsx'):
            file_path = os.path.join(extract_dir, file_name)
            os.remove(file_path)
            logger.debug(f"Deleted existing XTB file: {file_name}")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        logger.debug(f"Extracted new files from {zip_path}")


def get_open_position_sheet_name(extract_dir):
    main_file = None
    for file_name in os.listdir(extract_dir):
        if file_name.endswith('.xlsx') and 'ike' not in file_name.lower() and 'ikze' not in file_name.lower():
            main_file = file_name
            break

    if main_file is None:
        raise FileNotFoundError("No main Excel file found in the folder.")

    sheet_date = datetime.strptime(main_file[-15:-5], '%Y-%m-%d').strftime('%d%m%Y')
    open_sheet_name = constants.OPEN_SHEET_TEMPLATE.format(sheet_date)

    return open_sheet_name


def parse_data():
    zip_path = '../artifacts/xtb_files/account_50867007_pl_xlsx_2005-12-31_2025-10-21.zip'
    extract_dir = '../artifacts/xtb_files'

    extract_xtb_files(zip_path, extract_dir)
    open_sheet_name = get_open_position_sheet_name(extract_dir)
    xtb_file_paths = get_xtb_file_paths(extract_dir)

    get_data(
        account_files=xtb_file_paths,
        open_sheet_name=open_sheet_name,
        columns_open=constants.COLUMNS_OPEN,
        closed_sheet_name=constants.CLOSED_SHEET_NAME,
        columns_closed=constants.COLUMNS_CLOSED,
        cash_sheet_name=constants.CASH_SHEET_NAME,
        columns_cash=constants.COLUMNS_CASH,
        totals_cols_closed=constants.TOTALS_COLS_CLOSED,
        totals_cols_open=constants.TOTALS_COLS_OPEN,
        totals_cols_cash=constants.TOTALS_COLS_CASH,
        output_dir=extract_dir,
    )

    # Load into DataFrames
    df_open = pd.read_csv(f"{extract_dir}/open_positions.csv")
    df_closed = pd.read_csv(f"{extract_dir}/closed_positions.csv")
    df_cash = pd.read_csv(f"{extract_dir}/cash_operations.csv")

    # todo: create a button for importing refreshed data
    import_xtb_data(df_open, df_closed, df_cash)


def import_xtb_data(df_open_positions, df_closed_positions, df_cash_operations):
    """Import XTB dataframes into Django models."""
    # Combine open and closed positions
    df_open_positions["position_type"] = "open"
    df_closed_positions["position_type"] = "closed"
    df_positions = pd.concat([df_open_positions, df_closed_positions], ignore_index=True)

    # Replace inf/-inf with NaN (which Django will translate to NULL)
    df_positions["Gross P/L Perc"] = df_positions["Gross P/L Perc"].replace([np.inf, -np.inf], np.nan)
    # Symbol is object/string, so np.nan becomes the string "nan", replacing with None to nullify in the database
    df_cash_operations['Symbol'] = df_cash_operations['Symbol'].replace({np.nan: None})

    # Prepare Position objects for bulk_create
    position_objs = [
        Position(
            symbol=row["Symbol"],
            status=row["position_type"],
            account_type=row["account_type"],
            open_time=row["Open time"],
            close_price=row["Close price"] if "Close price" in row else None,
            open_price=row["Open price"] if "Open price" in row else None,
            market_price=row["Market price"] if "Market price" in row else None,
            volume=row["Volume"] if "Volume" in row else 0.0,
            purchase_value=row["Purchase value"] if "Purchase value" in row else 0.0,
            gross_pl=row["Gross P/L"] if "Gross P/L" in row else 0.0,
            gross_pl_perc=row["Gross P/L Perc"] if "Gross P/L Perc" in row else None,
            swap=row["Swap"] if "Swap" in row else 0.0,
            direction=row["Type"] if "Type" in row else None,
            position_id=row["Position"] if "Position" in row else None,
            instrument_type=determine_instrument_type(row["Symbol"]),
        )
        for _, row in df_positions.iterrows()
    ]

    # Prepare CashOperation objects
    cash_objs = [
        CashOperation(
            xtb_id=str(row["ID"]),
            time=row["Time"],
            symbol=row["Symbol"] if "Symbol" in row else None,
            type=row["Type"],
            amount=row["Amount"],
            account_type=row["account_type"],
        )
        for _, row in df_cash_operations.iterrows()
    ]

    # Bulk create within a transaction
    with transaction.atomic():
        Position.objects.all().delete()
        CashOperation.objects.all().delete()

        Position.objects.bulk_create(position_objs, ignore_conflicts=True)
        CashOperation.objects.bulk_create(cash_objs, ignore_conflicts=True)

    print(f"Imported {len(position_objs)} positions and {len(cash_objs)} cash operations")


def get_data(
        account_files: Dict[str, str],
        open_sheet_name: str,
        columns_open: List[str],
        closed_sheet_name: str,
        columns_closed: List[str],
        cash_sheet_name: str,
        columns_cash: List[str],
        totals_cols_closed: List[str],
        totals_cols_open: List[str],
        totals_cols_cash: List[str],
        output_dir: str,
):
    """
    Reads, aggregates, and saves XTB account data for multiple account types.
    account_files: dict like {"main": "/path/to/main.xlsx", "ike": "...", "ikze": "..."}
    """

    def read_all_accounts(sheet_name, columns, totals_cols, time_col, skiprows):
        return [
            read_sheet_data(
                file_path=path,
                sheet_name=sheet_name,
                columns=columns,
                totals_cols=totals_cols,
                time_col=time_col,
                account_type=acc_type,
                skiprows=skiprows,
            )
            for acc_type, path in account_files.items() if path  # skip empty paths if any
        ]

    # --- Open positions ---
    open_data = read_all_accounts(open_sheet_name, columns_open, totals_cols_open, "Open time", 10)
    df_open_positions_joint = aggregate_positions(pd.concat([df for df, _ in open_data]))

    # --- Closed positions ---
    closed_data = read_all_accounts(closed_sheet_name, columns_closed, totals_cols_closed, "Open time", 12)
    df_closed_positions_joint = aggregate_positions(pd.concat([df for df, _ in closed_data]))

    # --- Cash operations ---
    cash_data = read_all_accounts(cash_sheet_name, columns_cash, totals_cols_cash, "Time", 10)
    df_cash_operations_joint = pd.concat([df for df, _ in cash_data])

    # --- Save to CSV ---
    open_path = f"{output_dir}/open_positions.csv"
    closed_path = f"{output_dir}/closed_positions.csv"
    cash_path = f"{output_dir}/cash_operations.csv"
    # logger.critical(df_open_positions_joint)
    df_open_positions_joint.to_csv(open_path, index=False)
    df_closed_positions_joint.to_csv(closed_path, index=False)
    df_cash_operations_joint.to_csv(cash_path, index=False)

    print(f"Data saved to CSV files in {output_dir}")

    # Return nothing (explicitly) — just log and save
    return None


def read_sheet_data(
        file_path: str,
        sheet_name: str,
        columns: List[str],
        totals_cols: List[str],
        time_col: str,
        account_type: str,
        skiprows: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Read Excel sheet, parse dates, sort, and add account type."""
    df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skiprows)
    totals = df.iloc[-1:][totals_cols].reset_index(drop=True)

    df = df.iloc[:-1][columns]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)
    df["account_type"] = account_type

    return df, totals


def aggregate_positions(df: pd.DataFrame, time_threshold_sec: int = 2) -> pd.DataFrame:
    """Aggregate positions by Symbol and time difference."""
    # reset_index here is essential. Input df is vertically concatenated, which results in duplicated indices
    # Without resetting the index, aggregation of open_price fetches incorrect volume using .loc()
    df = df.sort_values(["Symbol", "Open time"]).reset_index(drop=True)
    df["time_diff"] = df.groupby("Symbol")["Open time"].diff().dt.total_seconds().fillna(9999)
    df["group_id"] = (df["time_diff"] > time_threshold_sec).cumsum()

    aggregation_dict = {
        "Position": "first",
        "Open time": "first",
        "Type": "first",
        "Volume": "sum",
        "Purchase value": "sum",
        "Gross P/L": "sum",
        "Open price": lambda x: (x * df.loc[x.index, "Volume"]).sum() / df.loc[x.index, "Volume"].sum(),
        "Market price": "last",
        "Close price": "last",
        "Swap": "sum",
        "account_type": "first",
    }

    existing_agg = {k: v for k, v in aggregation_dict.items() if k in df.columns}

    aggregated = (
        df.groupby(["Symbol", "group_id"])
        .agg(existing_agg)
        .reset_index()
        .sort_values("Open time")
    )

    if "Gross P/L" in aggregated.columns and "Purchase value" in aggregated.columns:
        aggregated["Gross P/L Perc"] = aggregated["Gross P/L"] / aggregated["Purchase value"]

    return aggregated


def determine_instrument_type(symbol: str) -> str:
    if "." in symbol:
        if symbol.upper().startswith("IG"):
            return "ETC"
        else:
            return "ETF"
    return "CFD"
