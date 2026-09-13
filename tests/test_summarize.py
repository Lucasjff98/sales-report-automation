"""
Unit tests for processing.summarize.summarize_orders.

Run with:
    pytest tests/test_summarize.py -v
"""

import pandas as pd
import pytest

from processing.summarize import summarize_orders


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_orders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer": ["Ana", "Bruno", "Ana", "Bruno", "Carla"],
            "amount": [100.0, 200.0, 50.0, 300.0, 75.0],
            "order_date": [
                "2026-01-01",
                "2026-01-05",
                "2026-02-10",
                "2026-03-01",
                "2026-01-20",
            ],
        }
    )


# ---------------------------------------------------------------------------
# Normal cases
# ---------------------------------------------------------------------------

def test_aggregates_total_amount_per_customer(basic_orders):
    result = summarize_orders(basic_orders)
    ana = result[result["customer"] == "Ana"].iloc[0]
    bruno = result[result["customer"] == "Bruno"].iloc[0]

    assert ana["total_amount"] == 150.0
    assert bruno["total_amount"] == 500.0


def test_counts_number_of_orders(basic_orders):
    result = summarize_orders(basic_orders)
    ana = result[result["customer"] == "Ana"].iloc[0]
    carla = result[result["customer"] == "Carla"].iloc[0]

    assert ana["order_count"] == 2
    assert carla["order_count"] == 1


def test_computes_average_order_value(basic_orders):
    result = summarize_orders(basic_orders)
    bruno = result[result["customer"] == "Bruno"].iloc[0]

    assert bruno["average_order"] == 250.0  # 500 / 2


def test_finds_last_order_date(basic_orders):
    result = summarize_orders(basic_orders)
    ana = result[result["customer"] == "Ana"].iloc[0]

    assert ana["last_order_date"] == pd.Timestamp("2026-02-10")


def test_result_sorted_by_total_amount_desc(basic_orders):
    result = summarize_orders(basic_orders)
    values = result["total_amount"].tolist()

    assert values == sorted(values, reverse=True)


def test_one_row_per_unique_customer(basic_orders):
    result = summarize_orders(basic_orders)

    assert result["customer"].is_unique
    assert len(result) == 3  # Ana, Bruno, Carla


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_dataframe_returns_correct_columns():
    empty = pd.DataFrame(columns=["customer", "amount", "order_date"])
    result = summarize_orders(empty)

    assert result.empty
    assert list(result.columns) == [
        "customer",
        "total_amount",
        "order_count",
        "average_order",
        "last_order_date",
    ]


def test_missing_column_raises_key_error():
    incomplete_df = pd.DataFrame({"customer": ["Ana"], "amount": [100.0]})

    with pytest.raises(KeyError):
        summarize_orders(incomplete_df)


def test_strips_whitespace_from_customer_name():
    df = pd.DataFrame(
        {
            "customer": ["Ana", " Ana", "Ana "],
            "amount": [10.0, 20.0, 30.0],
            "order_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        }
    )
    result = summarize_orders(df)

    # Leading/trailing spaces should be treated as the same customer.
    assert len(result) == 1
    assert result.iloc[0]["total_amount"] == 60.0


def test_case_difference_is_not_unified():
    """
    Documents a design decision: 'Ana' and 'ana' are treated as
    DIFFERENT customers, since unifying by case is a business rule
    that should be decided explicitly, not assumed by the function.
    """
    df = pd.DataFrame(
        {
            "customer": ["Ana", "ana"],
            "amount": [10.0, 20.0],
            "order_date": ["2026-01-01", "2026-01-02"],
        }
    )
    result = summarize_orders(df)

    assert len(result) == 2


def test_negative_amounts_are_summed_normally():
    """Orders with a negative amount (e.g. refunds) reduce the customer's total."""
    df = pd.DataFrame(
        {
            "customer": ["Ana", "Ana"],
            "amount": [100.0, -30.0],
            "order_date": ["2026-01-01", "2026-01-02"],
        }
    )
    result = summarize_orders(df)

    assert result.iloc[0]["total_amount"] == 70.0


def test_null_customer_is_ignored_by_groupby():
    """
    Documents pandas' default behavior: rows with a null customer
    (NaN/None) are excluded from the grouping. Handling orders with
    no identified customer should happen BEFORE calling
    summarize_orders (e.g. in a data-cleaning step).
    """
    df = pd.DataFrame(
        {
            "customer": ["Ana", None],
            "amount": [100.0, 999.0],
            "order_date": ["2026-01-01", "2026-01-02"],
        }
    )
    result = summarize_orders(df)

    assert len(result) == 1
    assert result.iloc[0]["customer"] == "Ana"


def test_invalid_date_becomes_nat_without_crashing():
    """Dates that cannot be parsed become NaT, but the function must not fail."""
    df = pd.DataFrame(
        {
            "customer": ["Ana"],
            "amount": [100.0],
            "order_date": ["invalid-date"],
        }
    )
    result = summarize_orders(df)

    assert pd.isna(result.iloc[0]["last_order_date"])


def test_does_not_mutate_original_dataframe(basic_orders):
    """Ensures the function is pure: it must not alter the input DataFrame."""
    original = basic_orders.copy(deep=True)
    summarize_orders(basic_orders)

    pd.testing.assert_frame_equal(basic_orders, original)


def test_accepts_custom_column_names():
    df = pd.DataFrame(
        {
            "customer_name": ["Ana", "Bruno"],
            "order_total": [100.0, 200.0],
            "date": ["2026-01-01", "2026-01-02"],
        }
    )
    result = summarize_orders(
        df,
        customer_col="customer_name",
        amount_col="order_total",
        date_col="date",
    )

    assert len(result) == 2
    assert set(result["customer"]) == {"Ana", "Bruno"}