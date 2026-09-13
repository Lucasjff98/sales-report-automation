"""
Unit tests for data.loader.load_orders.

Run with:
    pytest tests/test_loader.py -v
"""

from pathlib import Path

import pandas as pd
import pytest

from data.loader import load_orders


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Cliente": ["Ana", "Bruno"],
            "Valor": [100.0, 200.0],
            "Data": ["2026-01-01", "2026-01-02"],
        }
    )


@pytest.fixture
def standard_named_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer": ["Ana", "Bruno"],
            "amount": [100.0, 200.0],
            "order_date": ["2026-01-01", "2026-01-02"],
        }
    )


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def test_loads_csv_with_standard_column_names(tmp_path: Path, standard_named_df):
    csv_path = tmp_path / "orders.csv"
    standard_named_df.to_csv(csv_path, index=False)

    result = load_orders(csv_path)

    assert list(result["customer"]) == ["Ana", "Bruno"]
    assert list(result["amount"]) == [100.0, 200.0]


def test_loads_csv_with_column_mapping(tmp_path: Path, sample_df):
    csv_path = tmp_path / "orders.csv"
    sample_df.to_csv(csv_path, index=False)

    result = load_orders(
        csv_path,
        column_mapping={"Cliente": "customer", "Valor": "amount", "Data": "order_date"},
    )

    assert list(result["customer"]) == ["Ana", "Bruno"]
    assert list(result["amount"]) == [100.0, 200.0]
    assert "order_date" in result.columns


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def test_loads_xlsx_with_standard_column_names(tmp_path: Path, standard_named_df):
    xlsx_path = tmp_path / "orders.xlsx"
    standard_named_df.to_excel(xlsx_path, index=False)

    result = load_orders(xlsx_path)

    assert list(result["customer"]) == ["Ana", "Bruno"]


def test_loads_xlsx_with_column_mapping(tmp_path: Path, sample_df):
    xlsx_path = tmp_path / "orders.xlsx"
    sample_df.to_excel(xlsx_path, index=False)

    result = load_orders(
        xlsx_path,
        column_mapping={"Cliente": "customer", "Valor": "amount", "Data": "order_date"},
    )

    assert list(result["customer"]) == ["Ana", "Bruno"]


def test_loads_specific_excel_sheet(tmp_path: Path, standard_named_df):
    xlsx_path = tmp_path / "orders.xlsx"
    other_df = pd.DataFrame({"customer": ["Wrong"], "amount": [0], "order_date": ["2026-01-01"]})

    with pd.ExcelWriter(xlsx_path) as writer:
        other_df.to_excel(writer, sheet_name="Sheet1", index=False)
        standard_named_df.to_excel(writer, sheet_name="Orders", index=False)

    result = load_orders(xlsx_path, sheet_name="Orders")

    assert list(result["customer"]) == ["Ana", "Bruno"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def test_raises_file_not_found_for_missing_file(tmp_path: Path):
    missing_path = tmp_path / "does_not_exist.csv"

    with pytest.raises(FileNotFoundError):
        load_orders(missing_path)


def test_raises_value_error_for_unsupported_extension(tmp_path: Path):
    bad_path = tmp_path / "orders.txt"
    bad_path.write_text("customer,amount,order_date\nAna,100,2026-01-01")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        load_orders(bad_path)


def test_raises_value_error_when_required_column_missing_after_mapping(
    tmp_path: Path, sample_df
):
    csv_path = tmp_path / "orders.csv"
    sample_df.to_csv(csv_path, index=False)

    # Mapping omits "Data" -> "order_date", so the result is missing a
    # required standard column.
    with pytest.raises(ValueError, match="Missing required column"):
        load_orders(
            csv_path,
            column_mapping={"Cliente": "customer", "Valor": "amount"},
        )


def test_raises_value_error_when_no_mapping_and_columns_dont_match(
    tmp_path: Path, sample_df
):
    csv_path = tmp_path / "orders.csv"
    sample_df.to_csv(csv_path, index=False)

    # No mapping given, and the file's columns ("Cliente", "Valor", "Data")
    # don't match the standard names.
    with pytest.raises(ValueError, match="Missing required column"):
        load_orders(csv_path)


def test_extra_columns_are_preserved(tmp_path: Path, standard_named_df):
    df = standard_named_df.copy()
    df["region"] = ["South", "North"]
    csv_path = tmp_path / "orders.csv"
    df.to_csv(csv_path, index=False)

    result = load_orders(csv_path)

    assert "region" in result.columns