# 🎯 EquityWise

**Smart equity tax calculations from E*Trade data - RSU, ESPP & Foreign Assets for Indian compliance**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 9/9 Passing](https://img.shields.io/badge/Tests-9%2F9%20Passing-brightgreen.svg)](tests/)

EquityWise is a comprehensive tool for processing E*Trade and Excelity data to calculate tax obligations for RSU and ESPP equity compensation and Foreign Assets compliance under Indian tax law.

## 🎯 **What This Tool Does**

- **RSU & ESPP Tax Calculations**: Accurately compute capital gains/losses on equity sales
- **Foreign Assets Compliance**: Generate FA declaration data for Indian tax filing
- **Comprehensive Data Validation**: Cross-validate data consistency between E*Trade, Excelity, and G&L statements
- **CSV Export for Tax Forms**: Direct CSV export for FA declaration form import
- **Enhanced Excel Reports**: Professional formatting with currency, totals, and dynamic column widths
- **Bank Reconciliation**: Track equity proceeds and transfer expenses (multi-bank support)
- **Interactive CLI**: Guided workflows with progress tracking and error recovery

## 🚀 **Quick Start**

### Prerequisites

Before you start, ensure you have:
- **Python 3.11 or higher** ([Download here](https://www.python.org/downloads/))
- **Git** ([Download here](https://git-scm.com/downloads))

### Step 1: Install UV (Recommended Package Manager)

UV is a fast Python package manager. Choose your installation method:

**macOS/Linux:**
```bash
# Install UV using the official installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# IMPORTANT: Restart your terminal or source your shell profile
source ~/.zshrc  # for Zsh users
# OR
source ~/.bashrc  # for Bash users

# Alternative: Load UV environment directly
. "$HOME/.local/bin/env"
```

**Windows:**
```powershell
# Install UV using PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative - Using pip:**
```bash
pip install uv
```

### Step 2: Verify Installation

```bash
# Check Python version (should be 3.11+)
python --version

# Check UV installation
uv --version

# Check Git installation
git --version
```

### Step 3: Clone and Install EquityWise

```bash
# Clone the repository (replace with actual URL)
git clone <repository-url>
cd EquityWise

# Install using UV (recommended - faster and more reliable)
uv sync

# Alternative: Install using pip if UV doesn't work
pip install -e .
```

### Step 4: Verify Installation Works

```bash
# Test the installation
uv run equitywise --help

# You should see the help menu - if this works, you're ready!
```

### Step 5: Basic Usage

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

### 🚨 **Installation Troubleshooting**

**Issue 1: "zsh: command not found: uv"**
```bash
# If UV is installed but not found, try these solutions:

# Solution 1: Load UV environment
. "$HOME/.local/bin/env"
uv --version  # Should work now

# Solution 2: Reload your shell profile
source ~/.zshrc  # or ~/.bashrc
uv --version  # Test again

# Solution 3: Use full path to UV
/Users/$(whoami)/.local/bin/uv --version

# Solution 4: Install UV with pip instead
pip install uv

# Solution 5: Skip UV entirely, use pip
pip install -e .

# Then use: python -m equitywise instead of uv run equitywise

# Example usage with pip:
python -m equitywise --help
python -m equitywise calculate-rsu --financial-year FY24-25
```

**Issue 2: "Python version too old"**
```bash
# Check your Python version
python --version

# If below 3.11, install newer Python from https://www.python.org/downloads/
# Or use pyenv/conda to manage Python versions
```

**Issue 3: "Permission denied"**
```bash
# On macOS/Linux, try:
sudo pip install uv

# Or use --user flag:
pip install --user uv
```

## 📁 **Required Data Files**

EquityWise uses an organized folder structure to separate your private financial data from public market data:

```
data/
├── user_data/                          # 🔒 Personal financial data (NEVER commit to Git)
│   ├── benefit_history/
│   │   └── BenefitHistory.xlsx         # E*Trade comprehensive transaction history
│   ├── gl_statements/
│   │   ├── G&L_Expanded_2023.xlsx      # Annual gain/loss statements
│   │   ├── G&L_Expanded_2024.xlsx      # (one file per calendar year)
│   │   └── G&L_Expanded_2025.xlsx      # 
│   ├── rsu_documents/
│   │   ├── RSU_FY-22-23.pdf            # RSU & ESPP vesting statements from Excelity
│   │   ├── RSU_FY-23-24.pdf            # (one file per financial year)
│   │   ├── RSU_FY-24-25.pdf            # Supports both RSU and ESPP entries
│   │   └── RSU_FY-25-26.pdf            # 
│   └── bank_statements/
│       ├── BankStatement_FY23-24.xls   # Bank transfer records (optional)
│       └── BankStatement_FY24-25.xls   # 
└── reference_data/                     # 🌍 Public market data (safe to version control)
    ├── exchange_rates/
    │   └── Exchange_Reference_Rates.csv # SBI TTBR exchange rates
    └── adobe_stock/
        └── HistoricalData_*.csv        # Adobe stock price history
```

### 🔒 **Security & Privacy**
- **`user_data/`**: Contains your sensitive financial information - automatically ignored by Git
- **`reference_data/`**: Contains publicly available market data - safe to version control

### ✨ **Benefits of Organized Structure**
- **📂 Type-based organization**: Find files by their purpose (E*Trade, Excelity, Bank, etc.)
- **🔒 Enhanced privacy**: Clear separation between sensitive and public data
- **📈 Scalable**: Easily add more years of data without clutter
- **🧭 Intuitive navigation**: Logical folder names make it easy to locate files
- **📖 Self-documenting**: Each subfolder has README with specific instructions

### 📥 **How to Get Data Files**

#### 🏛️ **E*Trade Files** → `data/user_data/`
- **BenefitHistory.xlsx**: 
  - Login to **E*Trade → At Work → My Account → Benefit History → Download Expanded**
  - Save in: `data/user_data/benefit_history/BenefitHistory.xlsx`

- **G&L Statements** (one per calendar year):
  - Login to **E*Trade → At Work → My Account → Gains & Losses → Download Expanded**
  - Save in: `data/user_data/gl_statements/G&L_Expanded_YYYY.xlsx`

#### 📄 **RSU & ESPP Vesting Statements** → `data/user_data/rsu_documents/`
- Login to **Excelity Portal (Adobe Benefits)**
- Navigate: **Payroll & Benefits → My Reports → Stock Perquisites Statement**
- **Select Financial Year → Download as PDF or Excel**
- Save as: `data/user_data/rsu_documents/RSU_FY-XX-XX.pdf` or `RSU_FY-XX-XX.xlsx`
- **Note**: Files may contain both RSU and ESPP entries - both are automatically parsed

#### 🏦 **Bank Statements** → `data/user_data/bank_statements/` (Optional)
- Export bank statements covering RSU sale periods  
- Save as: `data/user_data/bank_statements/BankStatement_FYXX-XX.xls`
- **Multi-Bank Support**: Configurable patterns for SBI, HDFC, ICICI, Axis, Kotak banks
- **Custom Patterns**: Add patterns for any bank - see [Bank Patterns Guide](docs/BANK_PATTERNS.md)

#### 📈 **Adobe Stock Data & Exchange Rates** → `data/reference_data/`

Use the included script to automatically fetch the latest ADBE stock prices and USD-INR exchange rates:

```bash
# One-time setup (if .venv doesn't exist yet)
uv venv && uv pip install yfinance requests

# Fetch missing data up to today
.venv/bin/python scripts/update_reference_data.py
```

The script detects the last date in each CSV and only fetches what's missing — no duplicates, no manual downloads needed. See [`data/reference_data/README.md`](data/reference_data/README.md) for details on data sources and format.

## 💡 **Usage Examples**

### RSU Tax Calculation

```bash
# Calculate for specific financial year with detailed output
uv run equitywise calculate-rsu \
  --financial-year FY24-25 \
  --output-format excel \
  --detailed

# Enable comprehensive data validation (recommended)
uv run equitywise calculate-rsu \
  --financial-year FY24-25 \
  --validate

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

# Enable data validation for FA calculations (recommended)
uv run equitywise calculate-fa \
  --calendar-year 2024 \
  --validate

# Check if FA declaration is required
uv run equitywise calculate-fa --calendar-year 2024 --check-only

# Generate CSV export for direct import into FA declaration forms
uv run equitywise calculate-fa \
  --calendar-year 2024 \
  --output-format csv \
  --export-fa-csv
```

**Sample Output:**
```
🌍 Foreign Assets Summary for CY 2024
=====================================
💼 Vested Holdings: ₹4,23,455.76 (9.0 shares)
📊 Peak Balance: ₹4,33,160.00 (May 31, 2024)
⚖️  Declaration Required: ✅ YES (Peak > ₹2,00,000)

✅ FA Declaration CSV created: output/FA_Declaration_2024.csv
📊 20 vest-wise entries ready for import
```

## 🔍 **Comprehensive Data Validation**

EquityWise includes a powerful validation system that cross-validates data consistency between different sources (BenefitHistory, RSU PDFs, G&L statements) to ensure calculation accuracy.

### Key Validation Features

- **📊 Cross-Data Source Validation**: Compares vesting events across RSU PDFs and BenefitHistory
- **💰 Sale Transaction Consistency**: Validates sale events between G&L statements and BenefitHistory  
- **📅 Date Range Overlap Analysis**: Matches FY-based RSU calculations with CY-based FA calculations
- **🧮 Internal Calculation Consistency**: Verifies summary totals match detailed transaction sums
- **⚠️ Detailed Error Reporting**: Shows exactly which transactions are missing or inconsistent

### Using Validation

```bash
# Enable validation for RSU calculations (recommended)
uv run equitywise calculate-rsu --financial-year FY24-25 --validate

# Enable validation for FA calculations (recommended)  
uv run equitywise calculate-fa --calendar-year 2024 --validate

# Combined validation with detailed output
uv run equitywise calculate-rsu --financial-year FY24-25 --validate --detailed
```

### Sample Validation Output

```
🔍 Comprehensive Validation Results
===================================

✅ BenefitHistory vs RSU PDF Consistency: PASSED
• 12 vesting events validated across data sources
• All vesting dates and quantities match

✅ BenefitHistory vs G&L Statement Consistency: PASSED  
• 8 sale transactions validated
• All sale dates, quantities, and amounts consistent

✅ RSU vs FA Overlap Validation: PASSED
• Overlapping period: 2024-01-01 to 2024-12-31
• 3 common transactions validated
• Total overlap value: ₹2,45,678.90

✅ RSU Internal Consistency: PASSED
• Vesting income calculation validated
• Capital gains calculation validated

✅ FA Internal Consistency: PASSED
• Holdings calculation validated
• Peak balance calculation validated

✅ Comprehensive validation PASSED!
• 0 warnings
```

### Validation Benefits

- **🎯 Accuracy Assurance**: Catch data entry errors and missing transactions
- **🔗 Data Consistency**: Ensure all data sources are in sync
- **📋 Audit Trail**: Generate detailed validation reports for tax filing
- **⏰ Time Saving**: Identify issues early rather than during tax filing
- **🔒 Confidence**: Know your calculations are based on consistent, verified data

## 🎛️ **Command Reference**

### Core Commands

**`calculate-rsu`** - Calculate RSU tax obligations
```bash
# Calculate for specific financial year with Excel output
uv run equitywise calculate-rsu --financial-year FY24-25 --output-format excel

# Calculate with comprehensive data validation (recommended)
uv run equitywise calculate-rsu --financial-year FY24-25 --validate

# Interactive mode with detailed breakdown
uv run equitywise calculate-rsu --interactive --detailed
```

**`calculate-fa`** - Calculate Foreign Assets compliance
```bash
# Check FA declaration requirement for 2024
uv run equitywise calculate-fa --calendar-year 2024 --check-only

# Calculate with comprehensive data validation (recommended)
uv run equitywise calculate-fa --calendar-year 2024 --validate

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
- `--output-format excel` - Generate Excel reports with enhanced formatting (recommended, default)
- `--output-format csv` - Generate CSV files for analysis
- `--output-format both` - Generate both Excel and CSV

**Data Validation Options:**
- `--validate` - Enable comprehensive cross-validation between data sources (recommended)

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

### Enhanced Excel Reports
- **RSU_Report_FY24-25.xlsx**: Multi-sheet workbook with professional formatting
  - ✨ Proper currency formatting (₹/#,##0.00) instead of text
  - 📊 Total rows for USD and INR columns
  - 📐 Dynamic column widths to prevent "######" display
  - 📝 Wrap text headers for better readability
  - 📋 Separated vesting and sold transaction details

- **FA_Report_2024.xlsx**: Foreign Assets declaration with enhanced formatting
  - ✨ Professional currency and number formatting
  - 📊 Summary totals and subtotals
  - 📐 Optimal column widths for all data

### CSV Reports  
- **RSU_Summary_FY24-25.csv**: Lightweight summary for analysis
- **FA_Equity_Holdings_2024.csv**: Detailed holdings data
- **FA_Declaration_2024.csv**: Ready-to-import FA declaration form data

### Console Output
Beautiful Rich-formatted tables with color coding and progress indicators.

## 🔧 **Configuration**

Create `config/settings.toml` for custom settings:

```toml
[data_paths]
benefit_history_path = "data/user_data/benefit_history/BenefitHistory.xlsx"
gl_statements_paths = [
    "data/user_data/gl_statements/G&L_Expanded_2023.xlsx", 
    "data/user_data/gl_statements/G&L_Expanded_2024.xlsx", 
    "data/user_data/gl_statements/G&L_Expanded_2025.xlsx"
]
sbi_rates_path = "data/reference_data/exchange_rates/Exchange_Reference_Rates.csv"
adobe_stock_path = "data/reference_data/adobe_stock/HistoricalData_*.csv"
rsu_pdf_paths = [
    "data/user_data/rsu_documents/RSU_FY-22-23.pdf",
    "data/user_data/rsu_documents/RSU_FY-23-24.pdf", 
    "data/user_data/rsu_documents/RSU_FY-24-25.pdf",
    "data/user_data/rsu_documents/RSU_FY-25-26.pdf"
]
# Note: PDFs automatically parse both RSU and ESPP entries

[calculation_settings]
fa_declaration_threshold_inr = 200000.0
fallback_days_exchange_rate = 7
fallback_days_stock_price = 15

[bank_settings]
default_bank_pattern = "sbi"  # or "hdfc", "icici", "axis", "kotak"

# Custom bank patterns (optional)
[bank_settings.bank_remittance_patterns]
mybank = "USD\\s+([\\d.]+)\\s+RATE([\\d.]+)\\s+FEE([\\d.]+)"

[output_settings]
default_output_dir = "output"
excel_formatting = true
include_formulas = false
```

## 🩺 **Data Validation**

EquityWise includes multiple layers of data validation for maximum accuracy:

### Standard Data Validation
```bash
# Validate all data files
uv run equitywise validate-data

# Check specific file types
uv run equitywise validate-data --file-type benefit-history
uv run equitywise --log-level DEBUG validate-data
```

**Basic Validation Checks:**
- ✅ File format and structure
- ✅ Required columns present
- ✅ Date format consistency
- ✅ Numeric data integrity
- ✅ Cross-file data consistency

### Comprehensive Cross-Validation
The `--validate` flag enables advanced validation across all data sources:

```bash
# Enable cross-validation (recommended for accuracy)
uv run equitywise calculate-rsu --financial-year FY24-25 --validate
uv run equitywise calculate-fa --calendar-year 2024 --validate
```

**Advanced Validation Features:**
- 📊 **Multi-Source Consistency**: Validates data across BenefitHistory, RSU PDFs, and G&L statements
- 💰 **Transaction Matching**: Ensures sale events match across different data sources
- 📅 **Date Range Validation**: Validates overlapping periods between FY and CY calculations  
- 🧮 **Calculation Verification**: Cross-checks summary totals against detailed transaction sums
- ⚠️ **Detailed Error Reports**: Identifies exactly which transactions are missing or inconsistent
- 🎯 **Event Type Accuracy**: Distinguishes between actual sales ("Shares sold") and other events

## 🚨 **Troubleshooting**

### Common Issues

**Q: "FileNotFoundError: BenefitHistory.xlsx not found"**
```bash
# Check data directory structure
ls -la data/user_data/benefit_history/
# Ensure file has correct name and location (case-sensitive)
# Should be: data/user_data/benefit_history/BenefitHistory.xlsx
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
# Check data/reference_data/exchange_rates/Exchange_Reference_Rates.csv for data completeness
```

**Q: "Excel file format cannot be determined" or "Failed to parse ~$*.xlsx"**
```bash
# This occurs when Excel files are open and creating temporary lock files
# Solution: Close Excel files before running EquityWise, or the tool will automatically skip temp files
# The tool now automatically filters out Excel temporary files (~$*.xlsx)
```

**Q: "Validation warnings about missing transactions"**
```bash
# Use the validation system to identify data inconsistencies:
uv run equitywise calculate-rsu --financial-year FY24-25 --validate

# Check that:
# - BenefitHistory.xlsx is complete and up-to-date
# - G&L statements contain all sale transactions
# - RSU PDFs match the financial year being calculated
# - Event types in BenefitHistory distinguish between "Shares sold" and "Shares released"
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

- **Adobe Inc.** for the RSU and ESPP program structure  
- **E*Trade** for comprehensive transaction data export
- **SBI** for TTBR exchange rate data
- **Indian Income Tax Department** for FA declaration guidelines

## 🆕 **Recent Updates**

**Enhanced Excel Reporting**: Professional currency formatting, dynamic column widths, totals, and wrap-text headers  
**Comprehensive Validation**: Cross-validation system for data consistency across all sources  
**Bug Fixes**: Excel temporary file handling, BenefitHistory data interpretation improvements  
**User Experience**: Better error messages, detailed validation reports, and improved accuracy

---

**Made with ❤️ for Adobe employees and RSU holders navigating Indian tax compliance**

For support or questions, please open an issue on GitHub.
