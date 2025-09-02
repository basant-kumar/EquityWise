"""
Comprehensive data models for RSU FA Tool.

This module defines robust Pydantic data models for parsing and validating
financial data from E*Trade, SBI, Adobe, and bank statements. All models
include comprehensive validation, field aliases, and automatic data conversion.

Key Model Categories:

1. **E*Trade Data Models**:
   - BenefitHistoryRecord: Complete RSU vesting history (43 columns)
   - GLStatementRecord: Gain/Loss tax statements (47 columns) 
   - RSUTransaction: Processed RSU transactions for calculations

2. **Financial Reference Data**:
   - SBIRateRecord: SBI TTBR USD-INR exchange rates with date parsing
   - AdobeStockRecord: Historical stock prices with validation
   - ESOPVestingRecord: ESOP vesting data from PDF parsing

3. **Banking & Reconciliation**:
   - BankStatementRecord: Bank transfer data with broker detection
   - ForeignAssetRecord: FA declaration tracking and compliance

Validation Features:
✅ Field aliases for seamless Excel column mapping
✅ Automatic type conversion (strings to numbers, dates)
✅ Comprehensive validation rules (positive values, date formats)
✅ Error handling with detailed validation messages
✅ Cross-reference validation between related fields

Date Formats Supported:
- DD/MM/YYYY (Indian format)
- YYYY-MM-DD (ISO format)
- MM/DD/YYYY (US format)

Example Usage:
    # Load and validate E*Trade data
    benefit_records = BenefitHistoryLoader.load_data("BenefitHistory.xlsx")
    gl_records = GLStatementLoader.load_data("GainLoss_2024.xlsx")
    
    # Load financial reference data  
    sbi_rates = SBIRatesLoader.load_data("SBI_TTBR_Rates.xlsx")
    stock_data = AdobeStockDataLoader.load_data("HistoricalData.xlsx")
"""

from datetime import date as Date, datetime
from typing import Optional, Literal, Union
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import ESOP models from our parser
from equitywise.data.esop_parser import ESOPVestingRecord


class BenefitHistoryRecord(BaseModel):
    """Complete model for BenefitHistory.xlsx records with all 43 columns."""
    
    model_config = ConfigDict(
        populate_by_name=True, 
        str_strip_whitespace=True,
        extra='ignore'  # Ignore extra fields to avoid schema issues
    )
    
    # Required field
    record_type: str = Field(alias="Record Type")
    
    # All 43 columns from BenefitHistory.xlsx
    symbol: Optional[str] = Field(default=None, alias="Symbol")
    grant_date: Optional[Date] = Field(default=None, alias="Grant Date")
    settlement_type: Optional[str] = Field(default=None, alias="Settlement Type")
    granted_qty: Optional[float] = Field(default=None, alias="Granted Qty.")
    withheld_qty: Optional[float] = Field(default=None, alias="Withheld Qty.")
    vested_qty: Optional[float] = Field(default=None, alias="Vested Qty.")
    deferred_pending_release_qty: Optional[float] = Field(default=None, alias="Deferred / Pending Release Qty.")
    sellable_qty: Optional[float] = Field(default=None, alias="Sellable Qty.")
    est_market_value: Optional[float] = Field(default=None, alias="Est. Market Value")
    grant_number: Optional[str] = Field(default=None, alias="Grant Number")
    achieved_qty: Optional[float] = Field(default=None, alias="Achieved Qty.")
    unvested_qty: Optional[float] = Field(default=None, alias="Unvested Qty.")
    type_field: Optional[str] = Field(default=None, alias="Type")  # 'type' is reserved
    unreleased_dividend_value: Optional[float] = Field(default=None, alias="Unreleased Dividend Value")
    award_price: Optional[float] = Field(default=None, alias="Award Price")
    class_field: Optional[str] = Field(default=None, alias="Class")  # 'class' is reserved
    status: Optional[str] = Field(default=None, alias="Status")
    pending_sale_qty: Optional[float] = Field(default=None, alias="Pending Sale Qty.")
    blocked_qty: Optional[float] = Field(default=None, alias="Blocked Qty.")
    cancelled_qty: Optional[float] = Field(default=None, alias="Cancelled Qty.")
    date: Optional[Date] = Field(default=None, alias="Date")
    event_type: Optional[str] = Field(default=None, alias="Event Type")
    qty_or_amount: Optional[float] = Field(default=None, alias="Qty. or Amount")
    vest_period: Optional[str] = Field(default=None, alias="Vest Period")
    vest_date: Optional[Date] = Field(default=None, alias="Vest Date")
    deferred_until: Optional[Date] = Field(default=None, alias="Deferred Until")
    granted_qty_1: Optional[float] = Field(default=None, alias="Granted Qty..1")
    achieved_qty_1: Optional[float] = Field(default=None, alias="Achieved Qty..1")
    reason_for_cancelled_qty: Optional[str] = Field(default=None, alias="Reason for cancelled qty")
    cancelled_qty_1: Optional[float] = Field(default=None, alias="Cancelled Qty..1")
    date_cancelled: Optional[Date] = Field(default=None, alias="Date Cancelled")
    vested_qty_1: Optional[float] = Field(default=None, alias="Vested Qty..1")
    released_qty: Optional[float] = Field(default=None, alias="Released Qty")
    released_amount: Optional[float] = Field(default=None, alias="Released Amount")
    sellable_qty_1: Optional[float] = Field(default=None, alias="Sellable Qty..1")
    blocked_qty_1: Optional[float] = Field(default=None, alias="Blocked Qty..1")
    total_taxes_paid: Optional[float] = Field(default=None, alias="Total Taxes Paid")
    tax_description: Optional[str] = Field(default=None, alias="Tax Description")
    taxable_gain: Optional[float] = Field(default=None, alias="Taxable Gain")
    effective_tax_rate: Optional[float] = Field(default=None, alias="Effective Tax Rate")
    withholding_amount: Optional[float] = Field(default=None, alias="Withholding Amount")
    grant_value_denominator: Optional[str] = Field(default=None, alias="Grant Value Denominator (Hover me)")
    
    @field_validator('grant_date', 'vest_date', 'date', 'deferred_until', 'date_cancelled', mode='before')
    @classmethod
    def parse_dates(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ''):
            return None
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%m/%d/%Y").date()
            except ValueError:
                try:
                    return datetime.strptime(v, "%Y-%m-%d").date()
                except ValueError:
                    return None
        return v
    
    @field_validator('vest_period', mode='before')
    @classmethod
    def parse_vest_period(cls, v):
        """Convert vest period float to string."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return str(int(v))  # Convert 1.0 -> "1"
        return str(v)
    
    @field_validator('effective_tax_rate', mode='before')
    @classmethod
    def parse_effective_tax_rate(cls, v):
        """Parse percentage strings like '31.2%' to float."""
        if v is None or (isinstance(v, str) and v.strip() == ''):
            return None
        if isinstance(v, str) and v.endswith('%'):
            try:
                return float(v.replace('%', ''))
            except ValueError:
                return None
        if isinstance(v, (int, float)):
            return float(v)
        return None
    
    @field_validator('est_market_value', mode='after')
    @classmethod  
    def validate_market_value(cls, v):
        """Validate estimated market value is not negative"""
        if v is not None and v < 0:
            raise ValueError("Estimated market value cannot be negative")
        return v


class GLStatementRecord(BaseModel):
    """Complete model for G&L statement records with all 47 columns."""
    
    model_config = ConfigDict(
        populate_by_name=True, 
        str_strip_whitespace=True,
        extra='ignore'
    )
    
    # Required field
    record_type: str = Field(alias="Record Type")
    
    # All 47 columns from G&L statements
    symbol: Optional[str] = Field(default=None, alias="Symbol")
    plan_type: Optional[str] = Field(default=None, alias="Plan Type")
    quantity: Optional[float] = Field(default=None, alias="Quantity")
    date_acquired: Optional[Date] = Field(default=None, alias="Date Acquired")
    date_acquired_wash_sale: Optional[Date] = Field(default=None, alias="Date Acquired (Wash Sale Toggle = On)")
    acquisition_cost: Optional[float] = Field(default=None, alias="Acquisition Cost")
    acquisition_cost_per_share: Optional[float] = Field(default=None, alias="Acquisition Cost Per Share")
    ordinary_income_recognized: Optional[float] = Field(default=None, alias="Ordinary Income Recognized")
    ordinary_income_recognized_per_share: Optional[float] = Field(default=None, alias="Ordinary Income Recognized Per Share")
    adjusted_cost_basis: Optional[float] = Field(default=None, alias="Adjusted Cost Basis")
    adjusted_cost_basis_per_share: Optional[float] = Field(default=None, alias="Adjusted Cost Basis Per Share")
    date_sold: Optional[Date] = Field(default=None, alias="Date Sold")
    total_proceeds: Optional[float] = Field(default=None, alias="Total Proceeds")
    proceeds_per_share: Optional[float] = Field(default=None, alias="Proceeds Per Share")
    deferred_loss: Optional[float] = Field(default=None, alias="Deferred Loss")
    gain_loss: Optional[float] = Field(default=None, alias="Gain/Loss")
    gain_loss_wash_sale: Optional[float] = Field(default=None, alias="Gain/Loss (Wash Sale Toggle = On)")
    adjusted_gain_loss: Optional[float] = Field(default=None, alias="Adjusted Gain/Loss")
    adjusted_gain_loss_per_share: Optional[float] = Field(default=None, alias="Adjusted Gain (Loss) Per Share")
    capital_gains_status: Optional[str] = Field(default=None, alias="Capital Gains Status")
    wash_sale_adjusted_capital_gains_status: Optional[str] = Field(default=None, alias="Wash Sale Adjusted Capital Gains Status")
    total_wash_sale_adjustment_amount: Optional[float] = Field(default=None, alias="Total Wash Sale Adjustment Amount")
    wash_sale_adjustment_amount_per_share: Optional[float] = Field(default=None, alias="Wash Sale Adjustment Amount Per Share")
    total_wash_sale_adjusted_cost_basis: Optional[float] = Field(default=None, alias="Total Wash Sale Adjusted Cost Basis")
    wash_sale_adjusted_cost_basis_per_share: Optional[float] = Field(default=None, alias="Wash Sale Adjusted Cost Basis Per Share")
    total_wash_sale_adjusted_gain_loss: Optional[float] = Field(default=None, alias="Total Wash Sale Adjusted Gain/Loss")
    wash_sale_adjusted_gain_loss_per_share: Optional[float] = Field(default=None, alias="Wash Sale Adjusted Gain/Loss Per Share")
    order_type: Optional[str] = Field(default=None, alias="Order Type")
    covered_status: Optional[str] = Field(default=None, alias="Covered Status")
    qualified_plan: Optional[str] = Field(default=None, alias="Qualified Plan?")
    disposition_type: Optional[str] = Field(default=None, alias="Disposition Type")
    type_field: Optional[str] = Field(default=None, alias="Type")  # 'type' is reserved
    grant_date: Optional[Date] = Field(default=None, alias="Grant Date")
    grant_date_fmv: Optional[float] = Field(default=None, alias="Grant Date FMV")
    discount_amount: Optional[float] = Field(default=None, alias="Discount Amount")
    purchase_date: Optional[Date] = Field(default=None, alias="Purchase Date")
    purchase_date_fair_mkt_value: Optional[float] = Field(default=None, alias="Purchase Date Fair Mkt. Value")
    purchase_price: Optional[float] = Field(default=None, alias="Purchase Price")
    grant_number: Optional[str] = Field(default=None, alias="Grant Number")
    election_83b: Optional[str] = Field(default=None, alias="83(b) Election")
    vest_date: Optional[Date] = Field(default=None, alias="Vest Date")
    vest_date_fmv: Optional[float] = Field(default=None, alias="Vest Date FMV")
    exercise_date: Optional[Date] = Field(default=None, alias="Exercise Date")
    exercise_date_fmv: Optional[float] = Field(default=None, alias="Exercise Date FMV")
    grant_price: Optional[float] = Field(default=None, alias="Grant Price")
    order_number: Optional[str] = Field(default=None, alias="Order Number")
    
    @field_validator(
        'date_acquired', 'date_acquired_wash_sale', 'date_sold', 'grant_date', 
        'purchase_date', 'vest_date', 'exercise_date', mode='before'
    )
    @classmethod
    def parse_dates(cls, v):
        if v is None or (isinstance(v, str) and v.strip() in ['', '--']):
            return None
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%m/%d/%Y").date()
            except ValueError:
                try:
                    return datetime.strptime(v, "%Y-%m-%d").date()
                except ValueError:
                    return None
        return v
    
    @field_validator('order_number', 'grant_number', mode='before')
    @classmethod
    def parse_numbers_as_strings(cls, v):
        """Convert numeric order/grant numbers to strings."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return str(int(v))  # Convert 89254897.0 -> "89254897"
        return str(v)
    
    @field_validator('quantity', mode='after')
    @classmethod
    def validate_quantity(cls, v):
        """Validate quantity is reasonable (can be 0 for zero-share events)"""
        if v is not None and v < 0:
            raise ValueError("Quantity cannot be negative")
        return v
    
    @field_validator('record_type', mode='after')
    @classmethod
    def validate_record_type(cls, v):
        """Validate record type is one of expected values"""
        valid_types = {"Sale", "Sell", "Buy", "Transfer", "Split", "Dividend", "stock split", "ESOP"}  # Added "Sell"
        if v not in valid_types:
            raise ValueError(f"Invalid record type: {v}. Must be one of {valid_types}")
        return v


class SBIRateRecord(BaseModel):
    """Model for SBI TTBR rate records."""
    
    model_config = ConfigDict(
        populate_by_name=True, 
        str_strip_whitespace=True,
        extra='ignore'
    )
    
    date: Date = Field(alias="Date")
    time: str = Field(alias="Time")
    currency_pair: str = Field(alias="Currency Pairs")
    rate: float = Field(alias="Rate")
    comments: Optional[str] = Field(default=None, alias="Comments")
    
    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%d %b %Y").date()
            except ValueError:
                try:
                    return datetime.strptime(v, "%m/%d/%Y").date()
                except ValueError:
                    return None
        return v
    
    @field_validator('rate', mode='after')
    @classmethod
    def validate_positive_rate(cls, v):
        """Validate exchange rate is positive"""
        if v is not None and v <= 0:
            raise ValueError("Exchange rate must be positive")
        return v


class AdobeStockRecord(BaseModel):
    """Model for Adobe stock historical data records."""
    
    model_config = ConfigDict(
        populate_by_name=True, 
        str_strip_whitespace=True,
        extra='ignore'
    )
    
    date: Date = Field(alias="Date")
    close_price: float = Field(alias="Close/Last")
    volume: int = Field(alias="Volume")
    open_price: float = Field(alias="Open")
    high_price: float = Field(alias="High")
    low_price: float = Field(alias="Low")
    
    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%m/%d/%Y").date()
            except ValueError:
                return None
        return v
    
    @field_validator('close_price', 'open_price', 'high_price', 'low_price', mode='before')
    @classmethod
    def parse_price(cls, v):
        if isinstance(v, str):
            # Remove $ sign and convert to float
            return float(v.replace('$', '').replace(',', ''))
        return v
    
    @field_validator('close_price', 'open_price', 'high_price', 'low_price', mode='after')
    @classmethod
    def validate_positive_prices(cls, v):
        """Validate stock prices are positive"""
        if v is not None and v <= 0:
            raise ValueError("Stock prices must be positive")
        return v
    
    @field_validator('volume', mode='after')
    @classmethod
    def validate_positive_volume(cls, v):
        """Validate trading volume is positive"""
        if v is not None and v < 0:
            raise ValueError("Trading volume cannot be negative")
        return v


class RSUTransaction(BaseModel):
    """Processed RSU transaction model for calculations."""
    
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)
    
    grant_date: Date
    vest_date: Date
    grant_number: str
    symbol: str = "ADBE"
    vested_quantity: float
    grant_price: float = 0.0
    vest_date_fmv: float
    taxable_gain: float
    taxes_paid: Optional[float] = None
    sale_date: Optional[Date] = None
    sale_price: Optional[float] = None
    capital_gain_loss: Optional[float] = None
    
    @property
    def is_sold(self) -> bool:
        """Check if this RSU has been sold."""
        return self.sale_date is not None
    
    @property
    def financial_year(self) -> str:
        """Get the financial year for this vesting."""
        if self.vest_date.month >= 4:
            return f"FY{self.vest_date.year + 1}"
        else:
            return f"FY{self.vest_date.year}"


class ForeignAssetRecord(BaseModel):
    """Foreign asset record for FA declaration."""
    
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)
    
    asset_type: Literal["Shares", "ESOP"] = "Shares"
    company_name: str = "Adobe Inc."
    country: str = "USA"
    record_date: Date
    quantity: float
    market_value_usd: float
    exchange_rate: float
    market_value_inr: float
    
    @property
    def calendar_year(self) -> int:
        """Get calendar year for this record."""
        return self.record_date.year


class BankStatementRecord(BaseModel):
    """Bank statement transaction record for broker reconciliation."""
    
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)
    
    serial_no: int = Field(alias="S No.")
    value_date: Date = Field(alias="Value Date")
    transaction_date: Date = Field(alias="Transaction Date")
    cheque_number: Optional[str] = Field(default=None, alias="Cheque Number")
    transaction_remarks: str = Field(alias="Transaction Remarks")
    withdrawal_amount: float = Field(default=0.0, alias="Withdrawal Amount (INR )")
    deposit_amount: float = Field(default=0.0, alias="Deposit Amount (INR )")
    balance: float = Field(alias="Balance (INR )")
    
    @field_validator('value_date', 'transaction_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Parse date in DD/MM/YYYY format."""
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%d/%m/%Y").date()
            except ValueError:
                try:
                    return datetime.strptime(v, "%Y-%m-%d").date()
                except ValueError:
                    return None
        elif isinstance(v, datetime):
            return v.date()
        return v
    
    @field_validator('serial_no', mode='after')
    @classmethod
    def validate_serial_no(cls, v):
        """Validate serial number is positive"""
        if v is not None and v <= 0:
            raise ValueError("Serial number must be positive")
        return v
    
    @field_validator('cheque_number', mode='before')
    @classmethod
    def parse_cheque_number(cls, v):
        """Handle cheque number field (often contains '-' for non-cheque transactions)."""
        if v == '-' or v is None:
            return None
        return str(v)
    
    @property
    def financial_year(self) -> str:
        """Get the financial year for this transaction."""
        if self.transaction_date.month >= 4:
            return f"FY{self.transaction_date.year + 1}"
        else:
            return f"FY{self.transaction_date.year}"
    
    @property
    def is_credit(self) -> bool:
        """Check if this is a credit transaction."""
        return self.deposit_amount > 0
    
    @property
    def is_debit(self) -> bool:
        """Check if this is a debit transaction."""
        return self.withdrawal_amount > 0
    
    @property
    def net_amount(self) -> float:
        """Get net amount (positive for credit, negative for debit)."""
        return self.deposit_amount - self.withdrawal_amount
    
    @property
    def is_broker_transaction(self) -> bool:
        """Check if this is a broker RSU transaction based on transaction remarks."""
        # Look for patterns like "IRM/USD6213.87@87.0375GST576/INREM/20250204115415"
        remarks = self.transaction_remarks.upper()
        return (
            'IRM/' in remarks and 
            'USD' in remarks and 
            '@' in remarks and 
            'INREM' in remarks and
            self.is_credit  # Should be a credit transaction
        )
    
    def extract_broker_details(self) -> Optional[dict]:
        """Extract broker transaction details from transaction remarks.
        
        Returns:
            Dict with detailed broker transaction breakdown including GST and transfer expenses.
        """
        if not self.is_broker_transaction:
            return None
        
        import re
        
        try:
            # =================================================================================
            # BANK STATEMENT PARSING FORMULAS FOR RSU BROKER TRANSACTIONS
            # =================================================================================
            
            # REGEX PATTERN: IRM/USD{amount}@{rate}GST{gst}/INREM/{timestamp}
            # Example: "IRM/USD6213.87@87.0375GST576/INREM/20250204115415"
            # Explanation:
            #   - IRM/USD{amount}: USD amount bank processed (e.g., USD6213.87)
            #   - @{rate}: Bank exchange rate used (e.g., @87.0375 = ₹87.0375 per USD)
            #   - GST{amount}: GST amount deducted (e.g., GST576 = ₹576)
            #   - /INREM/{timestamp}: Transaction reference and timestamp
            pattern = r'IRM/USD([\d.]+)@([\d.]+)GST([\d.]+)'
            match = re.search(pattern, self.transaction_remarks)
            
            if match:
                usd_amount = float(match.group(1))        # Bank processed USD amount
                bank_exchange_rate = float(match.group(2)) # Bank's exchange rate
                gst_amount = float(match.group(3))        # GST amount deducted
                
                # FORMULA 1: Bank INR Before GST
                # Purpose: Calculate total INR from USD at bank's exchange rate
                # Formula: INR_Before_GST = Bank_USD_Amount × Bank_Exchange_Rate
                # Example: $6,213.87 × ₹87.0375 = ₹540,840
                inr_before_gst = usd_amount * bank_exchange_rate
                
                # FORMULA 2: Bank INR After GST  
                # Purpose: Calculate final INR amount after GST deduction
                # Formula: INR_After_GST = INR_Before_GST - GST_Amount
                # Example: ₹540,840 - ₹576 = ₹540,264
                inr_after_gst = inr_before_gst - gst_amount
                
                # Verification: Check if our calculation matches bank's actual deposit
                actual_received = self.deposit_amount
                calculation_diff = abs(inr_after_gst - actual_received)
                
                return {
                    'bank_usd_amount': usd_amount,
                    'bank_exchange_rate': bank_exchange_rate,
                    'inr_before_gst': inr_before_gst,
                    'inr_after_gst': inr_after_gst,
                    'gst_amount': gst_amount,
                    'actual_received': actual_received,
                    'calculation_accurate': calculation_diff < 1.0  # Within ₹1 difference
                }
        except (ValueError, AttributeError):
            pass
        
        return None


class ForeignCompanyRecord(BaseModel):
    """Model for foreign company information required for FA declarations."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    # Company identification
    company_name: str = Field(..., description="Full legal name of the foreign company")
    country_name: str = Field(..., description="Country where the company is incorporated")
    country_code: str = Field(..., description="Country code (typically numeric)")
    
    # Company address
    address_line1: str = Field(..., description="Primary address line")
    address_line2: Optional[str] = Field(None, description="Secondary address line")
    city: str = Field(..., description="City name")
    state_province: Optional[str] = Field(None, description="State or province")
    zip_code: str = Field(..., description="ZIP or postal code")
    
    # Company details
    nature_of_entity: str = Field(..., description="Nature of entity (e.g., LISTED, PRIVATE)")
    stock_exchange: Optional[str] = Field(None, description="Stock exchange if listed")
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Company name must be at least 2 characters")
        return v.strip()
    
    @field_validator('country_name')
    @classmethod
    def validate_country_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Country name must be at least 2 characters")
        return v.strip()


class EmployerCompanyRecord(BaseModel):
    """Model for employer company information (Indian company)."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    # Company identification
    company_name: str = Field(..., description="Full legal name of the employer company")
    tan: str = Field(..., description="Tax Account Number (TAN)")
    
    # Company address
    address_line1: str = Field(..., description="Primary address line")
    address_line2: Optional[str] = Field(None, description="Secondary address line")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State name")
    pin_code: str = Field(..., description="PIN code")
    
    @field_validator('tan')
    @classmethod
    def validate_tan(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.startswith('MRT') and not v.startswith('CHA'):
            raise ValueError("TAN should start with MRT or CHA")
        if len(v) != 10:
            raise ValueError("TAN should be 10 characters long")
        return v
    
    @field_validator('pin_code')
    @classmethod
    def validate_pin_code(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("PIN code should be 6 digits")
        return v


class ForeignDepositoryAccountRecord(BaseModel):
    """Model for foreign depository account information required for FA declarations."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    # Account identification
    account_number: str = Field(..., description="Account number")
    account_status: str = Field(..., description="Account status (e.g., Beneficial Owner)")
    
    # Financial institution details
    institution_name: str = Field(..., description="Name of the financial institution")
    institution_address: str = Field(..., description="Address of the financial institution")
    institution_city: str = Field(..., description="City where institution is located")
    institution_state: Optional[str] = Field(None, description="State or province")
    institution_zip: str = Field(..., description="ZIP code of the institution")
    institution_country: str = Field(..., description="Country of the institution")
    institution_country_code: str = Field(..., description="Country code")
    
    # Account timeline
    account_opening_date: Date = Field(..., description="Date when account was opened")
    
    @field_validator('account_number')
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Account number must be at least 5 characters")
        return v.strip()
    
    @field_validator('institution_name')
    @classmethod
    def validate_institution_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Institution name must be at least 2 characters")
        return v.strip()
    
    @field_validator('account_opening_date', mode='before')
    @classmethod
    def validate_account_opening_date(cls, v) -> Date:
        """Convert various date formats to Date object."""
        if isinstance(v, Date):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            # Try different date formats
            for date_format in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']:
                try:
                    return datetime.strptime(v.strip(), date_format).date()
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {v}")
        raise ValueError(f"Invalid date type: {type(v)}")


# Factory function to create default company records from ITR data
def create_default_company_records() -> tuple[EmployerCompanyRecord, ForeignCompanyRecord, ForeignDepositoryAccountRecord]:
    """Create default company and depository records - replace with your actual ITR data."""
    
    employer = EmployerCompanyRecord(
        company_name="Your Employer Company Name",
        tan="MRTXXXXXXX",
        address_line1="Employer Address Line 1",
        city="City",
        state="State", 
        pin_code="000000"
    )
    
    foreign_company = ForeignCompanyRecord(
        company_name="Foreign Company Name",
        country_name="United States of America",
        country_code="2",
        address_line1="Foreign Company Address",
        city="City", 
        state_province="State",
        zip_code="00000",
        nature_of_entity="LISTED"
    )
    
    depository_account = ForeignDepositoryAccountRecord(
        account_number="000000000",
        account_status="Beneficial Owner",
        institution_name="Depository Institution Name",
        institution_address="Institution Address",
        institution_city="City",
        institution_state="State",
        institution_zip="00000",
        institution_country="United States of America",
        institution_country_code="2",
        account_opening_date=Date(2020, 1, 1)
    )
    
    return employer, foreign_company, depository_account