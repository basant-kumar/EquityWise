import importlib.util
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "update_reference_data.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "equitywise_reference_data_updater",
    SCRIPT_PATH,
)
assert MODULE_SPEC and MODULE_SPEC.loader
updater = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(updater)


class FakeResponse:
    def __init__(self, *, content=b"", json_data=None):
        self.content = content
        self._json_data = json_data

    def raise_for_status(self):
        return None

    def json(self):
        return self._json_data


def test_stock_and_sbi_updates_use_their_expected_sources(tmp_path, monkeypatch):
    stock_dir = tmp_path / "adobe_stock"
    exchange_dir = tmp_path / "exchange_rates"
    stock_dir.mkdir()
    exchange_dir.mkdir()
    stock_file = stock_dir / "HistoricalData_test.csv"
    stock_file.write_text(
        "Date,Close/Last,Volume,Open,High,Low\n"
        "07/10/2026,$223.64,3206100,$226.50,$228.40,$222.82\n",
        encoding="utf-8",
    )

    sbi_payload = (
        b"DATE,PDF FILE,TT BUY,TT SELL\r\n"
        b"2026-07-17 09:07,https://example.test/sbi.pdf,95.90,96.75\r\n"
    )
    normalized_sbi_payload = sbi_payload.replace(b"\r\n", b"\n")
    prior_session_timestamp = int(
        datetime(2026, 7, 10, 13, 30, tzinfo=timezone.utc).timestamp()
    )
    yahoo_timestamp = int(
        datetime(2026, 7, 13, 13, 30, tzinfo=timezone.utc).timestamp()
    )
    yahoo_payload = {
        "chart": {
            "error": None,
            "result": [{
                # Yahoo can include the prior session even though period1 is
                # later; the updater must not prepend that duplicate.
                "timestamp": [prior_session_timestamp, yahoo_timestamp],
                "indicators": {"quote": [{
                    "close": [223.64, 225.50],
                    "volume": [3206100, 1234567],
                    "open": [226.50, 220.00],
                    "high": [228.40, 227.00],
                    "low": [222.82, 219.50],
                }]},
            }],
        }
    }
    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        if url == updater.YAHOO_CHART_URL:
            return FakeResponse(json_data=yahoo_payload)
        if url == updater.SBI_TTBR_ARCHIVE_URL:
            return FakeResponse(content=sbi_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(updater, "STOCK_DIR", stock_dir)
    monkeypatch.setattr(updater, "EXCHANGE_DIR", exchange_dir)
    monkeypatch.setattr(updater.requests, "get", fake_get)

    assert updater.update_stock_data()
    assert updater.update_exchange_rates()

    assert requested_urls == [
        updater.YAHOO_CHART_URL,
        updater.SBI_TTBR_ARCHIVE_URL,
    ]
    assert stock_file.read_text(encoding="utf-8").splitlines()[1] == (
        "07/13/2026,$225.50,1234567,$220.00,$227.00,$219.50"
    )
    assert (
        exchange_dir / "SBI_REFERENCE_RATES_USD.csv"
    ).read_bytes() == normalized_sbi_payload


def test_invalid_sbi_download_does_not_overwrite_existing_file(
    tmp_path, monkeypatch
):
    exchange_dir = tmp_path / "exchange_rates"
    exchange_dir.mkdir()
    exchange_file = exchange_dir / "SBI_REFERENCE_RATES_USD.csv"
    original = b"DATE,PDF FILE,TT BUY\n2025-04-30,card.pdf,84.25\n"
    exchange_file.write_bytes(original)

    monkeypatch.setattr(updater, "EXCHANGE_DIR", exchange_dir)
    monkeypatch.setattr(
        updater.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(content=b"not,a,valid,archive\n"),
    )

    assert not updater.update_exchange_rates()
    assert exchange_file.read_bytes() == original
