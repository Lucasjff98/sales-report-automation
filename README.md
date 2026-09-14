# Sales Report Automation

A no-browser sales/finance report automation pipeline: it reads raw order
data (CSV/Excel), aggregates it by customer, generates a formatted Excel
report, and emails it automatically to a configured list of recipients.

Built as a portfolio project to demonstrate a clean, testable pipeline
architecture in Python — pure business logic separated from I/O, secrets
kept out of version control, and 67 automated tests covering normal and
edge cases across every module.

## What it does

```
raw orders (CSV/Excel) → aggregate by customer → formatted Excel report → email delivery
```

1. **Load** — reads raw orders from a CSV or Excel file. Column names are
   configurable, so it adapts to whatever headers the source system uses.
2. **Summarize** — aggregates orders per customer: total amount, order
   count, average order value, and the date of the most recent order.
   This step is a pure function (no I/O, no side effects), which makes it
   trivial to unit test.
3. **Report** — generates a styled `.xlsx` file with a formatted table,
   a totals row, and a bar chart of total amount by customer.
4. **Deliver** — emails the generated report as an attachment over SMTP.

## Project structure

```
sales-report-automation/
├── data/           # File I/O: reading raw orders from CSV/Excel
├── processing/     # Pure aggregation logic (summarize_orders)
├── report/         # Excel report generation (openpyxl)
├── delivery/       # Email configuration + sending (SMTP)
├── tests/          # Unit and integration tests (pytest)
├── main.py         # CLI entry point that orchestrates the full pipeline
├── requirements.txt
├── .env.example    # Template for required environment variables
└── delivery/config.example.yaml  # Template for non-sensitive settings
```

## Why credentials are split from configuration

This project uses a **hybrid configuration model**:

| What | Where | Committed to Git? |
|---|---|---|
| `SENDER_EMAIL`, `SENDER_PASSWORD` (secrets) | `.env` | **Never** |
| `smtp_host`, `smtp_port`, `recipients`, `use_tls` | `delivery/config.yaml` | Safe to commit |

This keeps credentials out of source control entirely, while still
allowing the non-sensitive delivery settings to be versioned and reviewed
like any other code — a common pattern in real-world applications, where
`.env` files handle secrets and are always gitignored.

## Installation

```bash
git clone <this-repo-url>
cd sales-report-automation

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## Configuration

1. Copy the templates:
   ```bash
   cp .env.example .env
   cp delivery/config.example.yaml delivery/config.yaml
   ```

2. Fill in `.env` with your email credentials:
   ```
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=your-16-character-app-password
   ```
   > **Note:** most modern email providers (Gmail, Outlook/Office 365)
   > require an **app password** instead of your regular account
   > password once two-factor authentication is enabled. Regular
   > username/password SMTP login (Basic Authentication) has been phased
   > out entirely for Outlook.com/Hotmail consumer accounts as of 2026,
   > so this project was tested and validated end-to-end using Gmail SMTP.

3. Fill in `delivery/config.yaml` with your SMTP server and recipients:
   ```yaml
   smtp_host: smtp.gmail.com
   smtp_port: 587
   recipients:
     - recipient@example.com
   use_tls: true
   ```

## Usage

```bash
python main.py --input data/your_orders.csv --output output/sales_report.xlsx
```

If your raw file's columns don't already match `customer`, `amount`,
`order_date`, map them explicitly:

```bash
python main.py \
  --input data/your_orders.csv \
  --output output/sales_report.xlsx \
  --column-map "Cliente=customer,Valor=amount,Data=order_date"
```

To generate the report without sending an email (useful for testing):

```bash
python main.py --input data/your_orders.csv --output output/sales_report.xlsx --no-email
```

Run `python main.py --help` for all available options.

## Running the tests

```bash
python -m pytest tests/ -v
```

67 tests across 5 test modules, covering:
- Pure aggregation logic, including whitespace normalization, null
  customers, negative amounts (refunds), and invalid dates.
- File loading for both CSV and Excel, with and without column mapping.
- Excel report generation: formatting, totals row, and chart creation.
- Configuration loading from `.env` and YAML/JSON, with validation.
- Email sending, with the SMTP server mocked (no real network calls or
  credentials required to run the test suite).
- A full end-to-end integration test of the pipeline.

## Tech stack

- **pandas** — data loading and aggregation
- **openpyxl** — Excel report generation and formatting
- **PyYAML** — configuration file parsing
- **python-dotenv** — environment variable loading
- **pytest** — testing framework
- **smtplib** (standard library) — SMTP email delivery

## Design decisions worth noting

- `summarize_orders` is a **pure function**: it performs no I/O and never
  mutates its input, which makes it fully deterministic and easy to test
  in isolation from the rest of the pipeline.
- Customer names are normalized for whitespace (`"Ana "` and `"Ana"` are
  treated as the same customer) but **not** for capitalization
  (`"Ana"` and `"ana"` are treated as different customers) — unifying by
  case is a business decision that shouldn't be made silently inside a
  data-processing function.
- All file I/O is isolated to the `data/` and `report/` modules;
  `processing/` never touches the filesystem.