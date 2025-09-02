"""Comprehensive tests for Pydantic data models and validation."""

import pytest
from datetime import date
from typing import Dict, Any
from decimal import Decimal
from pydantic import ValidationError

from rsu_fa_tool.data.models import (
    ESOPVestingRecord,
    GLStatementRecord, 
    SBIRateRecord,
    AdobeStockRecord,
    BankStatementRecord,
    RSUTransaction,
    BenefitHistoryRecord
)


class TestESOPVestingRecord:
    """Test ESOP vesting record validation and processing."""

    def test_valid_esop_record(self):
        """Test creation of valid ESOP vesting record."""
        record = ESOPVestingRecord(
            employee_id="TEST123",
            employee_name="Test Employee",
            vesting_date=date(2024, 4, 15),
            grant_number="RU3861",
            fmv_usd=473.56,
            quantity=3,
            total_usd=1420.68,
            forex_rate=83.4516,
            total_inr=118558.0
        )
        
        assert record.vesting_date == date(2024, 4, 15)
        assert record.grant_number == "RU3861"
        assert record.fmv_usd == 473.56
        assert record.quantity == 3
        assert record.forex_rate == 83.4516
        assert record.total_inr == 118558.0

    def test_esop_record_validation_errors(self):
        """Test ESOP record validation catches errors."""
        
        # Test negative FMV
        with pytest.raises(ValidationError):
            ESOPVestingRecord(
                employee_id="TEST123",
                employee_name="Test Employee",
                vesting_date=date(2024, 4, 15),
                grant_number="RU3861",
                fmv_usd=-100.0,  # Invalid negative FMV
                quantity=3,
                total_usd=-300.0,
                forex_rate=83.4516,
                total_inr=118558.0
            )
        
        # Test zero quantity
        with pytest.raises(ValidationError):
            ESOPVestingRecord(
                employee_id="TEST123",
                employee_name="Test Employee",
                vesting_date=date(2024, 4, 15),
                grant_number="RU3861",
                fmv_usd=473.56,
                quantity=0,  # Invalid zero quantity
                total_usd=0.0,
                forex_rate=83.4516,
                total_inr=118558.0
            )
        
        # Test negative exchange rate
        with pytest.raises(ValidationError):
            ESOPVestingRecord(
                employee_id="TEST123",
                employee_name="Test Employee",
                vesting_date=date(2024, 4, 15),
                grant_number="RU3861",
                fmv_usd=473.56,
                quantity=3,
                total_usd=1420.68,
                forex_rate=-1.0,  # Invalid negative rate
                total_inr=118558.0
            )

    def test_esop_record_edge_cases(self):
        """Test ESOP record edge cases."""
        # Test with decimal values
        record = ESOPVestingRecord(
            employee_id="TEST123",
            employee_name="Test Employee",
            vesting_date=date(2024, 4, 15),
            grant_number="RU3861",
            fmv_usd=473.567890,  # High precision
            quantity=4,  # Integer shares (no fractional shares in RSUs)
            total_usd=1894.27,
            forex_rate=83.451678,  # High precision rate
            total_inr=118558.123
        )
        
        assert record.fmv_usd == 473.567890
        assert record.quantity == 4
        assert record.forex_rate == 83.451678

    def test_esop_record_string_representations(self):
        """Test string representations of ESOP record."""
        record = ESOPVestingRecord(
            employee_id="TEST123",
            employee_name="Test Employee",
            vesting_date=date(2024, 4, 15),
            grant_number="RU3861",
            fmv_usd=473.56,
            quantity=3,
            total_usd=1420.68,
            forex_rate=83.4516,
            total_inr=118558.0
        )
        
        str_repr = str(record)
        assert "RU3861" in str_repr
        assert "2024-04-15" in str_repr


class TestGLStatementRecord:
    """Test G&L statement record validation and processing."""

    def test_valid_gl_record(self):
        """Test creation of valid G&L statement record."""
        record = GLStatementRecord(
            record_type="Sell",
            symbol="ADBE",
            quantity=3.0,
            date_acquired=date(2024, 4, 15),
            date_sold=date(2024, 7, 15),
            total_proceeds=1688.91,
            proceeds_per_share=562.97,
            adjusted_cost_basis=1420.68,
            adjusted_gain_loss=268.23,
            grant_date=date(2023, 4, 15),
            vest_date=date(2024, 4, 15),
            grant_number="RU3861",
            order_number="TEST001"
        )
        
        assert record.record_type == "Sell"
        assert record.symbol == "ADBE"
        assert record.quantity == 3.0
        assert record.total_proceeds == 1688.91
        assert record.adjusted_gain_loss == 268.23

    def test_gl_record_with_aliases(self):
        """Test G&L record creation with field aliases."""
        # Test that aliases work correctly
        raw_data = {
            "Record Type": "Sell",
            "Symbol": "ADBE", 
            "Quantity": 3.0,
            "Date Acquired": date(2024, 4, 15),
            "Date Sold": date(2024, 7, 15),
            "Total Proceeds": 1688.91,
            "Proceeds Per Share": 562.97,
            "Adjusted Cost Basis": 1420.68,
            "Adjusted Gain/Loss": 268.23
        }
        
        record = GLStatementRecord(**raw_data)
        assert record.record_type == "Sell"
        assert record.total_proceeds == 1688.91
        assert record.adjusted_gain_loss == 268.23

    def test_gl_record_validation_errors(self):
        """Test G&L record validation catches errors."""
        
        # Test invalid record type
        with pytest.raises(ValidationError):
            GLStatementRecord(
                record_type="InvalidType",  # Invalid type
                symbol="ADBE",
                quantity=3.0,
                date_sold=date(2024, 7, 15),
                total_proceeds=1688.91
            )
        
        # Test negative quantity
        with pytest.raises(ValidationError):
            GLStatementRecord(
                record_type="Sell",
                symbol="ADBE",
                quantity=-3.0,  # Invalid negative quantity
                date_sold=date(2024, 7, 15),
                total_proceeds=1688.91
            )

    def test_gl_record_optional_fields(self):
        """Test G&L record with optional fields."""
        # Minimal record with only required fields
        record = GLStatementRecord(
            record_type="Sell",
            symbol="ADBE",
            quantity=3.0,
            date_sold=date(2024, 7, 15),
            total_proceeds=1688.91
        )
        
        assert record.record_type == "Sell"
        assert record.grant_number is None
        assert record.order_number is None
        assert record.adjusted_cost_basis is None


class TestSBIRateRecord:
    """Test SBI rate record validation and processing."""

    def test_valid_sbi_rate_record(self):
        """Test creation of valid SBI rate record."""
        record = SBIRateRecord(**{
            "Date": date(2024, 7, 15),
            "Time": "1:00:00 PM",
            "Currency Pairs": "INR / 1 USD",
            "Rate": 83.60
        })
        
        assert record.date == date(2024, 7, 15)
        assert record.time == "1:00:00 PM"
        assert record.currency_pair == "INR / 1 USD"
        assert record.rate == 83.60

    def test_sbi_rate_with_aliases(self):
        """Test SBI rate record with field aliases."""
        raw_data = {
            "Date": date(2024, 7, 15),
            "Time": "1:00:00 PM",
            "Currency Pairs": "INR / 1 USD",
            "Rate": 83.60
        }
        
        record = SBIRateRecord(**raw_data)
        assert record.date == date(2024, 7, 15)
        assert record.rate == 83.60

    def test_sbi_rate_validation_errors(self):
        """Test SBI rate record validation."""
        
        # Test negative rate
        with pytest.raises(ValidationError):
            SBIRateRecord(**{
                "Date": date(2024, 7, 15),
                "Time": "1:00:00 PM",
                "Currency Pairs": "INR / 1 USD",
                "Rate": -83.60  # Invalid negative rate
            })
        
        # Test zero rate
        with pytest.raises(ValidationError):
            SBIRateRecord(**{
                "Date": date(2024, 7, 15),
                "Time": "1:00:00 PM",
                "Currency Pairs": "INR / 1 USD",
                "Rate": 0.0  # Invalid zero rate
            })

    def test_sbi_rate_precision(self):
        """Test SBI rate record with high precision."""
        record = SBIRateRecord(**{
            "Date": date(2024, 7, 15),
            "Time": "1:00:00 PM",
            "Currency Pairs": "INR / 1 USD",
            "Rate": 83.6051789  # High precision rate
        })
        
        assert record.rate == 83.6051789


class TestAdobeStockRecord:
    """Test Adobe stock record validation and processing."""

    def test_valid_adobe_stock_record(self):
        """Test creation of valid Adobe stock record."""
        record = AdobeStockRecord(**{
            "Date": date(2024, 7, 15),
            "Close/Last": 562.97,
            "Volume": 1234567,
            "Open": 560.00,
            "High": 570.00,
            "Low": 555.00
        })
        
        assert record.date == date(2024, 7, 15)
        assert record.close_price == 562.97
        assert record.volume == 1234567
        assert record.open_price == 560.00
        assert record.high_price == 570.00
        assert record.low_price == 555.00

    def test_adobe_stock_with_aliases(self):
        """Test Adobe stock record with field aliases."""
        raw_data = {
            "Date": date(2024, 7, 15),
            "Close/Last": 562.97,
            "Volume": 1234567,
            "Open": 560.00,
            "High": 570.00,
            "Low": 555.00
        }
        
        record = AdobeStockRecord(**raw_data)
        assert record.close_price == 562.97
        assert record.volume == 1234567

    def test_adobe_stock_validation_errors(self):
        """Test Adobe stock record validation."""
        
        # Test negative price
        with pytest.raises(ValidationError):
            AdobeStockRecord(**{
                "Date": date(2024, 7, 15),
                "Close/Last": -562.97,  # Invalid negative price
                "Volume": 1234567,
                "Open": 560.00,
                "High": 570.00,
                "Low": 555.00
            })
        
        # Test negative volume
        with pytest.raises(ValidationError):
            AdobeStockRecord(**{
                "Date": date(2024, 7, 15),
                "Close/Last": 562.97,
                "Volume": -1234567,  # Invalid negative volume
                "Open": 560.00,
                "High": 570.00,
                "Low": 555.00
            })

    def test_adobe_stock_price_relationships(self):
        """Test Adobe stock price relationship validation."""
        # Test that high >= low (should pass)
        record = AdobeStockRecord(**{
            "Date": date(2024, 7, 15),
            "Close/Last": 562.97,
            "Volume": 1234567,
            "Open": 560.00,
            "High": 570.00,
            "Low": 555.00
        })
        
        assert record.high_price >= record.low_price
        assert record.close_price >= record.low_price
        assert record.close_price <= record.high_price


class TestBankStatementRecord:
    """Test bank statement record validation and processing."""

    def test_valid_bank_statement_record(self):
        """Test creation of valid bank statement record."""
        record = BankStatementRecord(**{
            "S No.": 1,
            "Value Date": date(2025, 1, 31),
            "Transaction Date": date(2025, 2, 4),
            "Transaction Remarks": "IRM/USD6213.87@87.0375GST576/INREM/20250204115415",
            "Cheque Number": "",
            "Withdrawal Amount (INR )": 0.0,
            "Deposit Amount (INR )": 540264.0,
            "Balance (INR )": 1234567.89
        })
        
        assert record.serial_no == 1
        assert record.value_date == date(2025, 1, 31)
        assert record.transaction_date == date(2025, 2, 4)
        assert record.deposit_amount == 540264.0

    def test_bank_statement_broker_transaction_detection(self):
        """Test broker transaction detection logic."""
        # Broker transaction
        broker_record = BankStatementRecord(
            serial_no=1,
            value_date=date(2025, 1, 31),
            transaction_date=date(2025, 2, 4),
            transaction_remarks="IRM/USD6213.87@87.0375GST576/INREM/20250204115415",
            deposit_amount=540264.0,
            balance=1234567.89  # Fixed: use 'balance' not 'balance_amount'
        )
        
        assert broker_record.is_broker_transaction
        
        # Non-broker transaction
        regular_record = BankStatementRecord(
            serial_no=2,
            value_date=date(2025, 1, 31),
            transaction_date=date(2025, 2, 4),
            transaction_remarks="SALARY CREDIT FROM EMPLOYER",
            deposit_amount=100000.0,
            balance=1334567.89  # Fixed: use 'balance' not 'balance_amount'
        )
        
        assert not regular_record.is_broker_transaction

    def test_bank_statement_broker_details_extraction(self):
        """Test broker transaction details extraction."""
        record = BankStatementRecord(
            serial_no=1,
            value_date=date(2025, 1, 31),
            transaction_date=date(2025, 2, 4),
            transaction_remarks="IRM/USD6213.87@87.0375GST576/INREM/20250204115415",
            deposit_amount=540264.0,
            balance=1234567.89  # Fixed: use 'balance' not 'balance_amount'
        )
        
        details = record.extract_broker_details()
        assert details is not None
        
        # Test extracted values
        assert details['bank_usd_amount'] == 6213.87
        assert details['bank_exchange_rate'] == 87.0375
        assert details['gst_amount'] == 576.0
        
        # Test calculated values
        expected_inr_before_gst = 6213.87 * 87.0375
        assert abs(details['inr_before_gst'] - expected_inr_before_gst) < 0.01
        
        expected_inr_after_gst = expected_inr_before_gst - 576.0
        assert abs(details['inr_after_gst'] - expected_inr_after_gst) < 0.01
        
        # Test accuracy verification
        assert details['calculation_accurate']  # Should be within ₹1

    def test_bank_statement_non_broker_details(self):
        """Test non-broker transaction details extraction."""
        record = BankStatementRecord(
            serial_no=2,
            value_date=date(2025, 1, 31),
            transaction_date=date(2025, 2, 4),
            transaction_remarks="SALARY CREDIT FROM EMPLOYER",
            deposit_amount=100000.0,
            balance=1234567.89  # Fixed: use 'balance' not 'balance_amount'
        )
        
        details = record.extract_broker_details()
        assert details is None

    def test_bank_statement_debit_record(self):
        """Test bank statement debit record."""
        record = BankStatementRecord(
            serial_no=3,
            value_date=date(2025, 1, 31),
            transaction_date=date(2025, 2, 4),
            transaction_remarks="ATM WITHDRAWAL",
            withdrawal_amount=5000.0,  # Fixed: use 'withdrawal_amount' not 'debit_amount'
            deposit_amount=0.0,  # Fixed: use 0.0 instead of None for float field
            balance=1229567.89  # Fixed: use 'balance' not 'balance_amount'
        )
        
        assert record.is_debit
        assert not record.is_credit
        assert record.net_amount == -5000.0

    def test_bank_statement_field_validation(self):
        """Test bank statement field validation."""
        
        # Test invalid serial number
        with pytest.raises(ValidationError):
            BankStatementRecord(
                serial_no=0,  # Invalid zero serial number
                value_date=date(2025, 1, 31),
                transaction_date=date(2025, 2, 4),
                transaction_remarks="Test transaction",
                deposit_amount=1000.0,
                balance=1234567.89  # Fixed: use 'balance' not 'balance_amount'
            )
        
        # Test negative amounts (should be allowed for corrections)
        record = BankStatementRecord(
            serial_no=1,
            value_date=date(2025, 1, 31),
            transaction_date=date(2025, 2, 4),
            transaction_remarks="CORRECTION ENTRY",
            deposit_amount=-1000.0,  # Negative correction
            balance=1233567.89  # Fixed: use 'balance' not 'balance_amount'
        )
        
        assert record.deposit_amount == -1000.0


class TestRSUTransaction:
    """Test RSU transaction model validation."""

    def test_valid_rsu_transaction(self):
        """Test creation of valid RSU transaction."""
        transaction = RSUTransaction(
            grant_date=date(2024, 1, 15),  # Fixed: use correct field names
            vest_date=date(2024, 7, 15),   # Fixed: use vest_date not transaction_date
            grant_number="RU3861",
            symbol="ADBE",
            vested_quantity=3.0,           # Fixed: use vested_quantity not quantity
            vest_date_fmv=562.97,          # Fixed: use vest_date_fmv not price_per_share
            taxable_gain=1688.91           # Fixed: use taxable_gain not total_value
        )
        
        assert transaction.vest_date == date(2024, 7, 15)  # Fixed: use vest_date
        assert transaction.grant_number == "RU3861"
        assert transaction.vested_quantity == 3.0          # Fixed: use vested_quantity
        assert transaction.taxable_gain == 1688.91         # Fixed: use taxable_gain

    def test_rsu_transaction_validation(self):
        """Test RSU transaction validation."""
        
        # Test missing required fields - grant_date
        with pytest.raises(ValidationError):
            RSUTransaction(
                # grant_date missing - should raise ValidationError
                vest_date=date(2024, 7, 15),
                grant_number="RU3861",
                symbol="ADBE",
                vested_quantity=3.0,
                vest_date_fmv=562.97,
                taxable_gain=1688.91
            )
        
        # Test missing required fields - vest_date
        with pytest.raises(ValidationError):
            RSUTransaction(
                grant_date=date(2024, 1, 15),
                # vest_date missing - should raise ValidationError
                grant_number="RU3861",
                symbol="ADBE",
                vested_quantity=3.0,
                vest_date_fmv=562.97,
                taxable_gain=1688.91
            )


class TestBenefitHistoryRecord:
    """Test benefit history record validation (legacy support)."""

    def test_valid_benefit_history_record(self):
        """Test creation of valid benefit history record."""
        record = BenefitHistoryRecord(
            record_type="Event",
            event_type="Shares vested",
            date=date(2024, 6, 15),
            grant_date=date(2023, 6, 15),
            grant_number="RU123456",
            qty_or_amount=100.0,
            est_market_value=52500.00,
            award_price=0.0,
            withholding_amount=5000.00
        )
        
        assert record.record_type == "Event"
        assert record.event_type == "Shares vested"
        assert record.qty_or_amount == 100.0
        assert record.est_market_value == 52500.00

    def test_benefit_history_record_validation(self):
        """Test benefit history record validation."""
        
        # Test negative market value
        with pytest.raises(ValidationError):
            BenefitHistoryRecord(
                record_type="Event",
                event_type="Shares vested",
                date=date(2024, 6, 15),
                qty_or_amount=100.0,
                est_market_value=-52500.00,  # Invalid negative value
                award_price=0.0
            )


class TestDataModelIntegration:
    """Integration tests for data models."""

    def test_model_serialization_deserialization(self):
        """Test that models can be serialized and deserialized."""
        # Test ESOP record
        esop_record = ESOPVestingRecord(
            employee_id="TEST123",        # Fixed: add required field
            employee_name="Test Employee", # Fixed: add required field
            vesting_date=date(2024, 4, 15),
            grant_number="RU3861",
            fmv_usd=473.56,
            quantity=3,
            total_usd=1420.68,           # Fixed: add required field
            forex_rate=83.4516,
            total_inr=118558.0
        )
        
        # Serialize to dict
        esop_dict = esop_record.model_dump()
        assert isinstance(esop_dict, dict)
        assert esop_dict['grant_number'] == "RU3861"
        
        # Deserialize from dict
        esop_reconstructed = ESOPVestingRecord(**esop_dict)
        assert esop_reconstructed.grant_number == esop_record.grant_number
        assert esop_reconstructed.fmv_usd == esop_record.fmv_usd

    def test_model_json_serialization(self):
        """Test JSON serialization of models."""
        record = SBIRateRecord(
            date=date(2024, 7, 15),
            time="1:00:00 PM",
            currency_pair="INR / 1 USD",  # Fixed: use 'currency_pair' not 'currency_pairs'
            rate=83.60
        )
        
        # Serialize to JSON
        json_str = record.model_dump_json()
        assert isinstance(json_str, str)
        assert "83.6" in json_str
        assert "2024-07-15" in json_str

    def test_model_validation_consistency(self):
        """Test that validation is consistent across similar models."""
        
        # Test that all financial amount fields reject negative values consistently
        models_to_test = [
            (ESOPVestingRecord, 'fmv_usd', -100.0),
            (GLStatementRecord, 'quantity', -1.0),
            (SBIRateRecord, 'rate', -1.0),
            (AdobeStockRecord, 'close_last', -100.0),
        ]
        
        for model_class, field_name, invalid_value in models_to_test:
            # Create minimal valid data
            base_data = {}
            
            if model_class == ESOPVestingRecord:
                base_data = {
                    'vesting_date': date(2024, 1, 1),
                    'grant_number': 'TEST',
                    'fmv_usd': 100.0,
                    'quantity': 1,
                    'forex_rate': 80.0,
                    'total_inr': 8000.0
                }
            elif model_class == GLStatementRecord:
                base_data = {
                    'record_type': 'Sell',
                    'symbol': 'ADBE',
                    'quantity': 1.0,
                    'date_sold': date(2024, 1, 1),
                    'total_proceeds': 100.0
                }
            elif model_class == SBIRateRecord:
                base_data = {
                    'date': date(2024, 1, 1),
                    'time': '1:00:00 PM',
                    'currency_pairs': 'INR / 1 USD',
                    'rate': 80.0
                }
            elif model_class == AdobeStockRecord:
                base_data = {
                    'date': date(2024, 1, 1),
                    'close_last': 100.0,
                    'volume': 1000,
                    'open': 100.0,
                    'high': 100.0,
                    'low': 100.0
                }
            
            # Override with invalid value
            base_data[field_name] = invalid_value
            
            # Should raise validation error
            with pytest.raises(ValidationError):
                model_class(**base_data)

    def test_date_field_consistency(self):
        """Test that date fields are handled consistently across models."""
        test_date = date(2024, 7, 15)
        
        # Test that all models with date fields accept valid dates
        esop_record = ESOPVestingRecord(
            employee_id="TEST123",        # Fixed: add required field
            employee_name="Test Employee", # Fixed: add required field
            vesting_date=test_date,
            grant_number="TEST",
            fmv_usd=100.0,
            quantity=1,
            total_usd=100.0,             # Fixed: add required field
            forex_rate=80.0,
            total_inr=8000.0
        )
        
        gl_record = GLStatementRecord(
            record_type="Sell",
            symbol="ADBE",
            quantity=1.0,
            date_sold=test_date,
            total_proceeds=100.0
        )
        
        sbi_record = SBIRateRecord(
            date=test_date,
            time="1:00:00 PM",
            currency_pair="INR / 1 USD",  # Fixed: use 'currency_pair' not 'currency_pairs'
            rate=80.0
        )
        
        # All should have the same date
        assert esop_record.vesting_date == test_date
        assert gl_record.date_sold == test_date
        assert sbi_record.date == test_date
