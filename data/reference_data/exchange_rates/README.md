# Exchange Rates Folder

Place **USD-INR exchange rate data** here for accurate currency conversions.

## 📄 Required Files
- **`Exchange_Reference_Rates.csv`** - Historical USD-INR exchange rates

## 📊 CSV Format
```csv
Date,Currency,Rate
2024-01-01,USD,83.2500
2024-01-02,USD,83.3200
2024-01-03,USD,83.1800
```

## 🔄 Data Sources
### Recommended Sources:
- **SBI TTBR Rates** - Reserve Bank of India reference rates
- **RBI Reference Rates** - Official central bank rates
- **xe.com** - Reliable commercial rates
- **Bank rates** - For specific transaction validation

### API Sources:
- **exchangerate-api.com** - Free API with historical data
- **fixer.io** - Professional exchange rate API
- **Alpha Vantage** - Financial data with forex rates

## 📅 Required Date Range
Ensure your exchange rate data covers:
- **First RSU vesting date** → **Present day**
- All periods when you had Foreign Asset holdings
- All RSU transaction periods

## 🎯 Usage
Exchange rates are used for:
- **RSU vesting calculations** - Convert USD FMV to INR
- **Sale proceeds** - Convert USD sales to INR equivalents  
- **Foreign Assets reporting** - Monthly balance calculations
- **Tax compliance** - Accurate INR valuations

## 🔄 Updating Data

### Automated (Recommended):
```bash
# From the project root
.venv/bin/python scripts/update_reference_data.py
```
This fetches missing USD-INR rates from the free fawazahmed0/currency-api and prepends them to the existing CSV.

---
💡 **Tip**: Keep this data updated regularly. Missing exchange rates will cause calculation errors or require manual fallback rates!
