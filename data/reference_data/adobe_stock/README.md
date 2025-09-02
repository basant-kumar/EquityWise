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
### Manual Download:
1. Go to **Yahoo Finance** → Search "ADBE"
2. Click **Historical Data** tab
3. Set date range and frequency (Daily)
4. **Download CSV** file
5. Save as `HistoricalData_YYYYMMDD.csv`

### API Example:
```bash
# Alpha Vantage API (free tier)
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=ADBE&outputsize=full&apikey=YOUR_KEY&datatype=csv" -o adobe_stock/HistoricalData_latest.csv

# Yahoo Finance (unofficial)
wget "https://query1.finance.yahoo.com/v7/finance/download/ADBE?period1=START_DATE&period2=END_DATE&interval=1d&events=history" -O adobe_stock/HistoricalData_latest.csv
```

## 📊 Data Quality Tips
- **Daily frequency** recommended for accurate calculations
- **Adjust for stock splits** - ensure historical prices are split-adjusted
- **Include recent data** - keep current for up-to-date valuations
- **Validate dates** - ensure no gaps during your RSU periods

---
💡 **Tip**: Stock price data is crucial for accurate Foreign Asset calculations. Missing prices on specific dates can affect balance calculations!
