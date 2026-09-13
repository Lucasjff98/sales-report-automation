"""
Data module: load raw orders from CSV or Excel files.

This module is the only layer allowed to perform file I/O. It reads a
raw orders file and returns a pandas DataFrame with standardized column
names ("customer", "amount", "order_date"), ready to be passed into
processing.summarize.summarize_orders.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

STANDARD_COLUMNS = ("customer", "amount", "order_date")

SUPPORTED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
SUPPORTED_CSV_EXTENSIONS = {".csv"}


def load_orders(
    file_path: str | Path,
    column_mapping: dict[str, str] | None = None,
    sheet_name: str | int = 0,
) -> pd.DataFrame:
    """
    Load raw orders from a CSV or Excel file into a standardized DataFrame.

    Parameters
    ----------
    file_path : str | Path
        Path to the source file. Format is detected from the extension
        (.csv, .xlsx, .xls).
    column_mapping : dict[str, str], optional
        Maps source column names to the standard names expected by the
        rest of the pipeline. Keys are the SOURCE column names as they
        appear in the file; values must be one of "customer", "amount",
        "order_date". Example:
            {"Cliente": "customer", "Valor Total": "amount", "Data": "order_date"}
        If omitted, the file's columns are assumed to already be named
        "customer", "amount", "order_date".
    sheet_name : str | int, default 0
        Sheet to read when the source is an Excel file. Ignored for CSV.

    Returns
    -------
    pd.DataFrame
        DataFrame containing at least the columns "customer", "amount",
        and "order_date" (extra columns from the source file, if any,
        are preserved after these).

    Raises
    ------
    FileNotFoundError
        If file_path does not exist.
    ValueError
        If the file extension is not supported, or if the resulting
        DataFrame (after applying column_mapping) is missing one of the
        required standard columns.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Orders file not found: {path}")

    extension = path.suffix.lower()

    if extension in SUPPORTED_CSV_EXTENSIONS:
        df = pd.read_csv(path)
    elif extension in SUPPORTED_EXCEL_EXTENSIONS:
        df = pd.read_excel(path, sheet_name=sheet_name)
    else:
        raise ValueError(
            f"Unsupported file extension '{extension}'. "
            f"Expected one of: {SUPPORTED_CSV_EXTENSIONS | SUPPORTED_EXCEL_EXTENSIONS}"
        )

    if column_mapping:
        df = df.rename(columns=column_mapping)

    missing = [col for col in STANDARD_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required column(s) after mapping: {missing}. "
            f"Available columns: {list(df.columns)}. "
            "Check your column_mapping argument."
        )

    return df