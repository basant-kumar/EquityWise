# EquityWise

EquityWise generates RSU, ESPP, and Foreign Assets reports for Indian tax
filing from E*Trade, Excelity, bank, stock-price, and exchange-rate data.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

## Features

- RSU and ESPP vesting-income calculations
- Configurable foreign-asset capital gain/loss calculations by sale lot
- Foreign Assets reporting for the corresponding calendar year
- PDF and Excel RSU statement support
- Bank reconciliation and deductible selling-expense handling
- Cross-source validation and Excel/CSV reports

## Quick start

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), and Git.

```bash
git clone https://github.com/basant-kumar/EquityWise.git
cd EquityWise
uv sync
uv run equitywise --help
```

Place your private input files under `data/user_data/` and run:

```bash
uv run equitywise generate-reports --financial-year FY25-26
```

This generates detailed RSU reports for FY25-26 and Foreign Assets reports for
calendar year 2025 in both Excel and CSV formats, with validation enabled.

## Input data

| Source | Location |
| --- | --- |
| E*Trade Benefit History | `data/user_data/benefit_history/` |
| E*Trade G&L statements | `data/user_data/gl_statements/` |
| RSU/ESPP PDF or Excel statements | `data/user_data/rsu_documents/` |
| Bank statements (optional) | `data/user_data/bank_statements/` |
| Exchange rates and stock prices | `data/reference_data/` |

Never commit files under `data/user_data/`; they contain sensitive financial
information. See the [data setup guide](data/README.md) for filenames and source
instructions.

Refresh both public reference datasets with one command:

```bash
uv run python scripts/update_reference_data.py
```

This adds missing ADBE trading days and refreshes the complete SBI USD TT BUY
archive.

## Capital gains

Choose one of these values:

| Configuration value | What it does |
| --- | --- |
| `inr-components` | **Default and recommended.** Converts sale proceeds and acquisition cost to INR separately using their applicable Rule 115 SBI TTBR dates, then calculates the gain/loss in INR. Use this unless your tax adviser directs otherwise. |
| `usd-gain-conversion` | Legacy compatibility. Calculates the gain/loss in USD first and converts that single result using the sale Rule 115 SBI TTBR. Use this only to reproduce older EquityWise reports or when specifically advised. |

### `inr-components` formula (default)

```text
Sale proceeds INR = Gross proceeds USD × sale Rule 115 SBI TTBR
Acquisition cost INR = Adjusted cost basis USD × acquisition Rule 115 SBI TTBR
Selling expense INR = Selling expense USD × sale Rule 115 SBI TTBR

Capital gain/loss INR
  = Sale proceeds INR − Acquisition cost INR − Selling expense INR
```

### `usd-gain-conversion` formula (legacy)

```text
Net gain/loss USD
  = Gross proceeds USD − Adjusted cost basis USD − Selling expense USD

Capital gain/loss INR = Net gain/loss USD × sale Rule 115 SBI TTBR
```

The default needs no option. To select a method for one run, place the global
option before `generate-reports`:

```bash
uv run equitywise --capital-gains-method inr-components generate-reports --financial-year FY25-26
uv run equitywise --capital-gains-method usd-gain-conversion generate-reports --financial-year FY25-26
```

To configure every run, put exactly one of these values in `.env`:

```dotenv
RSU_FA_CAPITAL_GAINS_CALCULATION_METHOD=inr-components
```

or:

```dotenv
RSU_FA_CAPITAL_GAINS_CALCULATION_METHOD=usd-gain-conversion
```

Bank INR credits are used for reconciliation, not as the Rule 115 conversion
rate. A bank-supported USD selling expense is deducted and converted using the
sale SBI TTBR. See [capital-gain calculations](docs/CAPITAL_GAINS.md) for the
complete formulas, TTBR date selection, and bank-rate treatment.

## Documentation

- [User and command guide](docs/README.md)
- [Data directory guide](data/README.md)
- [Bank pattern configuration](docs/BANK_PATTERNS.md)
- [Contribution guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Contributing

Contributions are welcome. Anyone can fork the public repository and open a pull
request. Pull requests are reviewed and merged by repository maintainers;
contributors cannot merge into this repository unless they have been granted
write or maintain access.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes, especially the
financial-data privacy requirements.

## License and disclaimer

Licensed under the [MIT License](LICENSE).

EquityWise is provided for informational purposes. Verify tax calculations with
a qualified tax professional before filing.
