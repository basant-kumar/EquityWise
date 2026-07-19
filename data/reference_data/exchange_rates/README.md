# SBI TT buying rates

`SBI_REFERENCE_RATES_USD.csv` contains historical USD/INR `TT BUY` values and a
link to the archived SBI rate-card PDF for each observation. Data is mirrored
from the MIT-licensed
[SBI FX RateKeeper](https://github.com/sahilgupta/sbi-fx-ratekeeper) project,
which archives SBI-published rate cards.

Do not substitute FBIL, RBI, generic market, or bank conversion rates in this
file and label them SBI TTBR. The bank's actual conversion rate belongs in the
bank statement and is handled separately during reconciliation.

Refresh the archive and stock data from the project root:

```bash
uv run python scripts/update_reference_data.py
```

SBI does not publish every calendar day. EquityWise uses its limited
nearby-date fallback when the required day is a weekend or bank holiday.
