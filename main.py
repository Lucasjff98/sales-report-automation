"""
Main entry point: orchestrates the full sales report pipeline.

    1. Load raw orders from a CSV/Excel file            (data.loader)
    2. Aggregate orders by customer                      (processing.summarize)
    3. Generate a formatted Excel report                 (report.excel_report)
    4. Email the report to the configured recipients      (delivery.*)

Usage
-----
    python main.py --input data/raw_orders.csv --output output/sales_report.xlsx

    # Skip sending the email (useful for testing the pipeline locally):
    python main.py --input data/raw_orders.csv --output output/sales_report.xlsx --no-email

    # If your raw file uses different column names:
    python main.py --input data/raw_orders.xlsx \\
        --column-map "Cliente=customer,Valor=amount,Data=order_date"
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from data.loader import load_orders
from delivery.config import build_email_config
from delivery.email_sender import send_report_email
from processing.summarize import summarize_orders
from report.excel_report import generate_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_column_map(raw: str | None) -> dict[str, str] | None:
    """
    Parse a "SourceCol=standard_name,SourceCol2=standard_name2" string
    into the dict format expected by data.loader.load_orders.
    """
    if not raw:
        return None

    mapping: dict[str, str] = {}
    for pair in raw.split(","):
        if "=" not in pair:
            raise ValueError(
                f"Invalid --column-map entry '{pair}'. Expected format: "
                "SourceColumn=standard_name"
            )
        source_col, standard_name = pair.split("=", 1)
        mapping[source_col.strip()] = standard_name.strip()
    return mapping


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sales report automation pipeline.")
    parser.add_argument(
        "--input", required=True, help="Path to the raw orders CSV/Excel file."
    )
    parser.add_argument(
        "--output",
        default="output/sales_report.xlsx",
        help="Path to write the generated Excel report (default: %(default)s).",
    )
    parser.add_argument(
        "--column-map",
        default=None,
        help=(
            "Optional column mapping if the raw file's columns don't match "
            "'customer', 'amount', 'order_date'. Format: "
            "'SourceCol=customer,SourceCol2=amount,SourceCol3=order_date'."
        ),
    )
    parser.add_argument(
        "--sheet-name",
        default=0,
        help="Sheet name or index to read when --input is an Excel file (default: first sheet).",
    )
    parser.add_argument(
        "--config",
        default="delivery/config.yaml",
        help="Path to the non-sensitive delivery settings file (default: %(default)s).",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Path to the .env file with credentials (default: python-dotenv's auto-discovery).",
    )
    parser.add_argument(
        "--subject",
        default=None,
        help="Custom email subject (default: the built-in default subject).",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Run the pipeline and generate the report, but skip sending the email.",
    )
    return parser.parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> Path:
    """
    Execute the full pipeline and return the path to the generated report.
    Raises whatever exception occurs in any stage; the caller (main) is
    responsible for logging and exit codes.
    """
    column_mapping = parse_column_map(args.column_map)

    logger.info("Loading raw orders from %s", args.input)
    raw_orders = load_orders(
        args.input, column_mapping=column_mapping, sheet_name=args.sheet_name
    )
    logger.info("Loaded %d raw order rows", len(raw_orders))

    logger.info("Aggregating orders by customer")
    summary = summarize_orders(raw_orders)
    logger.info("Aggregated into %d customer rows", len(summary))

    logger.info("Generating Excel report at %s", args.output)
    report_path = generate_report(summary, args.output)
    logger.info("Report written to %s", report_path)

    if args.no_email:
        logger.info("--no-email flag set: skipping email delivery")
        return report_path

    logger.info("Loading email configuration")
    email_config = build_email_config(args.config, args.env_file)

    logger.info("Sending report to: %s", ", ".join(email_config["recipients"]))
    send_kwargs = {}
    if args.subject:
        send_kwargs["subject"] = args.subject
    send_report_email(email_config, report_path, **send_kwargs)
    logger.info("Email sent successfully")

    return report_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_pipeline(args)
    except Exception:
        logger.exception("Pipeline failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())