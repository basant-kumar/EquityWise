# 📖 EquityWise - Complete User Guide

**Comprehensive Step-by-Step Guide for Equity Compensation Tax Calculations**

This guide will walk you through every step of using EquityWise, from initial setup to generating professional tax reports for Indian compliance. EquityWise processes E*Trade data for RSU, ESPP, and Foreign Assets calculations.

---

## 🎯 **What You'll Accomplish**

By the end of this guide, you'll have:
- ✅ Complete RSU tax calculations for any financial year
- ✅ Foreign Assets declaration data for calendar years  
- ✅ Professional Excel and CSV reports ready for tax filing
- ✅ Bank reconciliation data for audit purposes
- ✅ Confidence in your tax compliance accuracy

---

## 📋 **Before You Start - Checklist**

### Required Files from E*Trade
- [ ] **BenefitHistory.xlsx** - RSU vesting transaction history
  - Login to **E*Trade** → **At Work** → **My Account** → **Benefit History** → **Download Expanded**
  - Save as: `BenefitHistory.xlsx`
- [ ] **Gain & Loss Statements** - Sale transaction records for each relevant year (2023, 2024, 2025)
  - Login to **E*Trade** → **At Work** → **My Account** → **Gains & Losses** → **Download Expanded**  
  - Save as: `G&L_Expanded_2023.xlsx`, `G&L_Expanded_2024.xlsx`, `G&L_Expanded_2025.xlsx`

### Required RSU & ESPP Documents from Excelity
- [ ] **RSU & ESPP Vesting Statements** - Download from Excelity Portal
  - Login to **Excelity Portal**
  - Navigate: **Payroll & Benefits** → **My Reports** → **Stock Perquisites Statement**
  - Select **Financial Year** (FY22-23, FY23-24, FY24-25, etc.)
  - **Download as PDF**
  - Save as: `RSU_FY-XX-XX.pdf`
  - **Note**: Files automatically parse both RSU and ESPP entries

### Required Reference Data  
- [ ] **Adobe Stock Price History** - Download from Yahoo Finance → ADBE → Historical Data
  - Save as: `HistoricalData_1234567890.csv` (any numeric suffix)
- [ ] **SBI Exchange Rates** - Download SBI TTBR rates or use provided file
  - Save as: `Exchange_Reference_Rates.csv`

### Optional Files
- [ ] **Bank Statement** - For reconciliation (if you want to track transfer expenses)
  - Save as: `BankStatement_FY24-25.xls`

---

## 🚀 **Step 1: Installation & Setup**

### 1.1 Prerequisites

Before you start, ensure you have:
- **Python 3.11 or higher** ([Download here](https://www.python.org/downloads/))
- **Git** ([Download here](https://git-scm.com/downloads))

Check your versions:
```bash
# Verify Python version (must be 3.11+)
python --version

# Verify Git is installed
git --version
```

### 1.2 Install UV Package Manager

UV is a fast Python package manager. If you don't have it:

**macOS/Linux:**
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# CRITICAL: Restart your terminal or reload your shell
source ~/.zshrc  # for Zsh
# OR  
source ~/.bashrc  # for Bash

# Alternative: Load UV environment directly
. "$HOME/.local/bin/env"

# Verify installation
uv --version
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

### 1.3 Clone and Install EquityWise

```bash
# Clone the repository (replace with actual URL)
git clone <repository-url>
cd EquityWise

# Install using UV (recommended - faster and more reliable)
uv sync

# Alternative: Install using pip if UV doesn't work
pip install -e .

# Test installation
uv run equitywise --help
# OR (if using pip):
python -m equitywise --help
```

### 1.4 Troubleshooting Installation

**If you get "command not found: uv" (even after installing):**
```bash
# Most common issue: New shell session doesn't have UV path

# Fix 1: Load UV environment manually
. "$HOME/.local/bin/env"
uv --version  # Should work now

# Fix 2: Reload shell profile
source ~/.zshrc  # or ~/.bashrc for Bash users
uv --version  # Test again

# Fix 3: Use full path if UV is installed
/Users/$(whoami)/.local/bin/uv --version

# Fix 4: Install UV with pip instead
pip install uv

# Fix 5: Skip UV entirely, use pip method
pip install -e .

# Then use python -m equitywise instead of uv run equitywise
python -m equitywise --help
python -m equitywise calculate-rsu --financial-year FY24-25
```

**If you get permission errors:**
```bash
# Use --user flag
pip install --user uv
pip install --user -e .
```

### 1.5 Create Data Directory Structure

```bash
# Create data directory in the project root
mkdir -p data

# Your structure should look like:
EquityWise/
├── data/
│   ├── user_data/               # Personal financial documents
│   │   ├── BenefitHistory.xlsx
│   │   ├── G&L_Expanded_2024.xlsx
│   │   ├── G&L_Expanded_2025.xlsx
│   │   ├── RSU_FY-24-25.pdf
│   │   └── BankStatement_FY24-25.xls (optional)
│   └── reference_data/          # Historic data (regularly updated)
│       ├── Exchange_Reference_Rates.csv
│       └── HistoricalData_*.csv
├── output/ (created automatically)
└── ...
```

### 1.6 Verify Installation

```bash
# Test the tool is working
uv run equitywise --help

# You should see the main help menu with all available commands
```

---

## 🎓 **Step 2: First-Time Setup - Data Validation**

Before running calculations, validate that your data files are correct:

```bash
# Validate all data files
uv run equitywise validate-data

# Expected output:
# ✅ BenefitHistory.xlsx: 178 records validated successfully
# ✅ GainLoss_2024.xlsx: 11 records validated successfully  
# ✅ SBI_TTBR_Rates.xlsx: 342 rates validated successfully
# ✅ HistoricalData.xlsx: 2,515 stock records validated successfully
```

### Troubleshooting Data Validation

**If you see errors:**

```bash
# Get detailed validation info
uv run equitywise --log-level DEBUG validate-data

# Check specific file types
uv run equitywise validate-data --file-type benefit-history
uv run equitywise validate-data --file-type gl-statements
```

**Common Issues & Solutions:**

| Error | Solution |
|-------|----------|
| `FileNotFoundError: BenefitHistory.xlsx` | Ensure file is in `data/user_data/` directory with exact name |
| `ValidationError: Invalid date format` | Check Excel date columns are formatted as dates |
| `No exchange rate data found` | Verify SBI_TTBR_Rates.xlsx has data for your date range |

---

## 🧮 **Step 3: RSU Tax Calculations**

### 3.1 Interactive Mode (Recommended for Beginners)

```bash
# Start interactive mode
uv run equitywise

# Follow the guided prompts:
# 1. Choose "RSU Tax Calculation"
# 2. Select financial year (e.g., FY24-25)
# 3. Choose output format (Excel recommended)
# 4. Review and confirm settings
```

### 3.2 Command Line Mode (For Advanced Users)

```bash
# Calculate RSU taxes for FY 2024-25
uv run equitywise calculate-rsu \
  --financial-year FY24-25 \
  --output-format excel \
  --detailed

# Calculate for specific date range
uv run equitywise calculate-rsu \
  --financial-year FY24-25 \
  --start-date 2024-04-01 \
  --end-date 2025-03-31 \
  --output-format both
```

### 3.3 Understanding RSU & ESPP Output

**Console Output Example:**
```
🎯 RSU Calculation Summary for FY 2024-25
==========================================
📊 Vesting Summary (includes both RSU and ESPP):
   • Total Vested: 25.0 shares
   • Total Value: ₹15,07,011.83
   • Taxable Income: ₹15,07,011.83

💰 Sales Summary:
   • Total Sold: 15.0 shares  
   • Sale Proceeds: ₹9,57,543.21
   • Cost Basis: ₹6,89,652.76
   • Capital Gains: ₹2,67,890.45

📈 Capital Gains Breakdown:
   • Short-term: ₹89,234.12 (< 24 months)
   • Long-term: ₹1,78,656.33 (> 24 months)

🏦 Bank Transfers:
   • Total Received: ₹9,45,231.19
   • Transfer Expenses: ₹12,312.02
   • Net Received: ₹9,32,919.17
```

**Excel Report Sheets:**
1. **Summary**: High-level totals for tax filing
2. **Vesting Events**: Detailed vesting history with taxable income
3. **Sale Events**: Capital gains calculations with holding periods  
4. **Bank Reconciliation**: Transfer tracking and expense analysis

---

## 🌍 **Step 4: Foreign Assets Calculations**

### 4.1 Quick FA Declaration Check

```bash
# Check if FA declaration is required for 2024
uv run equitywise calculate-fa \
  --calendar-year 2024 \
  --check-only

# Output will show:
# ⚖️ Declaration Required: ✅ YES (Peak balance ₹4,33,160 > ₹2,00,000)
# OR
# ⚖️ Declaration Required: ❌ NO (Peak balance ₹1,85,000 < ₹2,00,000)
```

### 4.2 Full FA Calculation

```bash
# Generate complete FA report
uv run equitywise calculate-fa \
  --calendar-year 2024 \
  --as-of-date 2024-12-31 \
  --output-format excel \
  --detailed
```

### 4.3 Understanding FA Output

**Console Output Example:**
```
🌍 Foreign Assets Summary for CY 2024
=====================================
📊 Balance Analysis:
   • Opening (Jan 1): ₹2,46,888.96 (6.0 shares)
   • Peak (May 31): ₹4,33,160.00 (10.0 shares)  
   • Closing (Dec 31): ₹4,23,455.76 (9.0 shares)

⚖️ Declaration Status:
   • Declaration Required: ✅ YES
   • Threshold: ₹2,00,000
   • Peak Balance: ₹4,33,160.00

🗓️ Key Dates:
   • Peak Date: May 31, 2024
   • Peak Stock Price: $520.00
   • Peak Exchange Rate: ₹83.30
```

**Excel Report Sheets:**
1. **FA Summary**: Declaration requirement and key balances
2. **Equity Holdings**: Detailed holdings with cost basis
3. **Vest-wise Details**: Individual vesting event tracking
4. **Balance Timeline**: Monthly balance progression

### 4.4 FA CSV Export for Tax Forms

Generate CSV files ready for direct import into FA declaration forms:

```bash
# Generate FA CSV for direct import into tax declaration forms
uv run equitywise calculate-fa \
  --calendar-year 2024 \
  --output-format csv \
  --export-fa-csv

# Output will show:
# ✅ FA Declaration CSV created: output/FA_Declaration_2024.csv
# 📊 20 vest-wise entries ready for import
# 💰 Total closing value: ₹5,71,12,239
```

**CSV Features:**
- **Ready-to-import format**: Matches standard FA declaration form templates
- **ITR Portal Compatible**: Formatted specifically for Indian Income Tax filing
- **Vest-wise entries**: Each vesting event tracked separately

**ITR Portal Format Compliance:**
- ✅ **Country Codes**: Uses numeric codes (USA = "2") for both country columns
- ✅ **Clean Address**: No quotes or commas in address field for portal compatibility
- ✅ **Integer Currency**: All amounts rounded to whole numbers (no decimals)
- ✅ **Date Format**: DD-MM-YYYY format as required by ITR portal
- **Pre-filled entity data**: Adobe Inc. details automatically included
- **Comprehensive values**: Initial, peak, closing, and sale proceeds for each vest

---

## 📊 **Step 5: Advanced Usage Scenarios**

### 5.1 Multi-Year Analysis

```bash
# Calculate RSU for multiple financial years
for fy in FY22-23 FY23-24 FY24-25; do
  uv run equitywise calculate-rsu \
    --financial-year $fy \
    --output-format excel
done

# Calculate FA for multiple calendar years  
for cy in 2022 2023 2024; do
  uv run equitywise calculate-fa \
    --calendar-year $cy \
    --output-format excel
done
```

### 5.2 Custom Output Locations

```bash
# Specify custom output directory
uv run equitywise calculate-rsu \
  --financial-year FY24-25 \
  --output-format excel \
  --output-dir "reports/tax_year_2024"

# The reports will be saved in:
# reports/tax_year_2024/RSU_Report_FY24-25_YYYYMMDD_HHMMSS.xlsx
```

### 5.3 Batch Processing with Scripts

Create a shell script for regular reporting:

```bash
#!/bin/bash
# File: generate_reports.sh

echo "🚀 Generating RSU FA Reports..."

# Set financial year and calendar year
FY="FY24-25"
CY="2024"
OUTPUT_DIR="reports/$(date +%Y%m%d)"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate RSU report
echo "📊 Generating RSU Report for $FY..."
uv run equitywise calculate-rsu \
  --financial-year "$FY" \
  --output-format excel \
  --output-dir "$OUTPUT_DIR" \
  --detailed

# Generate FA report
echo "🌍 Generating FA Report for $CY..."
uv run equitywise calculate-fa \
  --calendar-year "$CY" \
  --output-format excel \
  --output-dir "$OUTPUT_DIR" \
  --detailed

echo "✅ Reports generated in: $OUTPUT_DIR"
```

---

## 🔧 **Step 6: Customization & Configuration**

### 6.1 Create Custom Configuration

Create `config/settings.toml`:

```toml
[data_paths]
benefit_history_path = "data/user_data/BenefitHistory.xlsx"
gl_statements_paths = [
    "data/user_data/G&L_Expanded_2023.xlsx",
    "data/user_data/G&L_Expanded_2024.xlsx", 
    "data/user_data/G&L_Expanded_2025.xlsx"
]
sbi_rates_path = "data/reference_data/Exchange_Reference_Rates.csv"
adobe_stock_path = "data/reference_data/HistoricalData_*.csv"
bank_statement_path = "data/user_data/BankStatement_FY24-25.xls"

[calculation_settings]
fa_declaration_threshold_inr = 200000.0
fallback_days_exchange_rate = 7
fallback_days_stock_price = 15

[output_settings]
output_dir = "output"
excel_formatting = true
include_bank_reconciliation = true
```

### 6.2 Environment Variable Overrides

```bash
# Override file paths
export RSU_BENEFIT_HISTORY_PATH="/custom/path/user_data/BenefitHistory.xlsx"
export RSU_OUTPUT_DIR="/custom/output/directory"
export RSU_LOG_LEVEL="DEBUG"

# Run with custom settings
uv run equitywise calculate-rsu --financial-year FY24-25
```

---

## 🎯 **Step 7: Tax Filing Integration**

### 7.1 RSU Tax Filing (ITR-2)

**For Vesting Events (Salary Income):**
1. Open your Excel RSU report → "Vesting Events" sheet
2. Sum the "Taxable Gain INR" column
3. Report this amount in ITR-2 → Income from Salary → Other Allowances

**For Sale Events (Capital Gains):**
1. Open your Excel RSU report → "Sale Events" sheet  
2. Sum short-term gains → Report in ITR-2 → Capital Gains → Short Term
3. Sum long-term gains → Report in ITR-2 → Capital Gains → Long Term

### 7.2 Foreign Assets Declaration (ITR-2 Schedule FA)

**If FA declaration is required:**
1. Open your Excel FA report → "FA Summary" sheet
2. Use the following fields in ITR-2 Schedule FA:
   - **Opening Balance**: Copy from "Opening Balance INR" 
   - **Peak Balance**: Copy from "Peak Balance INR"
   - **Closing Balance**: Copy from "Closing Balance INR"
   - **Peak Date**: Copy from "Peak Balance Date"

### 7.3 Document Retention

**Keep these files for audit purposes:**
- All generated Excel/CSV reports
- Original E*Trade files (BenefitHistory.xlsx, GainLoss files)
- Bank statements showing RSU proceeds
- Screenshots of exchange rates used

---

## 🚨 **Troubleshooting Common Issues**

### Issue 1: Missing Exchange Rates

**Problem:** `No exchange rate found for date YYYY-MM-DD`

**Solution:**
```bash
# Check available date range in SBI rates
uv run equitywise --log-level DEBUG validate-data

# The tool uses 7-day fallback, so ensure rates are within 7 days
# Download additional SBI TTBR data if needed
```

### Issue 2: Stock Price Gaps

**Problem:** `No stock price found for date YYYY-MM-DD`

**Solution:**
```bash
# Check Adobe stock data coverage
uv run equitywise --log-level DEBUG validate-data

# Download more comprehensive historical data from Yahoo Finance
# Ensure data covers all your vesting and sale dates
```

### Issue 3: Calculation Discrepancies

**Problem:** Results don't match manual calculations

**Solution:**
```bash
# Run with debug logging for detailed calculations
export RSU_LOG_LEVEL="DEBUG"
uv run equitywise calculate-rsu --financial-year FY24-25

# Check the logs for step-by-step calculation details
# Verify exchange rates and stock prices match your sources
```

### Issue 4: Excel Report Not Opening

**Problem:** Generated Excel file is corrupted

**Solution:**
```bash
# Try CSV format first to verify data
uv run equitywise calculate-rsu \
  --financial-year FY24-25 \
  --output-format csv

# If CSV works, then re-try Excel format
# Check Excel version compatibility (requires Excel 2010+)
```

---

## 📞 **Getting Help**

### Built-in Help System

```bash
# Comprehensive help guide
uv run equitywise help-guide

# Command-specific help
uv run equitywise calculate-rsu --help
uv run equitywise calculate-fa --help

# Check version and system info
uv run equitywise --version
```

### Debug Information

```bash
# Generate debug report
export RSU_LOG_LEVEL="DEBUG"
uv run equitywise --log-level DEBUG validate-data > debug_output.txt 2>&1

# Include debug_output.txt when reporting issues
```

### Common Support Scenarios

**Before reaching out for help, try:**

1. ✅ Run `uv run equitywise --log-level DEBUG validate-data`
2. ✅ Check all required files are present and named correctly
3. ✅ Verify date ranges in your data files cover calculation periods
4. ✅ Try both Excel and CSV output formats
5. ✅ Test with a single year calculation first

---

## 🎉 **Congratulations!**

You now have comprehensive knowledge of the RSU FA Tool! With this guide, you should be able to:

- ✅ **Generate accurate RSU tax calculations** for any financial year
- ✅ **Determine Foreign Assets declaration requirements** for any calendar year  
- ✅ **Create professional reports** suitable for tax filing and audit
- ✅ **Troubleshoot common issues** and customize the tool for your needs
- ✅ **Integrate results** into your ITR-2 tax filing process

**Remember:** This tool provides calculations for reference. Always consult with a qualified tax professional for complex scenarios or if you're unsure about any tax implications.

---

**📧 Questions or Issues?** 
Open an issue on GitHub with your debug output and specific error details.

**🙏 Found this helpful?** 
Consider contributing improvements or sharing with fellow Adobe employees!

---

*Happy Tax Filing! 🎯*
