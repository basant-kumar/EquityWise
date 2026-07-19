#!/usr/bin/env python3
"""
Fetch Adobe stock (ADBE) data and the historical SBI USD TT buying-rate
archive used by EquityWise.

Usage:
    uv run python scripts/update_reference_data.py
"""

import csv
import io
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STOCK_DIR = PROJECT_ROOT / "data" / "reference_data" / "adobe_stock"
EXCHANGE_DIR = PROJECT_ROOT / "data" / "reference_data" / "exchange_rates"
SBI_TTBR_ARCHIVE_URL = (
    "https://raw.githubusercontent.com/sahilgupta/sbi-fx-ratekeeper/"
    "main/csv_files/SBI_REFERENCE_RATES_USD.csv"
)
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/ADBE"


def get_last_stock_date(stock_file: Path) -> date:
    latest = date(2015, 1, 1)
    with open(stock_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                d = datetime.strptime(row["Date"], "%m/%d/%Y").date()
                if d > latest:
                    latest = d
            except (ValueError, KeyError):
                continue
    return latest


def fetch_adbe_prices(start_date: date, end_date: date) -> list[dict]:
    """Fetch daily ADBE OHLCV data from Yahoo's chart endpoint."""
    period_start = int(
        datetime.combine(start_date, time.min, tzinfo=timezone.utc).timestamp()
    )
    period_end = int(
        datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        ).timestamp()
    )

    try:
        response = requests.get(
            YAHOO_CHART_URL,
            params={
                "period1": period_start,
                "period2": period_end,
                "interval": "1d",
                "events": "history",
            },
            headers={"User-Agent": "EquityWise/1.1"},
            timeout=30,
        )
        response.raise_for_status()
        chart = response.json()["chart"]
        if chart.get("error"):
            raise ValueError(chart["error"])
        result = chart["result"][0]
        timestamps = result.get("timestamp") or []
        quote = result["indicators"]["quote"][0]
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Could not fetch ADBE stock data: {exc}") from exc

    prices = []
    for index, timestamp in enumerate(timestamps):
        try:
            values = {
                "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).date(),
                "close": quote["close"][index],
                "volume": quote["volume"][index],
                "open": quote["open"][index],
                "high": quote["high"][index],
                "low": quote["low"][index],
            }
        except (KeyError, IndexError, TypeError):
            continue
        if any(value is None for value in values.values()):
            continue
        if not start_date <= values["date"] <= end_date:
            continue
        prices.append(values)

    return prices


def update_stock_data():
    csv_files = sorted(STOCK_DIR.glob("HistoricalData_*.csv"))
    if not csv_files:
        print("No existing stock CSV found in", STOCK_DIR)
        return False

    stock_file = csv_files[0]
    last_date = get_last_stock_date(stock_file)
    start_date = last_date + timedelta(days=1)
    end_date = date.today()

    if start_date > end_date:
        print(f"Stock data already up to date (last: {last_date})")
        return True

    print(f"Fetching ADBE stock data from {start_date} to {end_date}...")
    try:
        prices = fetch_adbe_prices(start_date, end_date)
    except RuntimeError as exc:
        print(exc)
        return False

    if not prices:
        print("No new stock data available from Yahoo Finance")
        return True

    new_lines = []
    for row in sorted(prices, key=lambda item: item["date"], reverse=True):
        line = (
            f"{row['date'].strftime('%m/%d/%Y')},"
            f"${row['close']:.2f},"
            f"{int(row['volume'])},"
            f"${row['open']:.2f},"
            f"${row['high']:.2f},"
            f"${row['low']:.2f}"
        )
        new_lines.append(line)

    original = stock_file.read_bytes()
    header_end = original.index(b"\n") + 1
    header = original[:header_end]
    rest = original[header_end:]

    # Use LF for newly tracked rows so Git does not interpret CR characters as
    # trailing whitespace in the historical CRLF-formatted source file.
    new_block = "\n".join(new_lines).encode() + b"\n"
    stock_file.write_bytes(header + new_block + rest)

    print(f"Added {len(new_lines)} new stock records to {stock_file.name}")
    return True


def update_exchange_rates():
    """Refresh the SBI TTBR archive without substituting market/FBIL rates."""
    exchange_file = EXCHANGE_DIR / "SBI_REFERENCE_RATES_USD.csv"
    print("Fetching historical SBI USD TT buying rates...")

    try:
        response = requests.get(SBI_TTBR_ARCHIVE_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Could not fetch SBI TTBR data: {exc}")
        return False

    try:
        archive_text = response.content.decode("utf-8-sig")
        archive_text = archive_text.replace("\r\n", "\n").replace("\r", "\n")
        payload = archive_text.encode("utf-8")
        rows = list(csv.DictReader(io.StringIO(archive_text)))
        valid_rows = [
            row for row in rows
            if row.get("DATE") and float(row.get("TT BUY") or 0) > 0
        ]
    except (UnicodeDecodeError, ValueError) as exc:
        print(f"Downloaded SBI TTBR archive is invalid: {exc}")
        return False

    if not valid_rows or not {"DATE", "PDF FILE", "TT BUY"}.issubset(
        rows[0].keys() if rows else set()
    ):
        print("Downloaded file does not have the expected SBI TTBR columns")
        return False

    EXCHANGE_DIR.mkdir(parents=True, exist_ok=True)
    if exchange_file.exists() and exchange_file.read_bytes() == payload:
        print(f"SBI TTBR data already up to date ({len(valid_rows)} usable rates)")
        return True

    temporary_file = exchange_file.with_suffix(".csv.tmp")
    temporary_file.write_bytes(payload)
    temporary_file.replace(exchange_file)
    print(f"Updated {exchange_file.name} with {len(valid_rows)} usable SBI TTBR rates")
    return True


def main():
    print("=" * 60)
    print("EquityWise Reference Data Updater")
    print("=" * 60)
    print()

    stock_ok = update_stock_data()
    print()
    exchange_ok = update_exchange_rates()
    print()

    if stock_ok and exchange_ok:
        print("All reference data updated successfully.")
    else:
        print("Some updates failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
