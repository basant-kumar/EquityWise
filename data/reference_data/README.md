# Reference Data Directory

This directory contains **publicly available market data** that's safe to version control. This data is used for accurate currency conversion and stock price calculations.

## 📁 Folder Structure

### 💱 `exchange_rates/`
**USD-INR Currency Exchange Rates**

#### 📄 Files
- **`Exchange_Reference_Rates.csv`** - Historical USD-INR exchange rates

#### 🔄 Data Sources
- **SBI TTBR Rates** (recommended) - Reserve Bank of India reference rates
- **RBI Reference Rates** - Official central bank rates  
- **Commercial bank rates** - For specific transaction dates

#### 📊 CSV Format
```csv
Date,Currency,Rate
2024-01-01,USD,83.2500
2024-01-02,USD,83.3200
```

#### 🔄 Update Frequency
- **Daily**: For active trading periods
- **Monthly**: For historical data gaps
- **As needed**: When processing new transactions

---

### 📈 `adobe_stock/`
**Adobe Inc. (ADBE) Stock Price History**

#### 📄 Files
- **`HistoricalData_*.csv`** - Adobe stock price history from financial data providers

#### 🔄 Data Sources
- **Yahoo Finance** - Free historical data
- **Google Finance** - Alternative free source
- **Financial APIs** - Alpha Vantage, IEX Cloud, etc.

#### 📊 CSV Format
```csv
Date,Open,High,Low,Close,Volume
2024-01-01,580.00,585.50,578.25,582.75,1500000
2024-01-02,583.00,587.25,580.00,584.50,1750000
```

#### 🔄 Update Frequency
- **Weekly**: For recent price data
- **Monthly**: For historical backlogs
- **As needed**: When processing new RSU transactions

---

## 📖 How This Data Is Used

### 🧮 **Currency Conversion**
Exchange rates convert USD amounts to INR for:
- RSU vesting values (tax calculations)
- Sale proceeds (capital gains)
- Foreign Assets reporting (compliance)

### 💰 **Stock Valuation** 
Stock prices determine:
- Fair Market Value at RSU vesting
- Peak/closing balances for Foreign Assets
- Unrealized gains for compliance reporting

---

## 🔄 Maintaining Reference Data

### ✅ **Safe to Commit**
- All files in this directory are public market data
- No personal or sensitive information
- Version control helps track data updates

### 🔄 **Automated Updates (Recommended)**

Use the included update script to fetch missing data up to the current date:

```bash
# One-time setup (if .venv doesn't exist yet)
uv venv && uv pip install yfinance requests

# Run the updater
.venv/bin/python scripts/update_reference_data.py
```

The script automatically:
- Detects the last date in each CSV
- Fetches only the missing data (no duplicates)
- Prepends new rows while preserving the original file format
- Uses **Yahoo Finance** for ADBE stock prices and **fawazahmed0/currency-api** for USD-INR rates

### 📊 **Data Quality**
- **Date ranges**: Ensure coverage for all your RSU transaction periods
- **Format consistency**: Maintained automatically by the update script
- **Rate accuracy**: Uses reliable financial data sources (Yahoo Finance, open exchange rate APIs)

---

## 🚀 Quick Reference

### 📅 **Important Date Ranges to Cover**
- Your first RSU vesting date → Present
- All calendar years with Foreign Asset holdings
- Peak stock price periods (for accurate valuations)

### 🔍 **Data Validation**
```bash
# Check date coverage
head -5 exchange_rates/Exchange_Reference_Rates.csv
tail -5 exchange_rates/Exchange_Reference_Rates.csv

# Verify stock data
head -5 adobe_stock/HistoricalData_*.csv
```

### ⚡ **Automatic Processing**
The EquityWise application automatically:
- Loads all CSV files from these subfolders
- Matches dates to your RSU transactions
- Uses fallback logic for missing data points
- Validates data quality during calculations

---

💡 **Pro Tip**: Keep this data updated regularly to ensure accurate tax calculations and compliance reporting!