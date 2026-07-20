"""Hand-verified golden tests for the three calculators (RSU, ESPP, FA).

Every expected number below is computed BY HAND from the documented formulas in
the calculator source, using tiny, controlled inputs. Rate/stock lookups that
depend on reference data are monkeypatched to fixed values so that each test
isolates one calculation formula. If a formula changes, these tests must be
re-derived by hand -- that is the point of a golden test.
"""

from datetime import date as Date

import pytest

from equitywise.calculators.rsu_calculator import (
    RSUCalculator,
    VestingEvent,
    SaleEvent,
    INR_COMPONENTS_METHOD,
)
from equitywise.calculators.fa_calculator import FACalculator
from equitywise.data.rsu_parser import RSUVestingRecord
from equitywise.data.models import GLStatementRecord


# --------------------------------------------------------------------------
# Shared fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def rsu_calc():
    """RSU calculator with empty reference data (default INR-components method)."""
    return RSUCalculator(sbi_rates=[], stock_data=[])


@pytest.fixture
def fa_calc():
    return FACalculator(sbi_rates=[], stock_data=[])


# ==========================================================================
# 1. RSU VESTING  (pure formula, no rate lookups)
#    vest_fmv_inr   = fmv_usd * forex_rate
#    taxable_gain_* = pass-through of total_usd / total_inr from the PDF
#    financial_year = Indian FY (Apr-Mar) of the vest date
# ==========================================================================
def test_rsu_vesting_golden(rsu_calc):
    record = RSUVestingRecord(
        grant_number="G1",
        quantity=100.0,
        vesting_date=Date(2024, 6, 15),   # month >= 4  -> FY24-25
        fmv_usd=500.0,
        total_usd=50_000.0,
        forex_rate=83.0,
        total_inr=4_150_000.0,
        wh_quantity=30.0,
    )

    events = rsu_calc.process_rsu_vesting_events([record])

    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, VestingEvent)
    assert ev.vested_quantity == 100.0
    assert ev.vest_fmv_usd == 500.0
    # 500.00 * 83.00 = 41500.00  (hand-computed)
    assert ev.vest_fmv_inr == pytest.approx(41_500.0)
    assert ev.exchange_rate == 83.0
    # taxable gains pass straight through from the RSU PDF
    assert ev.taxable_gain_usd == pytest.approx(50_000.0)
    assert ev.taxable_gain_inr == pytest.approx(4_150_000.0)
    assert ev.withheld_quantity == 30.0
    assert ev.financial_year == "FY24-25"


# ==========================================================================
# 2. ESPP PURCHASE  (same vesting path; grant_type="ESPP", vest date = purchase)
#    An ESPP purchase flows through process_rsu_vesting_events identically:
#    the discount is already baked into total_inr by the parser, so the
#    calculator only converts FMV: vest_fmv_inr = fmv_usd * forex_rate.
# ==========================================================================
def test_espp_purchase_golden(rsu_calc):
    record = RSUVestingRecord(
        grant_number="ESPP1",
        grant_type="ESPP",
        quantity=50.0,
        vesting_date=Date(2024, 9, 30),   # purchase date, month 9 -> FY24-25
        fmv_usd=400.0,
        total_usd=20_000.0,
        forex_rate=82.0,
        total_inr=1_640_000.0,
        grant_price_usd=340.0,            # 15% discount purchase price
    )

    events = rsu_calc.process_rsu_vesting_events([record])

    assert len(events) == 1
    ev = events[0]
    # 400.00 * 82.00 = 32800.00  (hand-computed)
    assert ev.vest_fmv_inr == pytest.approx(32_800.0)
    assert ev.vested_quantity == 50.0
    assert ev.taxable_gain_usd == pytest.approx(20_000.0)
    assert ev.taxable_gain_inr == pytest.approx(1_640_000.0)
    assert ev.financial_year == "FY24-25"


# ==========================================================================
# 3. RSU SALE  (INR-components method = the default)
#    cost_basis_inr    = cost_basis_usd * acquisition_rate
#    sale_proceeds_inr = sale_proceeds_usd * sale_rate
#    capital_gain_inr  = sale_proceeds_inr - cost_basis_inr
#    gain_type         = Long-term if sold > acquired + 2 years
# ==========================================================================
def test_rsu_sale_golden_inr_components(rsu_calc, monkeypatch):
    # Fixed Rule-115 rates: 84 on sale date, 80 on acquisition date.
    def fake_rule_115(event_date):
        return 84.0 if event_date == Date(2024, 3, 20) else 80.0

    monkeypatch.setattr(rsu_calc, "get_rule_115_exchange_rate", fake_rule_115)
    # No prior vesting details -> else branch derives cost basis per share.
    monkeypatch.setattr(rsu_calc, "get_vesting_details", lambda *a, **k: None)
    monkeypatch.setattr(rsu_calc, "get_exchange_rate", lambda *a, **k: 80.0)

    record = GLStatementRecord(
        record_type="Sell",
        quantity=10.0,
        date_acquired=Date(2022, 1, 10),
        date_sold=Date(2024, 3, 20),      # > 2022-01-10 + 2y -> Long-term
        adjusted_cost_basis=3_000.0,
        total_proceeds=5_000.0,
        proceeds_per_share=500.0,
        adjusted_gain_loss=2_000.0,
        grant_number="G1",
    )

    events = rsu_calc.process_sale_events([record])

    assert len(events) == 1
    se = events[0]
    assert isinstance(se, SaleEvent)
    assert se.calculation_method == INR_COMPONENTS_METHOD
    assert se.quantity_sold == 10.0
    assert se.sale_proceeds_usd == pytest.approx(5_000.0)
    # 5000 * 84 = 420000
    assert se.sale_proceeds_inr == pytest.approx(420_000.0)
    assert se.cost_basis_usd == pytest.approx(3_000.0)
    # 3000 * 80 (acquisition rate) = 240000
    assert se.cost_basis_inr == pytest.approx(240_000.0)
    assert se.capital_gain_usd == pytest.approx(2_000.0)
    # 420000 - 240000 = 180000
    assert se.capital_gain_inr == pytest.approx(180_000.0)
    assert se.exchange_rate_sale == 84.0
    assert se.acquisition_exchange_rate == 80.0
    assert se.cost_basis_exchange_rate == 80.0
    assert se.gain_type == "Long-term"
    # sold 2024-03-20 (Jan-Mar) -> FY23-24
    assert se.financial_year == "FY23-24"


# ==========================================================================
# 4. FA SUMMARY selection  (opening / closing / peak picked from balances)
#    opening = FIRST balance whose date.year <= calendar_year (sorted keys)
#    closing = the "{year}-12-31" balance
#    peak    = balance with the maximum vested_value_inr
# ==========================================================================
def test_fa_summary_selection_golden(fa_calc, monkeypatch):
    balances = {
        "2025-03-31": {  # earliest key -> OPENING
            "date": Date(2025, 3, 31),
            "vested_value_inr": 1_000_000.0,
            "total_value_usd": 12_000.0,
            "exchange_rate": 83.0,
            "stock_price": 500.0,
            "holdings_count": 2,
        },
        "2025-08-15": {  # highest vested value -> PEAK
            "date": Date(2025, 8, 15),
            "vested_value_inr": 1_500_000.0,
            "total_value_usd": 18_000.0,
            "exchange_rate": 84.0,
            "stock_price": 550.0,
            "holdings_count": 2,
        },
        "2025-12-31": {  # Dec 31 -> CLOSING
            "date": Date(2025, 12, 31),
            "vested_value_inr": 1_200_000.0,
            "total_value_usd": 15_000.0,
            "exchange_rate": 85.0,
            "stock_price": 480.0,
            "holdings_count": 2,
        },
    }

    monkeypatch.setattr(fa_calc, "calculate_year_balances", lambda *a, **k: balances)
    # Not under test here -- isolate the opening/closing/peak selection logic.
    monkeypatch.setattr(fa_calc, "calculate_vest_wise_details", lambda *a, **k: [])
    monkeypatch.setattr(
        fa_calc,
        "calculate_share_statistics",
        lambda *a, **k: {
            "total_vested_ever": 30.0,
            "total_sold_ever": 0.0,
            "total_sold_in_cl": 0.0,
            "opening_shares": 24.0,
            "current_holdings": 30.0,
            "vested_before_cl": 30.0,
            "sold_before_cl": 0.0,
        },
    )

    # A non-empty rsu_records list flips has_source_data on; content is
    # irrelevant because the two methods above are stubbed.
    dummy_rsu = RSUVestingRecord(
        grant_number="G1",
        quantity=30.0,
        vesting_date=Date(2025, 3, 31),
        fmv_usd=500.0,
        total_usd=15_000.0,
        forex_rate=83.0,
        total_inr=1_245_000.0,
    )

    # has_source_data requires rsu_records AND gl_records to both be non-None.
    summary = fa_calc.calculate_fa_summary(
        calendar_year="2025",
        equity_holdings=[],
        rsu_records=[dummy_rsu],
        gl_records=[],
    )

    # Opening = first qualifying key (2025-03-31)
    assert summary.opening_balance_inr == pytest.approx(1_000_000.0)
    assert summary.opening_exchange_rate == 83.0
    # 12000 / 500 = 24 shares
    assert summary.opening_shares == pytest.approx(24.0)

    # Closing = 2025-12-31
    assert summary.closing_balance_inr == pytest.approx(1_200_000.0)
    assert summary.year_end_exchange_rate == 85.0
    # 15000 / 480 = 31.25 shares
    assert summary.closing_shares == pytest.approx(31.25)

    # Peak = max vested_value_inr (2025-08-15)
    assert summary.peak_balance_inr == pytest.approx(1_500_000.0)
    assert summary.peak_balance_date == Date(2025, 8, 15)
    assert summary.peak_exchange_rate == 84.0
