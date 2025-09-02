# Data Directory Structure

This directory contains all data files needed for RSU and Foreign Assets calculations, organized into two main categories:

## 📁 Folder Structure

### 🔒 `user_data/` - Personal Financial Data
**Your private financial information - NEVER commit to version control**

#### 🏛️ `benefit_history/`
- **Purpose**: E*Trade comprehensive transaction history
- **Files**: `BenefitHistory.xlsx`
- **Source**: E*Trade → At Work → My Account → Benefit History → Download Expanded

#### 📊 `gl_statements/`
- **Purpose**: Annual gain/loss statements for capital gains calculations
- **Files**: `G&L_Expanded_YYYY.xlsx` (one per year)
- **Source**: E*Trade → At Work → My Account → Gains & Losses → Download Expanded

#### 📄 `rsu_documents/`
- **Purpose**: RSU vesting statements from employer
- **Files**: `RSU_FY-YY-YY.pdf` (one per financial year)
- **Source**: Excelity Portal → Payroll & Benefits → Stock perquisites statement

#### 🏦 `bank_statements/`
- **Purpose**: Bank statements for transaction reconciliation
- **Files**: `BankStatement_FYXX-XX.xls`
- **Source**: Your bank's transaction exports

---

### 🌍 `reference_data/` - Public Market Data
**Publicly available data - safe to version control**

#### 💱 `exchange_rates/`
- **Purpose**: USD-INR exchange rates for accurate currency conversion
- **Files**: `Exchange_Reference_Rates.csv`
- **Source**: SBI TTBR rates, RBI rates, or other reliable financial data sources

#### 📈 `adobe_stock/`
- **Purpose**: Adobe (ADBE) historical stock prices
- **Files**: `HistoricalData_*.csv`
- **Source**: Yahoo Finance, Google Finance, or financial data providers

---

## 🔒 Privacy & Security

### ✅ Version Controlled (Public Data)
```
data/
├── reference_data/          # Public market data
│   ├── exchange_rates/     # Currency exchange rates
│   └── adobe_stock/        # Stock price history
└── README.md               # Documentation
```

### ❌ Git Ignored (Private Data)
```
data/
└── user_data/              # Your personal financial data
    ├── benefit_history/    # E*Trade transaction history
    ├── gl_statements/      # Tax documents
    ├── rsu_documents/      # Employer RSU records
    └── bank_statements/    # Bank transaction records
```

## 📝 Quick Setup Guide

### 1️⃣ Download Your RSU Data
```bash
# From Excelity Portal
Payroll & Benefits → Stock perquisites statement → Download PDF
# Save as: data/user_data/rsu_documents/RSU_FY-YY-YY.pdf
```

### 2️⃣ Download E*Trade Data
```bash
# Benefit History (comprehensive)
E*Trade → Benefit History → Download Expanded
# Save as: data/user_data/benefit_history/BenefitHistory.xlsx

# G&L Statements (annual)
E*Trade → Gains & Losses → Download Expanded (per year)
# Save as: data/user_data/gl_statements/G&L_Expanded_YYYY.xlsx
```

### 3️⃣ Verify Setup
```bash
# Check if data is properly organized
ls data/user_data/*/
ls data/reference_data/*/
```

### 4️⃣ Run Calculations
```bash
# RSU tax calculations
uv run equitywise calculate-rsu --financial-year FY24-25

# Foreign Assets compliance
uv run equitywise calculate-fa --calendar-year 2024
```

---

## 🎯 File Organization Benefits

✅ **Clear separation** between personal vs public data  
✅ **Privacy protection** - sensitive files never tracked  
✅ **Easy navigation** - logical folder grouping  
✅ **Scalable structure** - add more years easily  
✅ **Type-based organization** - find files by purpose  

---

💡 **Pro Tip**: The application automatically scans all subfolders, so you can add multiple years of data and everything will be processed automatically!