# Foreign-asset capital gains

EquityWise supports two USD-to-INR calculation methods. The selected method is
applied per sale lot. `inr-components` is the default.

## SBI TTBR dates

Rule 115 expressly sets the specified date for capital gains as the last day of
the month immediately preceding the transfer month. If SBI did not publish a
card that day because of a weekend or holiday, EquityWise uses the latest SBI
observation on or before that date within seven days.

For the configurable `inr-components` interpretation, EquityWise applies the
same preceding-month convention to the acquisition/vest date. The
`usd-gain-conversion` method uses only the sale specified-date rate. Confirm the
selected interpretation with your tax adviser.

## Method 1: `inr-components` (default)

```text
Sale proceeds INR = gross proceeds USD × sale SBI TTBR
Cost basis INR = adjusted cost basis USD × acquisition SBI TTBR
Selling expense INR = selling expense USD × sale SBI TTBR

Capital gain/loss INR
  = Sale proceeds INR − Cost basis INR − Selling expense INR
```

This method can produce an INR gain while the broker shows a USD loss, or the
reverse, because the acquisition and sale components use different rates.

## Method 2: `usd-gain-conversion`

```text
Net gain/loss USD
  = gross proceeds USD − adjusted cost basis USD − selling expense USD

Capital gain/loss INR = net gain/loss USD × sale SBI TTBR
```

This preserves the earlier EquityWise behavior. In the detailed report, both
sale proceeds and cost basis use the sale SBI TTBR so their INR difference
agrees with the converted net USD gain/loss.

## Configuration

Set the method for one command by placing this global option before the command:

```bash
uv run equitywise --capital-gains-method inr-components generate-reports --financial-year FY25-26
uv run equitywise --capital-gains-method usd-gain-conversion generate-reports --financial-year FY25-26
```

Or set it in `.env` for every run:

```dotenv
RSU_FA_CAPITAL_GAINS_CALCULATION_METHOD=inr-components
```

Allowed values are `inr-components` and `usd-gain-conversion`.

## Bank conversion and selling expense

The G&L statement supplies gross USD proceeds. When a matched bank remittance
shows a lower USD amount, EquityWise treats the supported difference as selling
expense and allocates it across that sale date's lots.

For tax calculation, that USD expense is converted with the sale Rule 115 SBI
TTBR. For bank reconciliation, the bank statement's own exchange rate is
applied to the post-expense USD amount, and the bank-reported GST is then
subtracted:

```text
Bank INR before GST = bank-remitted USD × bank exchange rate
Bank INR after GST = bank INR before GST − bank-reported GST
```

The bank rate, FX spread, GST, and bank rounding do not replace SBI TTBR in the
capital-gain formula.

## Reference-data source

The bundled CSV contains the SBI `TT BUY` observations archived by
[SBI FX RateKeeper](https://github.com/sahilgupta/sbi-fx-ratekeeper), with a
rate-card PDF link on every row. It replaces the former FBIL reference-rate
file; generic currency API rates are no longer accepted as SBI TTBR.

References: [Income-tax Rule 115](https://wmstatic-prd.incometaxindia.gov.in/web/guest/w/rule-115-2)
and [Income-tax Act section 48](https://www.incometaxindia.gov.in/w/section-48).
The two calculation interpretations are also discussed by
[Swipe](https://getswipe.in/blog/article/rule-115-of-income-tax-rules) and
[CA for NRI](https://cafornri.com/understanding-rule-115-how-foreign-income-is-converted-into-inr-for-indian-taxation/).
