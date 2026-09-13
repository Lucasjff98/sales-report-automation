"""
Processing module: aggregate orders by customer.

Expected columns in the input DataFrame (adjust the column names below
if your source data uses different labels):
    - "customer"      : customer identifier or name (str)
    - "amount"        : monetary value of the order (float/int)
    - "order_date"    : order date (parseable str or datetime)
"""

from __future__ import annotations

import pandas as pd


def summarize_orders(
    orders: pd.DataFrame,
    customer_col: str = "customer",
    amount_col: str = "amount",
    date_col: str = "order_date",
) -> pd.DataFrame:
    """
    Aggregate orders by customer, computing sales metrics.

    Pure function: no I/O, does not mutate the input DataFrame, and
    always returns the same output for the same input.

    Parameters
    ----------
    orders : pd.DataFrame
        DataFrame with one order per row.
    customer_col, amount_col, date_col : str
        Names of the relevant columns, if they differ from the defaults.

    Returns
    -------
    pd.DataFrame
        One row per customer, with columns:
        - customer
        - total_amount      (sum of order amounts)
        - order_count       (number of orders)
        - average_order     (total_amount / order_count)
        - last_order_date   (most recent order date)

    Raises
    ------
    KeyError
        If any of the expected columns is missing from the DataFrame.
    """
    required_columns = {customer_col, amount_col, date_col}
    missing = required_columns - set(orders.columns)
    if missing:
        raise KeyError(f"Missing columns in DataFrame: {missing}")

    if orders.empty:
        return pd.DataFrame(
            columns=[
                "customer",
                "total_amount",
                "order_count",
                "average_order",
                "last_order_date",
            ]
        )

    # Work on a copy so the original DataFrame is never mutated (purity).
    df = orders.copy()

    # Normalize the customer name (strip extra whitespace) to avoid
    # duplicate groups caused by leading/trailing spaces.
    df[customer_col] = df[customer_col].astype(str).str.strip()

    # Ensure the date column is proper datetime so we can correctly
    # find the most recent order per customer.
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    aggregated = (
        df.groupby(customer_col)
        .agg(
            total_amount=(amount_col, "sum"),
            order_count=(amount_col, "count"),
            last_order_date=(date_col, "max"),
        )
        .reset_index()
        .rename(columns={customer_col: "customer"})
    )

    aggregated["average_order"] = (
        aggregated["total_amount"] / aggregated["order_count"]
    )

    # Reorder columns into the final combined layout.
    aggregated = aggregated[
        ["customer", "total_amount", "order_count", "average_order", "last_order_date"]
    ]

    return aggregated.sort_values("total_amount", ascending=False).reset_index(
        drop=True
    )