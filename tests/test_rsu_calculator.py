"""Tests for RSU calculation engine."""

import pytest
from datetime import date
from typing import List

from equitywise.calculators.rsu_calculator import (
    RSUCalculator, VestingEvent, SaleEvent, RSUCalculationSummary
)
from equitywise.data.models import (
    BenefitHistoryRecord, GLStatementRecord, SBIRateRecord, AdobeStockRecord
)


@pytest.fixture
def sample_sbi_rates() -> List[SBIRateRecord]:
    """Sample SBI exchange rates."""
    return [
        SBIRateRecord(**{
            'Date': date(2024, 1, 15),
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD',
            'Rate': 83.25
        }),
        SBIRateRecord(**{
            'Date': date(2024, 6, 15),
            'Time': '1:00:00 PM', 
            'Currency Pairs': 'INR / 1 USD',
            'Rate': 83.50
        }),
        SBIRateRecord(**{
            'Date': date(2024, 10, 15),
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD', 
            'Rate': 84.00
        })
    ]


@pytest.fixture
def sample_stock_data() -> List[AdobeStockRecord]:
    """Sample Adobe stock data."""
    return [
        AdobeStockRecord(**{
            'Date': date(2024, 1, 15),
            'Close/Last': 500.00,
            'Volume': 1000000,
            'Open': 495.00,
            'High': 505.00,
            'Low': 490.00
        }),
        AdobeStockRecord(**{
            'Date': date(2024, 6, 15),
            'Close/Last': 525.00,
            'Volume': 1200000,
            'Open': 520.00,
            'High': 530.00,
            'Low': 515.00
        }),
        AdobeStockRecord(**{
            'Date': date(2024, 10, 15),
            'Close/Last': 550.00,
            'Volume': 1100000,
            'Open': 545.00,
            'High': 555.00,
            'Low': 540.00
        })
    ]


@pytest.fixture
def rsu_calculator(sample_sbi_rates, sample_stock_data) -> RSUCalculator:
    """RSU calculator instance with test data."""
    return RSUCalculator(sample_sbi_rates, sample_stock_data)


class TestRSUCalculator:
    """Test RSU Calculator functionality."""

    def test_initialization(self, rsu_calculator):
        """Test calculator initialization."""
        assert len(rsu_calculator.sbi_rates) == 3
        assert len(rsu_calculator.stock_data) == 3

    def test_get_exchange_rate(self, rsu_calculator):
        """Test exchange rate lookup."""
        # Exact date match
        rate = rsu_calculator.get_exchange_rate(date(2024, 1, 15))
        assert rate == 83.25
        
        # No exact match, should return None (no fallback implemented in simple test)
        rate = rsu_calculator.get_exchange_rate(date(2024, 2, 1))
        assert rate is None

    def test_get_stock_price(self, rsu_calculator):
        """Test stock price lookup."""
        # Exact date match
        price = rsu_calculator.get_stock_price(date(2024, 6, 15))
        assert price == 525.00
        
        # No exact match
        price = rsu_calculator.get_stock_price(date(2024, 7, 1))
        assert price is None

    def test_financial_year_calculation(self, rsu_calculator):
        """Test Indian financial year calculation."""
        # April onwards - next year FY
        assert rsu_calculator.calculate_financial_year(date(2024, 4, 1)) == "FY24-25"
        assert rsu_calculator.calculate_financial_year(date(2024, 6, 15)) == "FY24-25"
        assert rsu_calculator.calculate_financial_year(date(2024, 12, 31)) == "FY24-25"
        
        # Jan-Mar - current year FY
        assert rsu_calculator.calculate_financial_year(date(2024, 1, 15)) == "FY23-24"
        assert rsu_calculator.calculate_financial_year(date(2024, 3, 31)) == "FY23-24"

    def test_process_vesting_events(self, rsu_calculator):
        """Test processing of vesting events."""
        # Create sample BenefitHistory records
        benefit_records = [
            BenefitHistoryRecord(
                record_type="Event",
                event_type="Shares vested",
                date=date(2024, 6, 15),
                grant_date=date(2023, 6, 15),
                grant_number="RU123456",
                qty_or_amount=100.0,
                est_market_value=52500.00,  # 100 shares * $525
                award_price=0.0,
                withholding_amount=5000.00
            )
        ]
        
        vesting_events = rsu_calculator.process_vesting_events(benefit_records)
        
        assert len(vesting_events) == 1
        event = vesting_events[0]
        
        assert event.vested_quantity == 100.0
        assert event.vest_fmv_usd == 525.0  # $52,500 / 100 shares
        assert event.exchange_rate == 83.50
        assert event.vest_fmv_inr == 525.0 * 83.50
        assert event.taxable_gain_usd == 52500.0  # (525 - 0) * 100
        assert event.taxable_gain_inr == 52500.0 * 83.50
        assert event.financial_year == "FY24-25"
        assert event.taxes_withheld == 5000.00

    def test_process_sale_events(self, rsu_calculator):
        """Test processing of sale events."""
        # Create sample G&L records
        gl_records = [
            GLStatementRecord(
                record_type="Sell",
                symbol="ADBE",
                quantity=50.0,
                date_acquired=date(2024, 6, 15),
                date_sold=date(2024, 10, 15),
                total_proceeds=27500.00,  # 50 * $550
                proceeds_per_share=550.00,  # Per share sale price
                adjusted_cost_basis=26250.00,  # 50 * $525 (vest FMV)
                adjusted_gain_loss=1250.00,  # $27,500 - $26,250
                acquisition_cost=26250.00,  # Keep for backward compatibility
                grant_date=date(2023, 6, 15),
                vest_date=date(2024, 6, 15),
                grant_number="RU123456",
                order_number="12345678"
            )
        ]
        
        sale_events = rsu_calculator.process_sale_events(gl_records)
        
        assert len(sale_events) == 1
        event = sale_events[0]
        
        assert event.quantity_sold == 50.0
        assert event.sale_price_usd == 550.0  # $27,500 / 50 shares
        assert event.sale_proceeds_usd == 27500.0
        assert event.cost_basis_usd == 26250.0
        assert event.capital_gain_usd == 1250.0  # $27,500 - $26,250
        assert event.exchange_rate_sale == 84.00
        assert event.capital_gain_inr == 1250.0 * 84.00
        assert event.gain_type == "Short-term"  # 4 months holding period
        assert event.financial_year == "FY24-25"

    def test_calculate_fy_summary(self, rsu_calculator):
        """Test financial year summary calculation."""
        # Create sample events
        vesting_events = [
            VestingEvent(
                vest_date=date(2024, 6, 15),
                grant_date=date(2023, 6, 15),
                grant_number="RU123456",
                vested_quantity=100.0,
                vest_fmv_usd=525.0,
                vest_fmv_inr=43837.50,
                exchange_rate=83.50,
                taxable_gain_usd=52500.0,
                taxable_gain_inr=4383750.0,
                taxes_withheld=5000.0,
                financial_year="FY24-25"
            )
        ]
        
        sale_events = [
            SaleEvent(
                sale_date=date(2024, 10, 15),
                acquisition_date=date(2024, 6, 15),
                grant_date=date(2023, 6, 15),
                grant_number="RU123456",
                order_number="12345678",
                quantity_sold=50.0,
                sale_price_usd=550.0,
                sale_proceeds_usd=27500.0,
                sale_proceeds_inr=2310000.0,
                cost_basis_usd=26250.0,
                cost_basis_inr=2205000.0,
                capital_gain_usd=1250.0,
                capital_gain_inr=105000.0,
                gain_type="Short-term",
                exchange_rate_sale=84.00,
                financial_year="FY24-25"
            )
        ]
        
        summary = rsu_calculator.calculate_fy_summary("FY24-25", vesting_events, sale_events)
        
        # Vesting summary
        assert summary.total_vested_quantity == 100.0
        assert summary.total_taxable_gain_usd == 52500.0
        assert summary.total_taxable_gain_inr == 4383750.0
        assert summary.total_taxes_withheld == 5000.0
        assert summary.vesting_events_count == 1
        
        # Sale summary
        assert summary.total_sold_quantity == 50.0
        assert summary.total_sale_proceeds_usd == 27500.0
        assert summary.total_capital_gains_usd == 1250.0
        assert summary.short_term_gains_usd == 1250.0
        assert summary.long_term_gains_usd == 0.0
        assert summary.sale_events_count == 1
        
        # Net summary
        assert summary.net_gain_loss_inr == 4383750.0 + 105000.0  # Vesting + capital gains


class TestVestingEvent:
    """Test VestingEvent model."""

    def test_is_current_fy(self):
        """Test current FY detection."""
        # This test depends on current date, so we'll create a basic test
        vesting = VestingEvent(
            vest_date=date(2024, 6, 15),
            grant_date=date(2023, 6, 15),
            grant_number="RU123456",
            vested_quantity=100.0,
            vest_fmv_usd=525.0,
            vest_fmv_inr=43837.50,
            exchange_rate=83.50,
            taxable_gain_usd=52500.0,
            taxable_gain_inr=4383750.0,
            financial_year="FY24-25"
        )
        
        # Result depends on current date, so just verify method exists and runs
        result = vesting.is_current_fy
        assert isinstance(result, bool)


class TestSaleEvent:
    """Test SaleEvent model."""

    def test_holding_period_calculation(self):
        """Test holding period calculation."""
        sale = SaleEvent(
            sale_date=date(2024, 10, 15),
            acquisition_date=date(2024, 6, 15),
            grant_date=date(2023, 6, 15),
            grant_number="RU123456",
            order_number="12345678",
            quantity_sold=50.0,
            sale_price_usd=550.0,
            sale_proceeds_usd=27500.0,
            sale_proceeds_inr=2310000.0,
            cost_basis_usd=26250.0,
            cost_basis_inr=2205000.0,
            capital_gain_usd=1250.0,
            capital_gain_inr=105000.0,
            gain_type="Short-term",
            exchange_rate_sale=84.00,
            financial_year="FY24-25"
        )
        
        # 4 months = ~122 days
        assert sale.holding_period_days == 122
        assert not sale.is_long_term  # < 24 months


class TestRSUCalculationSummary:
    """Test RSUCalculationSummary model."""

    def test_average_exchange_rate(self):
        """Test average exchange rate calculation."""
        summary = RSUCalculationSummary(
            financial_year="FY24-25",
            total_taxable_gain_usd=52500.0,
            total_taxable_gain_inr=4383750.0
        )
        
        expected_rate = 4383750.0 / 52500.0
        assert abs(summary.average_exchange_rate - expected_rate) < 0.01
        
        # Test zero case
        empty_summary = RSUCalculationSummary(financial_year="FY2025")
        assert empty_summary.average_exchange_rate == 0.0
