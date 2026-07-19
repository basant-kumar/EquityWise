# EquityWise

EquityWise generates RSU, ESPP, and Foreign Assets reports for Indian tax
filing from E*Trade, Excelity, bank, stock-price, and exchange-rate data.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

## Features

- RSU and ESPP vesting-income calculations
- INR-first capital gain/loss calculations by sale lot
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

## Capital gain formula

Each sale lot is calculated directly in INR:

```text
Sale proceeds (USD) × sale-date exchange rate
− Acquisition cost (USD) × vest-date exchange rate
− Selling expense (USD) × sale-date exchange rate
= Capital gain or loss (INR)
```

The broker's USD gain/loss is retained for reconciliation but does not determine
the INR capital gain/loss.

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
