# User Data Directory

This directory contains your personal financial data files organized into logical subfolders. **⚠️ Never commit these files to version control** - they contain sensitive financial information.

## 📁 Folder Structure

### 🏛️ `benefit_history/`
**E*Trade Benefit History Files**
- **`BenefitHistory.xlsx`** - Complete RSU transaction history from E*Trade

**How to Download:**
1. Login to **E*Trade → At Work → My Account**
2. Go to **Benefit History → Download Expanded**
3. Save as `BenefitHistory.xlsx` in this folder

---

### 📊 `gl_statements/`
**Gain & Loss Statements from E*Trade**
- **`G&L_Expanded_YYYY.xlsx`** - Annual gain/loss statements for each year
- Example files: `G&L_Expanded_2023.xlsx`, `G&L_Expanded_2024.xlsx`

**How to Download:**
1. Login to **E*Trade → At Work → My Account**
2. Go to **Gains & Losses → Download Expanded** (for each year)
3. Save as `G&L_Expanded_YYYY.xlsx` where YYYY is the year

---

### 📄 `rsu_documents/`
**RSU Vesting Statements from Excelity Portal**
- **`RSU_FY-YY-YY.pdf`** - Annual RSU vesting statements
- Example files: `RSU_FY-22-23.pdf`, `RSU_FY-23-24.pdf`, `RSU_FY-24-25.pdf`

**How to Download:**
1. Login to **Excelity Portal**
2. Go to **Payroll & Benefits → My reports → Stock perquisites statement**
3. **Select Financial Year → Download as PDF**
4. Save as `RSU_FY-YY-YY.pdf` format

---

### 🏦 `bank_statements/`
**Bank Statement Files for Transaction Reconciliation**
- **`BankStatement_FYXX-XX.xls`** - Annual bank statements for broker transactions
- Example files: `BankStatement_FY23-24.xls`, `BankStatement_FY24-25.xls`

**How to Add:**
1. Export bank statements covering your RSU sale periods
2. Save as `BankStatement_FYXX-XX.xls` format
3. Place in this folder for transaction reconciliation

---

## 🔒 Security & Privacy

- ✅ **Tracked**: Only README files
- ❌ **Ignored**: All financial data files (`.xlsx`, `.xls`, `.pdf`)
- 🔐 **Private**: Your sensitive financial information stays local

## 📝 File Naming Conventions

- **RSU PDFs**: `RSU_FY-YY-YY.pdf` (Financial Year format)
- **G&L Statements**: `G&L_Expanded_YYYY.xlsx` (Calendar Year format)
- **Benefit History**: `BenefitHistory.xlsx` (Latest comprehensive data)
- **Bank Statements**: `BankStatement_FYXX-XX.xls` (Financial Year format)

## 🎯 Next Steps

1. **Download your RSU statements** from Excelity portal (most important)
2. **Download G&L statements** from E*Trade for all relevant years
3. **Download Benefit History** from E*Trade (comprehensive transaction data)
4. **Add bank statements** if you need transaction reconciliation
5. **Run calculations**: `uv run equitywise calculate-rsu` or `calculate-fa`

---

💡 **Tip**: The application automatically detects all files in these subfolders, so you can add multiple years of data and the system will process them all.