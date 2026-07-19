# EquityWise user guide

This guide covers installation, input data, commands, calculations, reports,
validation, and troubleshooting. For a quick introduction, start with the
[main README](../README.md).

## Installation

Install Python 3.11 or newer, Git, and
[uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```bash
git clone https://github.com/basant-kumar/EquityWise.git
cd EquityWise
uv sync
uv run equitywise --help
```

If you do not use uv:

```bash
python -m pip install -e .
python -m equitywise --help
```

## Prepare input data

EquityWise keeps private user data separate from public reference data.

```text
data/
├── user_data/
│   ├── benefit_history/   # BenefitHistory.xlsx
│   ├── gl_statements/     # G&L_Expanded_YYYY.xlsx
│   ├── rsu_documents/     # RSU statements as PDF or Excel
│   └── bank_statements/   # Optional remittance records
└── reference_data/
    ├── exchange_rates/    # SBI TTBR USD/INR rates
    └── adobe_stock/       # ADBE historical prices
```

### E*Trade files

- Download Benefit History Expanded and save it under
  `data/user_data/benefit_history/`.
- Download the Expanded Gains & Losses statement for every relevant calendar
  year and save the files under `data/user_data/gl_statements/`.

### RSU and ESPP statements

Download the Stock Perquisites Statement for each financial year from the
benefits portal. Both PDF and Excel statements are supported. Save them under
`data/user_data/rsu_documents/`.

### Bank statements

Bank statements are optional, but they allow EquityWise to reconcile actual INR
credits and deduct confirmed selling expenses that are absent from the broker
G&L statement. See [BANK_PATTERNS.md](BANK_PATTERNS.md) for supported and custom
bank patterns.

### Reference data

Exchange rates and Adobe stock prices belong under `data/reference_data/`. See
the [reference-data guide](../data/reference_data/README.md) for formats and the
update script.

Private statements, generated reports, account numbers, and tax data must never
be committed. The repository ignores the standard private-data locations, but
always inspect `git status` before committing.

## Generate annual reports

The recommended command generates both report types:

```bash
uv run equitywise generate-reports --financial-year FY25-26
```

`FY25-26` maps to:

- RSU and ESPP reporting for financial year FY25-26
- Foreign Assets reporting for calendar year 2025

Detailed Excel and CSV output plus cross-validation are enabled by default.

Useful overrides:

```bash
uv run equitywise generate-reports --financial-year FY25-26 --output-format excel
uv run equitywise generate-reports --financial-year FY25-26 --summary-only
uv run equitywise generate-reports --financial-year FY25-26 --no-validate
```

## Run one report

```bash
# RSU/ESPP only
uv run equitywise calculate-rsu \
  --financial-year FY25-26 \
  --output-format both \
  --detailed \
  --validate

# Foreign Assets only
uv run equitywise calculate-fa \
  --calendar-year 2025 \
  --output-format both \
  --detailed \
  --validate
```

Use command-specific help for the authoritative option list:

```bash
uv run equitywise generate-reports --help
uv run equitywise calculate-rsu --help
uv run equitywise calculate-fa --help
```

## Validate input files

```bash
uv run equitywise validate-data
uv run equitywise --log-level DEBUG validate-data
```

Validation checks file structure, required columns, data types, date ranges,
cross-source transaction matching, and agreement between detailed events and
report totals. Coverage warnings can be expected when Benefit History contains
older years for which no G&L statement was supplied; review every warning before
filing.

## Calculation notes

### Vesting income

The statement's vest-date FMV and INR amount are used to calculate taxable
vesting income. RSU vesting income is reported separately from capital gains.

### Capital gains

The calculation method is configurable. The default is `inr-components`:

```text
Sale proceeds INR = sale proceeds USD × sale Rule 115 SBI TTBR
Acquisition cost INR = adjusted cost basis USD × acquisition Rule 115 SBI TTBR
Selling expense INR = selling expense USD × sale Rule 115 SBI TTBR

Capital gain/loss INR
  = Sale proceeds INR − Acquisition cost INR − Selling expense INR
```

See [Capital-gain calculations](CAPITAL_GAINS.md) for the alternative
`usd-gain-conversion` method and configuration instructions.

### Bank reconciliation

The bank's rate converts the post-selling-expense USD remittance into the actual
INR credit. It is used for reconciliation, not as the Rule 115 tax rate.
Confirmed selling expenses reduce capital gains. GST, bank FX spread, and
line-level bank rounding remain reconciliation items unless separately
supported as deductible expenses.

## Report output

Reports are written to `output/`:

- RSU summary, vesting-event, sale-event, and bank-reconciliation CSV files
- Multi-sheet RSU Excel workbook
- Foreign Assets summary and holdings CSV files
- Multi-sheet Foreign Assets Excel workbook
- Validation report when RSU validation is requested

Detailed sale reports show the SBI TTBRs, selected calculation method, gross and
net gains, and allocated selling expenses.

## Troubleshooting

### A file is missing

Confirm its name and directory using the [data guide](../data/README.md), then
run `uv run equitywise validate-data`.

### An Excel lock file is detected

Close the workbook in Excel. Temporary files beginning with `~$` are ignored,
but the original workbook still needs to be readable.

### An exchange rate or stock price is missing

Check that reference data covers every vesting, sale, and valuation date. The
calculator uses a limited nearby-date fallback and reports missing coverage.

### Totals differ between sources

Run the annual command with validation and debug logging:

```bash
uv run equitywise --log-level DEBUG generate-reports \
  --financial-year FY25-26
```

Check statement coverage, transaction dates, quantities, withheld shares, and
bank remittance details before changing calculations.

## Development and contributions

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the fork workflow, test commands,
privacy rules, review process, and merge permissions.

## Disclaimer

EquityWise is an informational calculation tool, not tax advice. Retain your
source documents and verify the final filing with a qualified tax professional.
