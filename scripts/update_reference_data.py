#!/usr/bin/env python3
"""
Fetch missing Adobe stock (ADBE) and USD-INR exchange rate data
and prepend to the existing reference CSVs.

Usage:
    python scripts/update_reference_data.py
"""

import csv
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

import requests
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STOCK_DIR = PROJECT_ROOT / "data" / "reference_data" / "adobe_stock"
EXCHANGE_DIR = PROJECT_ROOT / "data" / "reference_data" / "exchange_rates"


def detect_line_ending(file_path: Path) -> str:
    raw = file_path.read_bytes()
    if b"\r\n" in raw:
        return "\r\n"
    return "\n"


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


def get_last_exchange_date(exchange_file: Path) -> date:
    latest = date(2018, 1, 1)
    with open(exchange_file, newline="") as f:
        for line in f:
            if "INR / 1 USD" in line:
                parts = line.split(",")
                try:
                    d = datetime.strptime(parts[0].strip(), "%d %b %Y").date()
                    if d > latest:
                        latest = d
                except ValueError:
                    continue
    return latest


def update_stock_data():
    csv_files = sorted(STOCK_DIR.glob("HistoricalData_*.csv"))
    if not csv_files:
        print("No existing stock CSV found in", STOCK_DIR)
        return False

    stock_file = csv_files[0]
    eol = detect_line_ending(stock_file)
    last_date = get_last_stock_date(stock_file)
    start_date = last_date + timedelta(days=1)
    end_date = date.today()

    if start_date > end_date:
        print(f"Stock data already up to date (last: {last_date})")
        return True

    print(f"Fetching ADBE stock data from {start_date} to {end_date}...")
    ticker = yf.Ticker("ADBE")
    df = ticker.history(start=start_date.isoformat(), end=(end_date + timedelta(days=1)).isoformat())

    if df.empty:
        print("No new stock data available from Yahoo Finance")
        return True

    new_lines = []
    for idx, row in sorted(df.iterrows(), reverse=True):
        d = idx.date() if hasattr(idx, "date") else idx
        line = (
            f"{d.strftime('%m/%d/%Y')},"
            f"${row['Close']:.2f},"
            f"{int(row['Volume'])},"
            f"${row['Open']:.2f},"
            f"${row['High']:.2f},"
            f"${row['Low']:.2f}"
        )
        new_lines.append(line)

    original = stock_file.read_bytes()
    header_end = original.index(b"\n") + 1
    header = original[:header_end]
    rest = original[header_end:]

    new_block = eol.join(new_lines).encode() + eol.encode()
    stock_file.write_bytes(header + new_block + rest)

    print(f"Added {len(new_lines)} new stock records to {stock_file.name}")
    return True


def update_exchange_rates():
    exchange_file = EXCHANGE_DIR / "Exchange_Reference_Rates.csv"
    if not exchange_file.exists():
        print("No existing exchange rate CSV found at", exchange_file)
        return False

    eol = detect_line_ending(exchange_file)
    last_date = get_last_exchange_date(exchange_file)
    start_date = last_date + timedelta(days=1)
    end_date = date.today()

    if start_date > end_date:
        print(f"Exchange rate data already up to date (last: {last_date})")
        return True

    print(f"Fetching USD-INR exchange rates from {start_date} to {end_date}...")

    new_rates = []
    d = start_date
    while d <= end_date:
        if d.weekday() < 5:
            try:
                resp = requests.get(
                    f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{d.isoformat()}/v1/currencies/usd.json",
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    inr_rate = data.get("usd", {}).get("inr")
                    if inr_rate:
                        new_rates.append((d, round(inr_rate, 4)))
            except Exception:
                pass
        d += timedelta(days=1)

    if not new_rates:
        print("Trying fallback API for exchange rates...")
        try:
            resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                inr_rate = data.get("rates", {}).get("INR")
                if inr_rate:
                    d = start_date
                    while d <= end_date:
                        if d.weekday() < 5:
                            new_rates.append((d, round(inr_rate, 4)))
                        d += timedelta(days=1)
        except Exception as e:
            print(f"Fallback API also failed: {e}")

    if not new_rates:
        print("Could not fetch any exchange rate data")
        return False

    new_lines = []
    for d, rate in sorted(new_rates, key=lambda x: x[0], reverse=True):
        new_lines.append(f"{d.strftime('%d %b %Y')},1:30:00 PM,INR / 1 USD,{rate},")

    original = exchange_file.read_bytes()
    # Find the end of the 3rd line (after the 2 header lines + column header)
    pos = 0
    for _ in range(3):
        pos = original.index(b"\n", pos) + 1
    header = original[:pos]
    rest = original[pos:]

    new_block = eol.join(new_lines).encode() + eol.encode()
    exchange_file.write_bytes(header + new_block + rest)

    print(f"Added {len(new_rates)} new USD-INR exchange rate records to {exchange_file.name}")
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
