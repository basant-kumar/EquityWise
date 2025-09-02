# Data Files Directory

Place your data files in this directory:

## Required Files:
- `BenefitHistory.xlsx` - E*Trade benefit history export
- `G&L_Expanded_YYYY.xlsx` - G&L statements for each year
- `Reference Rates.csv` - SBI TTBR rates
- `HistoricalData_*.csv` - Adobe stock historical data
- `ESOP_*.pdf` - ESOP vesting statements  
- `BankStatement_*.xls` - Bank statements for reconciliation

## File Naming Examples:
- `G&L_Expanded_2024.xlsx`
- `ESOP_FY-24-25.pdf`
- `BankStatement_FY24-25.xls`

📁 This directory is ignored by git (.gitignore) to protect your private financial data.

## Configuration Update Required

⚠️ **Important**: You need to update the company and depository account information in:
`src/rsu_fa_tool/data/models.py` - `create_default_company_records()` function

Replace the placeholder values with your actual:
- Employer company details (name, TAN, address)
- Foreign company details (name, address, country)
- Depository account details (institution, account number, dates)

This information is required for accurate Foreign Assets (FA) reporting.