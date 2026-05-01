from typing import List, Tuple, Dict
import zipfile
import os
import re
import pandas as pd
import numpy as np
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from budgetwebapp.investments.models import Position, CashOperation, TransferOperation
from budgetwebapp.investments import constants
from core.logger import logger


def parse_data(extract_dir):
    extract_xtb_files(extract_dir)
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
    df_transfers = pd.read_csv(f"{extract_dir}/transfer_operations.csv")

    # df_cash = convert_ewallet_to_regular_transfer(df_cash)
    # logger.warn(df_cash.sort_values(by='Time')[-20:])
    # todo: create a button for importing refreshed data
    import_xtb_data(df_open, df_closed, df_cash, df_transfers)


def extract_account_number(filename):
    match = re.search(r"account_(.*?)_pl_xlsx_", filename.lower())
    return match.group(1) if match else None


def get_xtb_file_paths(extract_dir):
    """
    Returns a dictionary with paths to main, IKE, and IKZE Excel files.
    Example:
    {
        "main": "/path/to/account_....xlsx",
        "ike": "/path/to/account_ike_....xlsx",
        "ikze": "/path/to/account_ikze_....xlsx"
    }
    """

    # discover all account tokens
    account_tokens = []

    for file_name in os.listdir(extract_dir):
        if file_name.endswith(".xlsx"):
            token = extract_account_number(file_name)
            if token:
                account_tokens.append(token)

    # sort tokens (account types are sorted via account number - ascending)
    account_tokens = sorted(account_tokens)

    # map tokens → types based on ordering
    file_paths = {}

    for i, token in enumerate(account_tokens):
        if i < len(constants.ACCOUNT_TYPE_ORDER):
            account_type = constants.ACCOUNT_TYPE_ORDER[i]
        else:
            account_type = f"extra_{i}"

        # find the matching file again
        for file_name in os.listdir(extract_dir):
            if token in file_name.lower():
                file_paths[account_type] = os.path.join(extract_dir, file_name)
                break

    # Sanity check: ensure at least main file exists
    if file_paths["main"] == '':
        raise FileNotFoundError("No main XTB file found in the folder.")

    return file_paths


def extract_xtb_files(extract_dir):
    # Find the ZIP file in the directory
    zip_files = [f for f in os.listdir(extract_dir) if f.lower().endswith(".zip")]

    if not zip_files:
        raise FileNotFoundError("No ZIP file found in extract_dir")

    if len(zip_files) > 1:
        raise RuntimeError(f"Multiple ZIP files found: {zip_files}. Expected exactly one.")

    zip_path = os.path.join(extract_dir, zip_files[0])
    logger.debug(f"Using ZIP file: {zip_path}")

    # Get the list of files in the ZIP
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_xlsx_files = [os.path.basename(f) for f in zip_ref.namelist() if f.endswith('.xlsx')]

    # Delete only these files from the extract_dir
    for file_name in os.listdir(extract_dir):
        if file_name in zip_xlsx_files:
            file_path = os.path.join(extract_dir, file_name)
            os.remove(file_path)
            logger.debug(f"Deleted existing XTB ZIP file: {file_name}")

    # Extract ZIP
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


def convert_ewallet_to_regular_transfer(df_cash):
    df = df_cash.copy()
    df = df.sort_values(by='Time').reset_index(drop=True)

    # Identify eWallet withdrawals and deposits
    mask_w = (df["Type"] == "withdrawal") & df["Comment"].str.contains("eWallet OT", na=False)
    mask_d = (df["Type"] == "deposit") & df["Comment"].str.contains("eWallet OT", na=False)

    withdrawals = df[mask_w].sort_values("Time")
    deposits = df[mask_d].sort_values("Time")

    if len(withdrawals) != len(deposits):
        raise ValueError("Unmatched eWallet deposits/withdrawals")

    for (w_idx, w_row), (d_idx, d_row) in zip(withdrawals.iterrows(), deposits.iterrows()):
        w_amt = abs(w_row["Amount"])
        d_amt = d_row["Amount"]
        rate = round(w_amt / d_amt, 6)

        # Update withdrawal → transfer
        df.at[w_idx, "Type"] = "transfer"
        df.at[w_idx, "Comment"] = (
            f"Currency conversion, PLN to USD from TA: {w_row.account_type} "
            f"to: {d_row.account_type}, Exchange rate:{rate}"
        )

        # Update deposit → transfer
        df.at[d_idx, "Type"] = "transfer"
        df.at[d_idx, "Comment"] = (
            f"Currency conversion, PLN to USD from TA: {w_row.account_type} "
            f"to: {d_row.account_type}, Exchange rate:{rate}"
        )

    skip_ids = np.concatenate((deposits.ID.values, withdrawals.ID.values))
    df = invert_transfer_exchange_rates(df, skip_ids)

    return df


def invert_transfer_exchange_rates(df_cash, skip_ids):
    """
    For all transfer rows (except those in skip_ids),
    replace Exchange rate:x with Exchange rate:1/x .
    """
    df = df_cash.copy()

    # All transfer rows except skipped
    mask = (df["Type"] == "transfer") & (~df["ID"].isin(skip_ids))

    # Regex to find "Exchange rate:0.123456"
    rate_pattern = re.compile(r"Exchange rate:([0-9]*\.?[0-9]+)")

    for idx, row in df[mask].iterrows():
        comment = row["Comment"]
        match = rate_pattern.search(comment)
        if not match:
            continue  # no exchange rate present → skip

        old_rate = float(match.group(1))
        new_rate = round(1 / old_rate, 6)  # more precision here; adjust if needed

        # Replace only the first occurrence
        new_comment = rate_pattern.sub(f"Exchange rate:{new_rate}", comment, count=1)

        df.at[idx, "Comment"] = new_comment

    return df


def import_xtb_data(df_open_positions, df_closed_positions, df_cash_operations, df_transfers):
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
            open_time=timezone.make_aware(pd.to_datetime(row["Open time"])),
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
            time=timezone.make_aware(pd.to_datetime(row["Time"])),
            symbol=row["Symbol"] if "Symbol" in row else None,
            type=row["Type"],
            amount=row["Amount"],
            account_type=row["account_type"],
        )
        for _, row in df_cash_operations.iterrows()
    ]

    transfer_objs = [
        TransferOperation(
            timestamp_out=timezone.make_aware(pd.to_datetime(row["timestamp_out"])),
            timestamp_in=timezone.make_aware(pd.to_datetime(row["timestamp_in"])),
            amount_out=row["amount_out"],
            currency_out=row["currency_out"],
            account_out=row["account_out"],
            xtb_id_out=row["xtb_id_out"],
            amount_in=row["amount_in"],
            currency_in=row["currency_in"],
            account_in=row["account_in"],
            xtb_id_in=row["xtb_id_in"],
            exchange_rate=row["exchange_rate"]
        )
        for _, row in df_transfers.iterrows()
    ]

    # Bulk create within a transaction
    with transaction.atomic():
        Position.objects.all().delete()
        CashOperation.objects.all().delete()
        TransferOperation.objects.all().delete()

        Position.objects.bulk_create(position_objs, ignore_conflicts=True)
        CashOperation.objects.bulk_create(cash_objs, ignore_conflicts=True)
        TransferOperation.objects.bulk_create(transfer_objs, ignore_conflicts=True)

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
    df_cash_operations_joint = convert_ewallet_to_regular_transfer(df_cash_operations_joint)
    df_transfers = get_transfers(df_cash_operations_joint)

    # --- Save to CSV ---
    open_path = f"{output_dir}/open_positions.csv"
    closed_path = f"{output_dir}/closed_positions.csv"
    cash_path = f"{output_dir}/cash_operations.csv"
    transfer_path = f"{output_dir}/transfer_operations.csv"

    df_open_positions_joint.to_csv(open_path, index=False)
    df_closed_positions_joint.to_csv(closed_path, index=False)
    df_cash_operations_joint.to_csv(cash_path, index=False)
    df_transfers.to_csv(transfer_path, index=False)

    logger.debug(f"Data saved to CSV files in {output_dir}")

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


def get_transfers(df_cash):
    pairs = []

    # Filter only transfers
    df_transfers = df_cash.loc[df_cash.Type == 'transfer'].reset_index(drop=True)

    # Iterate over every two rows
    for i in range(0, len(df_transfers), 2):
        r1 = df_transfers.iloc[i]
        r2 = df_transfers.iloc[i+1]

        # Determine which row is PLN out and which is FX in
        out_row = r1 if r1.Amount < 0 else r2
        in_row  = r1 if r1.Amount > 0 else r2

        # Extract exchange rate from the comment of the "out" row
        rate_match = re.search(r'Exchange rate:([\d.]+)', out_row.Comment)
        exchange_rate = float(rate_match.group(1)) if rate_match else None

        # Map account type to currency
        currency_out = constants.ACCOUNT_CURRENCY_MAP.get(out_row.account_type.lower(), out_row.account_type.upper())
        currency_in = constants.ACCOUNT_CURRENCY_MAP.get(in_row.account_type.lower(), in_row.account_type.upper())

        pairs.append({
            "timestamp_out": out_row.Time,
            "timestamp_in": in_row.Time,
            "amount_out": abs(out_row.Amount),
            "currency_out": currency_out,
            "account_out": out_row.account_type,
            "xtb_id_out": out_row.ID,
            "amount_in": in_row.Amount,
            "currency_in": currency_in,
            "account_in": in_row.account_type,
            "xtb_id_in": in_row.ID,
            "exchange_rate": exchange_rate
        })

    # Convert list of dicts to DataFrame
    df_pairs = pd.DataFrame(pairs)

    return df_pairs
