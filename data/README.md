# Data Files Directory

This directory is organized into two main categories for better structure and maintainability:

## 📁 Folder Structure

```
data/
├── reference_data/     # Historic and reference data (regularly updated)
└── user_data/         # Personal financial documents (user-specific)
```

## 🗂️ Reference Data (`reference_data/`)

Historic and reference data that needs regular updates:

- `Exchange_Reference_Rates.csv` - SBI TTBR exchange rates (update regularly)
- `HistoricalData_*.csv` - Adobe stock historical price data (update as needed)

### Update Schedule
- **Exchange rates**: Update monthly or as needed for accurate currency conversions
- **Stock data**: Update periodically for current market valuations

## 👤 User Data (`user_data/`)

Personal financial documents specific to your accounts:

### Required Files:

**From E*Trade:**
- `BenefitHistory.xlsx` - RSU vesting transaction history
  - Login to **E*Trade** → **At Work** → **My Account** → **Benefit History** → **Download Expanded**
- `G&L_Expanded_YYYY.xlsx` - Sale transaction records for each year (2023, 2024, 2025)
  - Login to **E*Trade** → **At Work** → **My Account** → **Gains & Losses** → **Download Expanded**

**From Excelity Portal:**
- `RSU_FY-YY-YY.pdf` - RSU vesting statements 
  - Login to **Excelity Portal** → **Payroll & Benefits** → **My Reports** → **Stock Perquisites Statement** → Select **Financial Year** → **Download as PDF**

**From Bank:**
- `BankStatement_FY*-*.xls` - Bank statements for reconciliation

### File Naming Convention:
- G&L statements: `G&L_Expanded_2024.xlsx`
- RSU documents: `RSU_FY-24-25.pdf`
- Bank statements: `BankStatement_FY24-25.xls`

## 🔒 Privacy & Security

📁 This entire directory is ignored by git (.gitignore) to protect your private financial data.

## ⚙️ Configuration Update Required

⚠️ **Important**: You need to update the company and depository account information in:
`src/equitywise/data/models.py` - `create_default_company_records()` function

Replace the placeholder values with your actual:
- Employer company details (name, TAN, address)
- Foreign company details (name, address, country)  
- Depository account details (institution, account number, dates)

This information is required for accurate Foreign Assets (FA) reporting.

## 📋 Usage Notes

1. **Adding New Files**: Place new user documents in `user_data/` and reference data in `reference_data/`
2. **Updates**: Regularly update exchange rates and stock data in `reference_data/`
3. **Backups**: Consider backing up `user_data/` separately as it contains irreplaceable financial records
4. **File Types**: The application supports Excel (.xlsx, .xls), CSV (.csv), and PDF (.pdf) formats