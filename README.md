# 🎯 EquityWise

**Smart equity tax calculations from E*Trade data - RSU, ESOP, ESPP & Foreign Assets for Indian compliance**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 9/9 Passing](https://img.shields.io/badge/Tests-9%2F9%20Passing-brightgreen.svg)](tests/)

EquityWise is a comprehensive tool for processing E*Trade data to calculate tax obligations for equity compensation (RSU, ESOP, ESPP) and Foreign Assets compliance under Indian tax law.

## 🎯 **What This Tool Does**

- **RSU Tax Calculations**: Accurately compute capital gains/losses on RSU sales
- **Foreign Assets Compliance**: Generate FA declaration data for Indian tax filing
- **Multi-Format Reports**: Professional Excel and CSV reports for tax preparation
- **Bank Reconciliation**: Track RSU proceeds and transfer expenses
- **Interactive CLI**: Guided workflows with progress tracking and error recovery

## 🚀 **Quick Start**

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd EquityWise

# Install using UV (recommended)
uv sync

# Or install using pip
pip install -e .
```

### Basic Usage

```bash
# Interactive mode (recommended for first-time users)
uv run equitywise

# Calculate RSU taxes for FY 2024-25
uv run equitywise calculate-rsu --financial-year FY24-25 --output-format excel

# Calculate Foreign Assets for Calendar Year 2024
uv run equitywise calculate-fa --calendar-year 2024 --output-format both

# Get comprehensive help
uv run equitywise help-guide
```

## 📁 **Required Data Files**

Place your E*Trade and bank files in the `data/` directory:

```
data/
├── BenefitHistory.xlsx          # E*Trade RSU vesting history
├── GainLoss_2024.xlsx          # E*Trade gain/loss statements  
├── GainLoss_2025.xlsx          # (if applicable)
├── HistoricalData_*.xlsx       # Adobe stock price history
├── SBI_TTBR_Rates.xlsx         # SBI exchange rates
└── BankStatement.xlsx          # Bank transfer records (optional)
```

### 📥 **How to Get Data Files**

1. **E*Trade Files**: 
   - Login to E*Trade → My Account → Documents & Tax Forms
   - Download "Benefit History" and "Gain & Loss" statements

2. **Adobe Stock Data**: 
   - Yahoo Finance → ADBE → Historical Data → Download CSV
   - Convert to Excel format

3. **SBI Exchange Rates**: 
   - SBI website → TTBR rates → Download historical data
   - Or use the tool's built-in rate fetching (future feature)

## 💡 **Usage Examples**

### RSU Tax Calculation

```bash
# Calculate for specific financial year with detailed output
uv run equitywise calculate-rsu \
  --financial-year FY24-25 \
  --output-format excel \
  --detailed

# Interactive mode for guided calculation
uv run equitywise calculate-rsu --interactive
```

**Sample Output:**
```
🎯 RSU Calculation Summary for FY 2024-25
==========================================
📊 Total Vested: 25.0 shares (₹1,507,011.83)
💰 Total Sold: 15.0 shares (₹957,543.21) 
📈 Capital Gains: ₹267,890.45
📊 Short-term: ₹89,234.12 | Long-term: ₹178,656.33
```

### Foreign Assets Declaration

```bash
# Calculate FA requirement for calendar year
uv run equitywise calculate-fa \
  --calendar-year 2024 \
  --as-of-date 2024-12-31 \
  --output-format both

# Check if FA declaration is required
uv run equitywise calculate-fa --calendar-year 2024 --check-only
```

**Sample Output:**
```
🌍 Foreign Assets Summary for CY 2024
=====================================
💼 Vested Holdings: ₹4,23,455.76 (9.0 shares)
📊 Peak Balance: ₹4,33,160.00 (May 31, 2024)
⚖️  Declaration Required: ✅ YES (Peak > ₹2,00,000)
```

## 🎛️ **Command Reference**

### Core Commands

**`calculate-rsu`** - Calculate RSU tax obligations
```bash
# Calculate for specific financial year with Excel output
uv run equitywise calculate-rsu --financial-year FY24-25 --output-format excel

# Interactive mode with detailed breakdown
uv run equitywise calculate-rsu --interactive --detailed
```

**`calculate-fa`** - Calculate Foreign Assets compliance
```bash
# Check FA declaration requirement for 2024
uv run equitywise calculate-fa --calendar-year 2024 --check-only

# Full FA report with detailed holdings
uv run equitywise calculate-fa --calendar-year 2024 --output-format excel --detailed
```

**`validate-data`** - Validate input data files
```bash
# Validate all data files
uv run equitywise validate-data

# Validate with detailed logging
uv run equitywise --log-level DEBUG validate-data
```

**`help-guide`** - Show comprehensive help documentation
```bash
# Show complete help guide
uv run equitywise help-guide

# Show specific section
uv run equitywise help-guide --section cli
```

### Common Options

**Output Format Options:**
- `--output-format excel` - Generate Excel reports (recommended, default)
- `--output-format csv` - Generate CSV files for analysis
- `--output-format both` - Generate both Excel and CSV

**Date Range Options:**
- `--financial-year FY24-25` - Indian Financial Year (April 2024 to March 2025)
- `--calendar-year 2024` - Calendar year (January to December 2024)
- `--start-date 2024-04-01` - Custom start date (YYYY-MM-DD format)
- `--end-date 2025-03-31` - Custom end date (YYYY-MM-DD format)

**Mode and Display Options:**
- `--detailed` - Include detailed breakdowns and calculations
- `--interactive` - Enable guided interactive mode
- `--log-level DEBUG` - Show detailed logging and progress information
- `--check-only` - Quick check without generating full reports

**File and Directory Options:**
- `--output-dir reports/` - Specify custom output directory
- `--config-file config.toml` - Use custom configuration file

## 📊 **Report Outputs**

### Excel Reports
- **RSU_Report_FY24-25.xlsx**: Multi-sheet workbook with summary, transactions, and reconciliation
- **FA_Report_2024.xlsx**: Foreign Assets declaration data with balance tracking

### CSV Reports  
- **RSU_Summary_FY24-25.csv**: Lightweight summary for analysis
- **FA_Equity_Holdings_2024.csv**: Detailed holdings data

### Console Output
Beautiful Rich-formatted tables with color coding and progress indicators.

## 🔧 **Configuration**

Create `config/settings.toml` for custom settings:

```toml
[data_paths]
benefit_history_path = "data/BenefitHistory.xlsx"
gl_statements_paths = ["data/GainLoss_2024.xlsx", "data/GainLoss_2025.xlsx"]
sbi_rates_path = "data/SBI_TTBR_Rates.xlsx"
adobe_stock_path = "data/HistoricalData_*.xlsx"

[calculation_settings]
fa_declaration_threshold_inr = 200000.0
fallback_days_exchange_rate = 7
fallback_days_stock_price = 15

[output_settings]
default_output_dir = "output"
excel_formatting = true
include_formulas = false
```

## 🩺 **Data Validation**

The tool includes comprehensive data validation:

```bash
# Validate all data files
uv run equitywise validate-data

# Check specific file types
uv run equitywise validate-data --file-type benefit-history
uv run equitywise --log-level DEBUG validate-data
```

**Validation Checks:**
- ✅ File format and structure
- ✅ Required columns present
- ✅ Date format consistency
- ✅ Numeric data integrity
- ✅ Cross-file data consistency

## 🚨 **Troubleshooting**

### Common Issues

**Q: "FileNotFoundError: BenefitHistory.xlsx not found"**
```bash
# Check data directory structure
ls -la data/
# Ensure file has correct name (case-sensitive)
```

**Q: "ValidationError: Invalid date format"**
```bash
# Run data validation to identify issues
uv run equitywise --log-level DEBUG validate-data
# Check date formats in Excel files (DD/MM/YYYY expected)
```

**Q: "No exchange rate found for date YYYY-MM-DD"**
```bash
# The tool uses 7-day fallback window
# Ensure SBI rates file covers the required date range
# Check SBI_TTBR_Rates.xlsx for data completeness
```

### Performance Tips

- **Large datasets**: Use `--batch-size 1000` for files with >5000 records
- **Memory issues**: Process one year at a time for multi-year calculations
- **Speed optimization**: Place data files on SSD storage

### Getting Help

```bash
# Comprehensive help guide
uv run equitywise help-guide

# Command-specific help  
uv run equitywise calculate-rsu --help
uv run equitywise calculate-fa --help

# Check tool version and dependencies
uv run equitywise --version
```

## 🧪 **Testing**

Run the comprehensive test suite:

```bash
# Run all tests (9 test suites)
python tests/run_all_tests.py

# Run specific test categories
uv run python -m pytest tests/test_rsu_calculator.py -v
uv run python -m pytest tests/test_fa_calculator.py -v

# Generate coverage report
uv run python -m pytest --cov=src/rsu_fa_tool --cov-report=html
```

**Test Coverage**: 9/9 test suites passing with comprehensive validation

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite: `python tests/run_all_tests.py`
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
uv sync --dev

# Install pre-commit hooks
pre-commit install

# Run code formatting
black src/ tests/
isort src/ tests/

# Run linting
flake8 src/ tests/
mypy src/
```

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ **Disclaimer**

This tool is provided for informational purposes only. Tax calculations should be verified with a qualified tax professional. The authors are not responsible for any errors in tax calculations or compliance issues.

## 🙏 **Acknowledgments**

- **Adobe Inc.** for the RSU program structure  
- **E*Trade** for comprehensive transaction data export
- **SBI** for TTBR exchange rate data
- **Indian Income Tax Department** for FA declaration guidelines

---

**Made with ❤️ for Adobe employees and RSU holders navigating Indian tax compliance**

For support or questions, please open an issue on GitHub.
