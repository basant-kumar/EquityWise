# Adobe Stock Data Folder

Place **Adobe Inc. (ADBE) historical stock price data** here for accurate valuations.

## 📄 Required Files
- **`HistoricalData_*.csv`** - Adobe stock price history from financial data providers

## 📊 CSV Format
```csv
Date,Open,High,Low,Close,Volume
2024-01-01,580.00,585.50,578.25,582.75,1500000
2024-01-02,583.00,587.25,580.00,584.50,1750000
```

## 🔄 Data Sources
### Free Sources:
- **Yahoo Finance** - `finance.yahoo.com/quote/ADBE/history`
- **Google Finance** - Historical data downloads
- **Alpha Vantage** - Free tier with 500 calls/day
- **IEX Cloud** - Reliable financial API

### Professional Sources:
- **Bloomberg API** - Enterprise-grade data
- **Refinitiv (Reuters)** - Professional financial data
- **Quandl** - Financial and economic data

## 📅 Required Date Range
Ensure your stock data covers:
- **First RSU grant date** → **Present day**
- All periods when calculating Foreign Asset balances
- Peak price periods for accurate valuations

## 🎯 Usage
Stock prices are used for:
- **Fair Market Value** - RSU vesting date valuations
- **Foreign Assets reporting** - Opening/peak/closing balance calculations
- **Unrealized gains** - Current holding valuations
- **Tax compliance** - Accurate stock price references

## 🔄 Updating Data

### Automated (Recommended):
```bash
# From the project root
uv run python scripts/update_reference_data.py
```
This fetches missing ADBE prices from Yahoo Finance and refreshes the complete
SBI TTBR archive in the same run.

### Manual Download:
1. Go to **Yahoo Finance** → Search "ADBE"
2. Click **Historical Data** tab
3. Set date range and frequency (Daily)
4. **Download CSV** file
5. Save as `HistoricalData_YYYYMMDD.csv`

## 📊 Data Quality Tips
- **Daily frequency** recommended for accurate calculations
- **Adjust for stock splits** - ensure historical prices are split-adjusted
- **Include recent data** - keep current for up-to-date valuations
- **Validate dates** - ensure no gaps during your RSU periods

---
💡 **Tip**: Stock price data is crucial for accurate Foreign Asset calculations. Missing prices on specific dates can affect balance calculations!
