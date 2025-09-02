"""Tests for Foreign Assets calculation engine."""

import pytest
from datetime import date
from typing import List

from rsu_fa_tool.calculators.fa_calculator import (
    FACalculator, EquityHolding, FADeclarationSummary, FACalculationResults
)
from rsu_fa_tool.data.models import (
    BenefitHistoryRecord, SBIRateRecord, AdobeStockRecord
)


@pytest.fixture
def sample_sbi_rates() -> List[SBIRateRecord]:
    """Sample SBI exchange rates for year-end."""
    return [
        SBIRateRecord(**{
            'Date': date(2023, 12, 29),  # Last business day 2023
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD',
            'Rate': 83.25
        }),
        SBIRateRecord(**{
            'Date': date(2024, 12, 30),  # Last business day 2024
            'Time': '1:00:00 PM', 
            'Currency Pairs': 'INR / 1 USD',
            'Rate': 83.50
        }),
        SBIRateRecord(**{
            'Date': date(2024, 6, 15),
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD', 
            'Rate': 83.40
        })
    ]


@pytest.fixture
def sample_stock_data() -> List[AdobeStockRecord]:
    """Sample Adobe stock data for year-end."""
    return [
        AdobeStockRecord(**{
            'Date': date(2023, 12, 29),  # Last trading day 2023
            'Close/Last': 500.00,
            'Volume': 1000000,
            'Open': 495.00,
            'High': 505.00,
            'Low': 490.00
        }),
        AdobeStockRecord(**{
            'Date': date(2024, 12, 30),  # Last trading day 2024
            'Close/Last': 525.00,
            'Volume': 1200000,
            'Open': 520.00,
            'High': 530.00,
            'Low': 515.00
        }),
        AdobeStockRecord(**{
            'Date': date(2024, 6, 15),
            'Close/Last': 510.00,
            'Volume': 1100000,
            'Open': 505.00,
            'High': 515.00,
            'Low': 500.00
        })
    ]


@pytest.fixture
def fa_calculator(sample_sbi_rates, sample_stock_data) -> FACalculator:
    """FA calculator instance with test data."""
    return FACalculator(sample_sbi_rates, sample_stock_data)


class TestFACalculator:
    """Test FA Calculator functionality."""

    def test_initialization(self, fa_calculator):
        """Test calculator initialization."""
        assert len(fa_calculator.sbi_rates) == 3
        assert len(fa_calculator.stock_data) == 3

    def test_get_year_end_exchange_rate(self, fa_calculator):
        """Test year-end exchange rate lookup."""
        # Exact business day match
        rate = fa_calculator.get_year_end_exchange_rate("2024")
        assert rate == 83.50  # Dec 30, 2024
        
        # Should find nearby rate for 2023
        rate = fa_calculator.get_year_end_exchange_rate("2023")
        assert rate == 83.25  # Dec 29, 2023
        
        # No data available for this year
        rate = fa_calculator.get_year_end_exchange_rate("2025")
        assert rate is None

    def test_get_year_end_stock_price(self, fa_calculator):
        """Test year-end stock price lookup."""
        # Exact trading day match
        price = fa_calculator.get_year_end_stock_price("2024")
        assert price == 525.00  # Dec 30, 2024
        
        # Should find nearby price for 2023
        price = fa_calculator.get_year_end_stock_price("2023")
        assert price == 500.00  # Dec 29, 2023
        
        # No data available
        price = fa_calculator.get_year_end_stock_price("2025")
        assert price is None

    def test_calendar_year_calculation(self, fa_calculator):
        """Test calendar year calculation."""
        assert fa_calculator.calculate_calendar_year(date(2024, 1, 1)) == "2024"
        assert fa_calculator.calculate_calendar_year(date(2024, 6, 15)) == "2024"
        assert fa_calculator.calculate_calendar_year(date(2024, 12, 31)) == "2024"

    def test_process_equity_holdings(self, fa_calculator):
        """Test processing of equity holdings."""
        # Create sample BenefitHistory records
        benefit_records = [
            # Grant record
            BenefitHistoryRecord(
                record_type="Grant",
                symbol="ADBE",
                grant_date=date(2023, 6, 15),
                grant_number="RU123456",
                granted_qty=200.0,
                award_price=0.0  # RSUs typically have $0 grant price
            ),
            # Vesting event
            BenefitHistoryRecord(
                record_type="Event",
                event_type="RSU Vest",
                vest_date=date(2024, 6, 15),
                grant_date=date(2023, 6, 15),
                grant_number="RU123456",
                qty_or_amount=100.0  # 100 shares vested
            )
        ]
        
        # Calculate holdings as of end of 2024
        as_of_date = date(2024, 12, 31)
        equity_holdings = fa_calculator.process_equity_holdings(benefit_records, as_of_date)
        
        assert len(equity_holdings) == 2  # One vested, one unvested
        
        # Find vested and unvested holdings
        vested_holding = next((h for h in equity_holdings if h.holding_type == "Vested"), None)
        unvested_holding = next((h for h in equity_holdings if h.holding_type == "Unvested"), None)
        
        assert vested_holding is not None
        assert unvested_holding is not None
        
        # Verify vested holding
        assert vested_holding.quantity == 100.0
        assert vested_holding.market_value_usd_per_share == 525.0
        assert vested_holding.exchange_rate == 83.50
        assert vested_holding.market_value_usd_total == 52500.0  # 100 * 525
        assert vested_holding.market_value_inr_total == 52500.0 * 83.50
        assert vested_holding.calendar_year == "2024"
        
        # Verify unvested holding
        assert unvested_holding.quantity == 100.0  # 200 granted - 100 vested
        assert unvested_holding.cost_basis_usd_total == 0.0  # Not owned yet
        assert unvested_holding.market_value_usd_total == 52500.0  # 100 * 525
        assert unvested_holding.calendar_year == "2024"

    def test_calculate_fa_summary(self, fa_calculator):
        """Test FA declaration summary calculation."""
        # Create sample equity holdings
        equity_holdings = [
            EquityHolding(
                holding_date=date(2024, 12, 31),
                quantity=100.0,
                cost_basis_usd_per_share=0.0,
                market_value_usd_per_share=525.0,
                cost_basis_usd_total=0.0,
                market_value_usd_total=52500.0,
                cost_basis_inr_total=0.0,
                market_value_inr_total=4383750.0,  # 52500 * 83.50
                exchange_rate=83.50,
                holding_type="Vested",
                grant_number="RU123456",
                calendar_year="2024"
            ),
            EquityHolding(
                holding_date=date(2024, 12, 31),
                quantity=100.0,
                cost_basis_usd_per_share=0.0,
                market_value_usd_per_share=525.0,
                cost_basis_usd_total=0.0,
                market_value_usd_total=52500.0,
                cost_basis_inr_total=0.0,
                market_value_inr_total=4383750.0,  # 52500 * 83.50
                exchange_rate=83.50,
                holding_type="Unvested",
                grant_number="RU123456", 
                calendar_year="2024"
            )
        ]
        
        summary = fa_calculator.calculate_fa_summary("2024", equity_holdings)
        
        assert summary.calendar_year == "2024"
        assert summary.total_vested_shares == 100.0
        assert summary.total_unvested_shares == 100.0
        assert summary.vested_holdings_inr == 4383750.0
        assert summary.unvested_holdings_inr == 4383750.0
        assert summary.total_equity_value_inr == 8767500.0
        assert summary.year_end_exchange_rate == 83.50
        
        # Check declaration requirements (₹2 lakh threshold)
        assert summary.exceeds_declaration_threshold  # ₹87.7 lakhs > ₹2 lakhs
        assert summary.declaration_required  # Vested holdings ₹43.8 lakhs > ₹2 lakhs


class TestEquityHolding:
    """Test EquityHolding model."""

    def test_unrealized_gain_calculation(self):
        """Test unrealized gain calculation."""
        holding = EquityHolding(
            holding_date=date(2024, 12, 31),
            quantity=100.0,
            cost_basis_usd_per_share=400.0,
            market_value_usd_per_share=525.0,
            cost_basis_usd_total=40000.0,  # 100 * 400
            market_value_usd_total=52500.0,  # 100 * 525
            cost_basis_inr_total=3340000.0,  # 40000 * 83.50
            market_value_inr_total=4383750.0,  # 52500 * 83.50
            exchange_rate=83.50,
            holding_type="Vested",
            calendar_year="2024"
        )
        
        # Unrealized gain in USD
        assert holding.unrealized_gain_usd == 12500.0  # 52500 - 40000
        
        # Unrealized gain in INR
        expected_gain_inr = 12500.0 * 83.50  # 1,043,750
        assert holding.unrealized_gain_inr == expected_gain_inr


class TestFADeclarationSummary:
    """Test FADeclarationSummary model."""

    def test_declaration_threshold_logic(self):
        """Test FA declaration threshold logic."""
        
        # Below threshold - no declaration required
        summary_below = FADeclarationSummary(
            declaration_date=date(2024, 12, 31),
            calendar_year="2024",
            vested_holdings_inr=150000.0,  # ₹1.5 lakhs
            unvested_holdings_inr=50000.0   # ₹0.5 lakhs
        )
        summary_below.total_equity_value_inr = 200000.0
        
        assert not summary_below.declaration_required  # ₹1.5 lakhs < ₹2 lakhs threshold
        assert not summary_below.exceeds_declaration_threshold  # Total ₹2 lakhs = threshold (not >)
        
        # Above threshold - declaration required
        summary_above = FADeclarationSummary(
            declaration_date=date(2024, 12, 31),
            calendar_year="2024",
            vested_holdings_inr=500000.0,  # ₹5 lakhs
            unvested_holdings_inr=300000.0  # ₹3 lakhs
        )
        summary_above.total_equity_value_inr = 800000.0
        
        assert summary_above.declaration_required  # ₹5 lakhs > ₹2 lakhs threshold
        assert summary_above.exceeds_declaration_threshold  # Total ₹8 lakhs > ₹2 lakhs

    def test_edge_case_exact_threshold(self):
        """Test edge case at exact threshold."""
        summary = FADeclarationSummary(
            declaration_date=date(2024, 12, 31),
            calendar_year="2024",
            vested_holdings_inr=200000.0,  # Exactly ₹2 lakhs
            unvested_holdings_inr=0.0
        )
        summary.total_equity_value_inr = 200000.0
        
        # At exact threshold, declaration is required
        assert summary.declaration_required  # ₹2 lakhs >= ₹2 lakhs threshold
        assert not summary.exceeds_declaration_threshold  # ₹2 lakhs not > ₹2 lakhs threshold
