# Reference Data Directory

This directory contains **publicly available market data** that's safe to version control. This data is used for accurate currency conversion and stock price calculations.

## 📁 Folder Structure

### 💱 `exchange_rates/`
**USD-INR Currency Exchange Rates**

#### 📄 Files
- **`SBI_REFERENCE_RATES_USD.csv`** - Historical SBI USD/INR TT buying rates

#### 🔄 Data Sources
- **SBI TTBR archive** - SBI-published forex rate cards mirrored with PDF links

#### 📊 CSV Format
```csv
DATE,PDF FILE,TT BUY,TT SELL,BILL BUY,BILL SELL,...
2025-04-30 13:59,https://github.com/.../2025-04-30.pdf,84.25,85.10,...
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
uv run python scripts/update_reference_data.py
```

The script updates ADBE prices from Yahoo Finance and refreshes the SBI TTBR
archive. It never fills SBI gaps with generic market rates.

### 📊 **Data Quality**
- **Date ranges**: Ensure coverage for all your RSU transaction periods
- **Format consistency**: Maintained automatically by the update script
- **Rate accuracy**: Uses Yahoo Finance stock data and archived SBI-published TT BUY cards

---

## 🚀 Quick Reference

### 📅 **Important Date Ranges to Cover**
- Your first RSU vesting date → Present
- All calendar years with Foreign Asset holdings
- Peak stock price periods (for accurate valuations)

### 🔍 **Data Validation**
```bash
# Check date coverage
head -5 exchange_rates/SBI_REFERENCE_RATES_USD.csv
tail -5 exchange_rates/SBI_REFERENCE_RATES_USD.csv

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
