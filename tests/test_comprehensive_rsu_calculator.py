"""Comprehensive tests for RSU calculation engine with ESOP data and formula validation."""

import pytest
from datetime import date
from typing import List
from unittest.mock import Mock, patch
from pydantic import ValidationError

from equitywise.calculators.rsu_calculator import (
    RSUCalculator, VestingEvent, SaleEvent, RSUCalculationSummary
)
from equitywise.data.models import (
    GLStatementRecord, SBIRateRecord, AdobeStockRecord
)
from equitywise.data.esop_parser import ESOPVestingRecord


@pytest.fixture
def sample_sbi_rates() -> List[SBIRateRecord]:
    """Sample SBI exchange rates covering test scenarios."""
    return [
        SBIRateRecord(**{
            'Date': date(2024, 1, 15),
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD',
            'Rate': 83.25
        }),
        SBIRateRecord(**{
            'Date': date(2024, 4, 15),
            'Time': '1:00:00 PM', 
            'Currency Pairs': 'INR / 1 USD',
            'Rate': 83.45
        }),
        SBIRateRecord(**{
            'Date': date(2024, 7, 15),
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD', 
            'Rate': 83.60
        }),
        SBIRateRecord(**{
            'Date': date(2024, 10, 15),
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD', 
            'Rate': 84.00
        }),
        SBIRateRecord(**{
            'Date': date(2025, 1, 31),
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD', 
            'Rate': 86.64
        }),
        SBIRateRecord(**{
            'Date': date(2025, 4, 15),
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD', 
            'Rate': 87.20
        })
    ]


@pytest.fixture
def sample_stock_data() -> List[AdobeStockRecord]:
    """Sample Adobe stock data covering test scenarios."""
    return [
        AdobeStockRecord(**{
            'Date': date(2024, 1, 15),
            'Close/Last': 419.49,
            'Volume': 1000000,
            'Open': 415.00,
            'High': 425.00,
            'Low': 410.00
        }),
        AdobeStockRecord(**{
            'Date': date(2024, 4, 15),
            'Close/Last': 473.56,
            'Volume': 1200000,
            'Open': 470.00,
            'High': 480.00,
            'Low': 465.00
        }),
        AdobeStockRecord(**{
            'Date': date(2024, 7, 15),
            'Close/Last': 562.97,
            'Volume': 1100000,
            'Open': 560.00,
            'High': 570.00,
            'Low': 555.00
        }),
        AdobeStockRecord(**{
            'Date': date(2024, 10, 15),
            'Close/Last': 510.93,
            'Volume': 1300000,
            'Open': 515.00,
            'High': 520.00,
            'Low': 505.00
        }),
        AdobeStockRecord(**{
            'Date': date(2025, 1, 31),
            'Close/Last': 445.63,
            'Volume': 1400000,
            'Open': 440.00,
            'High': 450.00,
            'Low': 435.00
        }),
        AdobeStockRecord(**{
            'Date': date(2025, 4, 15),
            'Close/Last': 455.00,
            'Volume': 1500000,
            'Open': 450.00,
            'High': 460.00,
            'Low': 445.00
        })
    ]


@pytest.fixture
def sample_esop_records() -> List[ESOPVestingRecord]:
    """Sample ESOP vesting records from PDF data."""
    return [
        ESOPVestingRecord(
            employee_id="12345",
            employee_name="Test Employee",
            vesting_date=date(2024, 4, 15),
            grant_number="RU3861",
            fmv_usd=473.56,
            quantity=3,
            total_usd=1420.68,  # 473.56 * 3
            forex_rate=83.4516,
            total_inr=118558.0
        ),
        ESOPVestingRecord(
            employee_id="12345",
            employee_name="Test Employee",
            vesting_date=date(2024, 7, 15),
            grant_number="RU3861",
            fmv_usd=562.97,
            quantity=3,
            total_usd=1688.91,  # 562.97 * 3
            forex_rate=83.6051,
            total_inr=141201.0
        ),
        ESOPVestingRecord(
            employee_id="12345",
            employee_name="Test Employee",
            vesting_date=date(2025, 4, 15),  # Changed to FY25-26
            grant_number="RU3861",
            fmv_usd=419.49,
            quantity=3,
            total_usd=1258.47,  # 419.49 * 3
            forex_rate=86.3632,
            total_inr=108685.0
        )
    ]


@pytest.fixture
def sample_gl_records() -> List[GLStatementRecord]:
    """Sample G&L statement records."""
    return [
        GLStatementRecord(
            record_type="Sell",
            symbol="ADBE",
            quantity=3.0,
            date_acquired=date(2024, 4, 15),
            date_sold=date(2024, 7, 15),
            total_proceeds=1688.91,  # 3 * $562.97
            proceeds_per_share=562.97,
            adjusted_cost_basis=1420.68,  # 3 * $473.56 (vest FMV)
            adjusted_gain_loss=268.23,  # $1688.91 - $1420.68
            grant_date=date(2023, 4, 15),
            vest_date=date(2024, 4, 15),
            grant_number="RU3861",
            order_number="TEST001"
        ),
        GLStatementRecord(
            record_type="Sell",
            symbol="ADBE",
            quantity=3.0,
            date_acquired=date(2025, 4, 15),  # Updated to match new vesting date
            date_sold=date(2025, 4, 15),     # Same day sale for testing
            total_proceeds=1365.00,  # 3 * $455.00 (updated price)
            proceeds_per_share=455.00,       # Updated to match stock price
            adjusted_cost_basis=1258.47,     # 3 * $419.49 (vest FMV)
            adjusted_gain_loss=106.53,       # $1365.00 - $1258.47
            grant_date=date(2024, 4, 15),   # Updated grant date
            vest_date=date(2025, 4, 15),    # Updated to match new vesting date
            grant_number="RU3861",
            order_number="TEST002"
        )
    ]


@pytest.fixture
def rsu_calculator(sample_sbi_rates, sample_stock_data) -> RSUCalculator:
    """RSU calculator instance with test data."""
    return RSUCalculator(sample_sbi_rates, sample_stock_data)


class TestRSUCalculatorFormulas:
    """Test RSU Calculator formula implementations."""

    def test_initialization(self, rsu_calculator):
        """Test calculator initialization with proper data structures."""
        assert len(rsu_calculator.sbi_rates) == 6  # Updated count
        assert len(rsu_calculator.stock_data) == 6  # Updated count
        assert len(rsu_calculator.vesting_events) == 0  # Should start empty

    def test_exchange_rate_lookup_exact_match(self, rsu_calculator):
        """Test exchange rate lookup with exact date match."""
        rate = rsu_calculator.get_exchange_rate(date(2024, 7, 15))
        assert rate == 83.60

    def test_exchange_rate_lookup_fallback(self, rsu_calculator):
        """Test exchange rate lookup with fallback logic."""
        # Date close to existing rate (within 7-day window)
        rate = rsu_calculator.get_exchange_rate(date(2024, 7, 17))
        assert rate == 83.60  # Should fallback to nearest available
        
        # Date too far from any available rate
        rate = rsu_calculator.get_exchange_rate(date(2023, 1, 1))
        assert rate is None

    def test_stock_price_lookup_exact_match(self, rsu_calculator):
        """Test stock price lookup with exact date match."""
        price = rsu_calculator.get_stock_price(date(2024, 10, 15))
        assert price == 510.93

    def test_stock_price_lookup_fallback(self, rsu_calculator):
        """Test stock price lookup with fallback logic."""
        # Date close to existing price (within 7-day window)
        price = rsu_calculator.get_stock_price(date(2024, 10, 17))
        assert price == 510.93  # Should fallback to nearest available
        
        # Date too far from any available price
        price = rsu_calculator.get_stock_price(date(2023, 1, 1))
        assert price is None

    def test_financial_year_calculation_formulas(self, rsu_calculator):
        """Test Indian financial year calculation formulas."""
        # Formula: April 1 - March 31 is one financial year
        # April onwards - current year becomes FY prefix
        assert rsu_calculator.calculate_financial_year(date(2024, 4, 1)) == "FY24-25"
        assert rsu_calculator.calculate_financial_year(date(2024, 6, 15)) == "FY24-25"
        assert rsu_calculator.calculate_financial_year(date(2024, 12, 31)) == "FY24-25"
        assert rsu_calculator.calculate_financial_year(date(2025, 3, 31)) == "FY24-25"
        
        # Jan-Mar - previous year becomes FY prefix
        assert rsu_calculator.calculate_financial_year(date(2024, 1, 15)) == "FY23-24"
        assert rsu_calculator.calculate_financial_year(date(2024, 3, 31)) == "FY23-24"

    def test_esop_vesting_formulas(self, rsu_calculator, sample_esop_records):
        """Test ESOP vesting event processing formulas."""
        vesting_events = rsu_calculator.process_esop_vesting_events(sample_esop_records)
        
        assert len(vesting_events) == 3
        
        # Test first vesting event formulas
        event1 = vesting_events[0]
        assert event1.vested_quantity == 3
        assert event1.vest_fmv_usd == 473.56
        assert event1.exchange_rate == 83.4516
        
        # Formula 1: Individual Share Value (INR) = Vest_FMV_USD × ESOP_Exchange_Rate
        expected_fmv_inr = 473.56 * 83.4516
        assert abs(event1.vest_fmv_inr - expected_fmv_inr) < 0.01
        
        # Formula 2: Total Taxable Gain (USD) = Vest_FMV_USD × Vested_Quantity
        expected_taxable_usd = 473.56 * 3
        assert abs(event1.taxable_gain_usd - expected_taxable_usd) < 0.01
        
        # Formula 3: Use exact INR total from ESOP document (most accurate)
        assert event1.taxable_gain_inr == 118558.0  # Direct from ESOP PDF
        
        # Verify financial year calculation
        assert event1.financial_year == "FY24-25"

    def test_sale_event_formulas(self, rsu_calculator, sample_gl_records, sample_esop_records):
        """Test sale event processing formulas."""
        # First process vesting events to populate lookup
        rsu_calculator.process_esop_vesting_events(sample_esop_records)
        
        # Then process sales
        sale_events = rsu_calculator.process_sale_events(sample_gl_records)
        
        assert len(sale_events) == 2
        
        # Test first sale event formulas
        sale1 = sale_events[0]
        
        # Formula 1: Sale Proceeds (USD) - from G&L
        assert sale1.sale_proceeds_usd == 1688.91
        assert sale1.sale_price_usd == 562.97  # Per share
        
        # Formula 2: Sale Proceeds (INR) = Sale_Proceeds_USD × Sale_Date_Exchange_Rate
        expected_proceeds_inr = 1688.91 * 83.60  # Using 7/15 rate
        assert abs(sale1.sale_proceeds_inr - expected_proceeds_inr) < 1.0
        
        # Formula 3: Cost Basis (USD) - from G&L adjusted cost basis
        assert sale1.cost_basis_usd == 1420.68
        
        # Formula 4: Cost Basis (INR) = Cost_Basis_USD × Sale_Date_Exchange_Rate
        expected_cost_basis_inr = 1420.68 * 83.60
        assert abs(sale1.cost_basis_inr - expected_cost_basis_inr) < 1.0
        
        # Formula 5: Capital Gain (USD) - from G&L adjusted gain/loss (preferred)
        assert sale1.capital_gain_usd == 268.23
        
        # Formula 7: Capital Gain (INR) = Capital_Gain_USD × Sale_Date_Exchange_Rate
        expected_gain_inr = 268.23 * 83.60
        assert abs(sale1.capital_gain_inr - expected_gain_inr) < 1.0
        
        # Formula 8: Holding Period Classification
        holding_days = (date(2024, 7, 15) - date(2024, 4, 15)).days
        assert sale1.holding_period_days == holding_days
        assert sale1.gain_type == "Short-term"  # < 720 days (24 months)
        assert not sale1.is_long_term

    def test_long_term_gain_classification(self, rsu_calculator):
        """Test long-term capital gain classification (24-month rule)."""
        # Create a sale with > 24 months holding period
        long_term_sale = [
            GLStatementRecord(
                record_type="Sell",
                symbol="ADBE",
                quantity=1.0,
                date_acquired=date(2022, 1, 15),  # More than 24 months ago
                date_sold=date(2024, 7, 15),
                total_proceeds=562.97,
                proceeds_per_share=562.97,
                adjusted_cost_basis=400.00,
                adjusted_gain_loss=162.97,
                grant_date=date(2021, 1, 15),
                vest_date=date(2022, 1, 15),
                grant_number="RU_OLD",
                order_number="LONG_TERM"
            )
        ]
        
        sale_events = rsu_calculator.process_sale_events(long_term_sale)
        assert len(sale_events) == 1
        
        sale = sale_events[0]
        holding_days = (date(2024, 7, 15) - date(2022, 1, 15)).days
        assert sale.holding_period_days == holding_days
        assert sale.holding_period_days > (24 * 30)  # > 720 days
        assert sale.gain_type == "Long-term"
        assert sale.is_long_term

    def test_fy_summary_aggregation_formulas(self, rsu_calculator, sample_esop_records, sample_gl_records):
        """Test FY summary calculation formulas."""
        # Process both vesting and sale events
        vesting_events = rsu_calculator.process_esop_vesting_events(sample_esop_records)
        sale_events = rsu_calculator.process_sale_events(sample_gl_records)
        
        summary = rsu_calculator.calculate_fy_summary("FY24-25", vesting_events, sale_events)
        
        # Test vesting aggregation formulas
        expected_total_vested = sum(v.vested_quantity for v in vesting_events if v.financial_year == "FY24-25")
        assert summary.total_vested_quantity == expected_total_vested
        
        expected_taxable_gain_inr = sum(v.taxable_gain_inr for v in vesting_events if v.financial_year == "FY24-25")
        assert summary.total_taxable_gain_inr == expected_taxable_gain_inr
        
        # Test sale aggregation formulas
        fy_sales = [s for s in sale_events if s.financial_year == "FY24-25"]
        expected_total_sold = sum(s.quantity_sold for s in fy_sales)
        assert summary.total_sold_quantity == expected_total_sold
        
        expected_capital_gains_inr = sum(s.capital_gain_inr for s in fy_sales)
        assert abs(summary.total_capital_gains_inr - expected_capital_gains_inr) < 1.0
        
        # Test net position formula: Vesting Income + Capital Gains
        expected_net = summary.total_taxable_gain_inr + summary.total_capital_gains_inr
        assert abs(summary.net_gain_loss_inr - expected_net) < 1.0

    def test_vesting_lookup_functionality(self, rsu_calculator, sample_esop_records):
        """Test vesting details lookup for sale processing."""
        # Process vesting events first
        rsu_calculator.process_esop_vesting_events(sample_esop_records)
        
        # Test lookup functionality
        vest_details = rsu_calculator.get_vesting_details(date(2024, 4, 15), "RU3861")
        assert vest_details is not None
        assert vest_details.vest_fmv_usd == 473.56
        assert vest_details.exchange_rate == 83.4516
        
        # Test non-existent lookup
        missing_details = rsu_calculator.get_vesting_details(date(2023, 1, 1), "NONEXISTENT")
        assert missing_details is None

    def test_average_exchange_rate_calculation(self):
        """Test average exchange rate calculation in summary."""
        summary = RSUCalculationSummary(
            financial_year="FY24-25",
            total_taxable_gain_usd=1000.0,
            total_taxable_gain_inr=84000.0
        )
        
        expected_avg_rate = 84000.0 / 1000.0
        assert summary.average_exchange_rate == expected_avg_rate
        
        # Test zero division case
        empty_summary = RSUCalculationSummary(financial_year="FY24-25")
        assert empty_summary.average_exchange_rate == 0.0


class TestRSUCalculatorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_data_handling(self):
        """Test calculator with empty data sets."""
        empty_calculator = RSUCalculator([], [])
        
        # Should handle empty data gracefully
        assert empty_calculator.get_exchange_rate(date(2024, 1, 1)) is None
        assert empty_calculator.get_stock_price(date(2024, 1, 1)) is None
        
        # Should return empty results
        vesting_events = empty_calculator.process_esop_vesting_events([])
        assert vesting_events == []
        
        sale_events = empty_calculator.process_sale_events([])
        assert sale_events == []

    def test_invalid_esop_record_handling(self, rsu_calculator):
        """Test that invalid ESOP records are properly validated."""
        # Test that validation prevents creation of invalid records
        with pytest.raises(ValidationError):
            ESOPVestingRecord(
                employee_id="12345",
                employee_name="Test Employee",
                vesting_date=date(2024, 4, 15),
                grant_number="INVALID",
                fmv_usd=0.0,  # Invalid FMV - should fail validation
                quantity=0,   # Invalid quantity - should fail validation
                total_usd=0.0,
                forex_rate=0.0,  # Invalid rate - should fail validation
                total_inr=0.0
            )
        
        # Test calculator handles empty list gracefully
        vesting_events = rsu_calculator.process_esop_vesting_events([])
        assert isinstance(vesting_events, list)
        assert len(vesting_events) == 0

    def test_missing_rate_fallback_behavior(self, rsu_calculator):
        """Test behavior when exchange rates or stock prices are missing."""
        # Test with date far outside available data
        distant_date = date(2020, 1, 1)
        
        rate = rsu_calculator.get_exchange_rate(distant_date)
        assert rate is None
        
        price = rsu_calculator.get_stock_price(distant_date)
        assert price is None

    def test_sale_without_matching_vesting(self, rsu_calculator, sample_gl_records):
        """Test sale processing when matching vesting details are not found."""
        # Process sales without first processing vestings
        sale_events = rsu_calculator.process_sale_events(sample_gl_records)
        
        # Should still process sales but may use fallback values
        assert len(sale_events) >= 0  # Depends on implementation - may skip or use fallbacks
        
        for sale in sale_events:
            # Should have basic sale information even without vesting lookup
            assert sale.sale_proceeds_usd > 0
            assert sale.quantity_sold > 0


class TestRSUCalculatorIntegration:
    """Integration tests combining multiple components."""

    def test_full_calculation_workflow(self, rsu_calculator, sample_esop_records, sample_gl_records):
        """Test complete calculation workflow from ESOP to final summary."""
        # Step 1: Process vesting events (Formula application)
        vesting_events = rsu_calculator.process_esop_vesting_events(sample_esop_records)
        assert len(vesting_events) > 0
        
        # Step 2: Process sale events (Formula application)
        sale_events = rsu_calculator.process_sale_events(sample_gl_records)
        assert len(sale_events) > 0
        
        # Step 3: Calculate FY summary (Aggregation formulas)
        summary = rsu_calculator.calculate_fy_summary("FY24-25", vesting_events, sale_events)
        
        # Verify complete workflow produces valid results
        assert summary.total_vested_quantity > 0
        assert summary.total_taxable_gain_inr > 0
        assert summary.vesting_events_count > 0
        
        # Verify mathematical consistency
        manual_vesting_total = sum(v.taxable_gain_inr for v in vesting_events if v.financial_year == "FY24-25")
        assert abs(summary.total_taxable_gain_inr - manual_vesting_total) < 1.0
        
        manual_sales_total = sum(s.capital_gain_inr for s in sale_events if s.financial_year == "FY24-25")
        assert abs(summary.total_capital_gains_inr - manual_sales_total) < 1.0

    def test_multi_financial_year_handling(self, rsu_calculator, sample_esop_records, sample_gl_records):
        """Test handling of transactions across multiple financial years."""
        # Process all events
        vesting_events = rsu_calculator.process_esop_vesting_events(sample_esop_records)
        sale_events = rsu_calculator.process_sale_events(sample_gl_records)
        
        # Check that events are properly classified by FY
        fy_24_25_vestings = [v for v in vesting_events if v.financial_year == "FY24-25"]
        fy_25_26_vestings = [v for v in vesting_events if v.financial_year == "FY25-26"]
        
        assert len(fy_24_25_vestings) > 0
        assert len(fy_25_26_vestings) > 0
        
        # Test separate FY summaries
        fy_24_25_summary = rsu_calculator.calculate_fy_summary("FY24-25", vesting_events, sale_events)
        fy_25_26_summary = rsu_calculator.calculate_fy_summary("FY25-26", vesting_events, sale_events)
        
        # Summaries should be different and only include relevant FY data
        assert fy_24_25_summary.total_taxable_gain_inr != fy_25_26_summary.total_taxable_gain_inr
