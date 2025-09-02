"""RSU Calculation Engine for tax and gain/loss calculations."""

from datetime import date as Date, datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

from loguru import logger
from pydantic import BaseModel, Field

from ..data.models import (
    BenefitHistoryRecord, 
    GLStatementRecord, 
    SBIRateRecord, 
    AdobeStockRecord,
    RSUTransaction,
    RSUVestingRecord
)
from ..utils.date_utils import get_financial_year_dates
from ..utils.currency_utils import format_currency


class VestingEvent(BaseModel):
    """Represents an RSU vesting event with tax implications."""
    
    vest_date: Date
    grant_date: Date
    grant_number: str
    symbol: str = "ADBE"
    vested_quantity: float
    grant_price: float = 0.0  # RSUs typically have $0 grant price
    vest_fmv_usd: float  # Fair Market Value at vesting in USD
    vest_fmv_inr: float  # Fair Market Value at vesting in INR
    exchange_rate: float  # USD to INR rate on vest date
    taxable_gain_usd: float  # (vest_fmv - grant_price) * quantity
    taxable_gain_inr: float  # Taxable gain in INR
    taxes_withheld: Optional[float] = None  # US taxes withheld
    financial_year: str  # Indian FY (e.g., "FY2025")
    
    @property
    def is_current_fy(self) -> bool:
        """Check if this vesting is in current financial year."""
        current_date = Date.today()
        if current_date.month >= 4:  # April onwards
            start_year = current_date.year
            end_year = current_date.year + 1
            current_fy = f"FY{start_year % 100:02d}-{end_year % 100:02d}"
        else:  # Jan-Mar
            start_year = current_date.year - 1
            end_year = current_date.year
            current_fy = f"FY{start_year % 100:02d}-{end_year % 100:02d}"
        fy_start, fy_end = get_financial_year_dates(current_fy)
        return fy_start <= self.vest_date <= fy_end


class SaleEvent(BaseModel):
    """Represents an RSU sale event with capital gains implications."""
    
    sale_date: Date
    acquisition_date: Date  # When RSU was acquired (vest date)
    grant_date: Date
    grant_number: str
    order_number: str
    symbol: str = "ADBE"
    quantity_sold: float
    sale_price_usd: float  # Per share sale price in USD
    sale_proceeds_usd: float  # Total proceeds in USD
    sale_proceeds_inr: float  # Total proceeds in INR
    cost_basis_usd: float  # Cost basis (typically vest FMV)
    cost_basis_inr: float  # Cost basis in INR
    capital_gain_usd: float  # Sale proceeds - cost basis (USD)
    capital_gain_inr: float  # Capital gain in INR
    gain_type: str  # "Short-term" or "Long-term"
    exchange_rate_sale: float  # USD to INR rate on sale date
    vest_fmv_usd: float  # Original FMV per share when vested (USD)
    vest_exchange_rate: float  # Exchange rate when originally vested
    vest_fmv_inr: float  # Original FMV per share when vested (INR)
    financial_year: str  # Indian FY of sale
    
    @property
    def holding_period_days(self) -> int:
        """Calculate holding period in days."""
        return (self.sale_date - self.acquisition_date).days
    
    @property
    def is_long_term(self) -> bool:
        """Check if this is a long-term capital gain (>24 months for equity)."""
        return self.holding_period_days > (24 * 30)  # Approximate 24 months


class RSUCalculationSummary(BaseModel):
    """Summary of RSU calculations for a financial year."""
    
    financial_year: str
    
    # Vesting Summary
    total_vested_quantity: float = 0.0
    total_taxable_gain_usd: float = 0.0
    total_taxable_gain_inr: float = 0.0
    total_taxes_withheld: float = 0.0
    vesting_events_count: int = 0
    
    # Sale Summary  
    total_sold_quantity: float = 0.0
    total_sale_proceeds_usd: float = 0.0
    total_sale_proceeds_inr: float = 0.0
    total_cost_basis_usd: float = 0.0
    total_cost_basis_inr: float = 0.0
    
    # Capital Gains
    short_term_gains_usd: float = 0.0
    short_term_gains_inr: float = 0.0
    long_term_gains_usd: float = 0.0
    long_term_gains_inr: float = 0.0
    total_capital_gains_usd: float = 0.0
    total_capital_gains_inr: float = 0.0
    
    sale_events_count: int = 0
    
    # Net Position
    net_gain_loss_inr: float = 0.0  # Taxable gains + capital gains
    
    @property
    def average_exchange_rate(self) -> float:
        """Calculate weighted average exchange rate used."""
        if self.total_taxable_gain_usd > 0:
            return self.total_taxable_gain_inr / self.total_taxable_gain_usd
        return 0.0


class RSUCalculator:
    """Main RSU calculation engine."""
    
    def __init__(self, sbi_rates: List[SBIRateRecord], stock_data: List[AdobeStockRecord]):
        """Initialize RSU calculator with reference data."""
        self.sbi_rates = {rate.date: rate.rate for rate in sbi_rates}
        self.stock_data = {stock.date: stock for stock in stock_data}
        self.vesting_events: Dict[str, VestingEvent] = {}  # Store vesting events for lookup
        
        logger.info(f"Initialized RSU Calculator with {len(self.sbi_rates)} exchange rates "
                   f"and {len(self.stock_data)} stock price records")
    
    def get_exchange_rate(self, target_date: Date) -> Optional[float]:
        """Get USD to INR exchange rate for a specific date."""
        # Try exact date first
        if target_date in self.sbi_rates:
            return self.sbi_rates[target_date]
        
        # Find nearest available rate (within 7 days)
        for days_offset in range(1, 8):
            # Try previous days
            prev_date = target_date - timedelta(days=days_offset)
            if prev_date in self.sbi_rates:
                logger.debug(f"Using exchange rate from {prev_date} for {target_date}")
                return self.sbi_rates[prev_date]
            
            # Try next days  
            next_date = target_date + timedelta(days=days_offset)
            if next_date in self.sbi_rates:
                logger.debug(f"Using exchange rate from {next_date} for {target_date}")
                return self.sbi_rates[next_date]
        
        logger.warning(f"No exchange rate found for {target_date} within 7 days")
        return None
    
    def get_stock_price(self, target_date: Date) -> Optional[float]:
        """Get Adobe stock closing price for a specific date."""
        if target_date in self.stock_data:
            return self.stock_data[target_date].close_price
        
        # Find nearest trading day (within 5 business days)
        for days_offset in range(1, 8):
            prev_date = target_date - timedelta(days=days_offset)
            if prev_date in self.stock_data:
                logger.debug(f"Using stock price from {prev_date} for {target_date}")
                return self.stock_data[prev_date].close_price
        
        logger.warning(f"No stock price found for {target_date} within 7 days")
        return None
    
    def calculate_financial_year(self, transaction_date: Date) -> str:
        """Calculate Indian financial year for a given date."""
        if transaction_date.month >= 4:  # April onwards
            start_year = transaction_date.year
            end_year = transaction_date.year + 1
            return f"FY{start_year % 100:02d}-{end_year % 100:02d}"
        else:  # Jan-Mar
            start_year = transaction_date.year - 1
            end_year = transaction_date.year
            return f"FY{start_year % 100:02d}-{end_year % 100:02d}"
    
    def process_vesting_events(
        self, 
        benefit_records: List[BenefitHistoryRecord]
    ) -> List[VestingEvent]:
        """Process RSU vesting events from BenefitHistory records."""
        
        vesting_events = []
        
        # Filter for actual vesting events (not grants or other record types)
        vest_records = [
            r for r in benefit_records 
            if r.record_type in ['Event'] and r.event_type == 'Shares vested' 
            and r.date and r.qty_or_amount and r.qty_or_amount > 0
        ]
        
        logger.info(f"Found {len(vest_records)} RSU vesting events to process")
        
        for record in vest_records:
            try:
                # Get exchange rate for vest date (using date field, not vest_date)
                vest_date = record.date
                exchange_rate = self.get_exchange_rate(vest_date)
                if not exchange_rate:
                    logger.error(f"No exchange rate available for vest date {vest_date}")
                    continue
                
                # Get stock price (FMV) at vest date - try multiple sources
                vest_fmv_usd = None
                
                # First try from the record itself if available
                if hasattr(record, 'est_market_value') and record.est_market_value:
                    # Est Market Value is total value, divide by quantity for per-share FMV
                    vest_fmv_usd = record.est_market_value / record.qty_or_amount
                
                # Fallback to stock price data
                if not vest_fmv_usd:
                    vest_fmv_usd = self.get_stock_price(vest_date)
                
                if not vest_fmv_usd:
                    logger.error(f"No FMV available for vest date {vest_date}")
                    continue
                
                # Calculate taxable gain (RSUs have $0 grant price typically)
                grant_price = record.award_price or 0.0
                taxable_gain_per_share = vest_fmv_usd - grant_price
                total_taxable_gain_usd = taxable_gain_per_share * record.qty_or_amount
                total_taxable_gain_inr = total_taxable_gain_usd * exchange_rate
                
                # Create vesting event
                vesting_event = VestingEvent(
                    vest_date=vest_date,
                    grant_date=record.grant_date or vest_date,  # Fallback if grant date missing
                    grant_number=record.grant_number or "Unknown",
                    vested_quantity=record.qty_or_amount,
                    grant_price=grant_price,
                    vest_fmv_usd=vest_fmv_usd,
                    vest_fmv_inr=vest_fmv_usd * exchange_rate,
                    exchange_rate=exchange_rate,
                    taxable_gain_usd=total_taxable_gain_usd,
                    taxable_gain_inr=total_taxable_gain_inr,
                    taxes_withheld=record.withholding_amount,
                    financial_year=self.calculate_financial_year(vest_date)
                )
                
                vesting_events.append(vesting_event)
                
                logger.debug(f"Processed vesting: {record.qty_or_amount} shares on {vest_date}, "
                           f"FMV ${vest_fmv_usd:.2f}, Taxable gain ₹{total_taxable_gain_inr:,.2f}")
                
            except Exception as e:
                logger.error(f"Error processing vesting record {record.grant_number}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(vesting_events)} vesting events")
        return vesting_events
    
    def process_rsu_vesting_events(
        self,
        rsu_records: List[RSUVestingRecord]
    ) -> List[VestingEvent]:
        """Process RSU vesting events from RSU PDF records with accurate FMV and exchange rates."""
        
        # =================================================================================
        # RSU VESTING CALCULATION FORMULAS
        # =================================================================================
        # 
        # RSU Vesting Tax Treatment:
        # 1. At vesting, the Fair Market Value (FMV) becomes taxable income (NOT gain)
        # 2. This vesting income is treated as salary and taxed at regular income tax rates
        # 3. The FMV at vesting becomes the "cost basis" for future capital gains calculations
        # 4. IMPORTANT: Vesting creates income tax liability, not capital gains tax
        # 5. Capital gains tax only applies when shares are sold (difference between sale price and FMV at vesting)
        #
        # FORMULA 1: Individual Share Value (INR)
        # Purpose: Convert USD FMV to INR using exact RSU exchange rate
        # Formula: Vest_FMV_INR = Vest_FMV_USD × RSU_Exchange_Rate
        # Example: $419.49 × ₹86.3632 = ₹36,228.50 per share
        #
        # FORMULA 2: Total Vesting Income (USD)
        # Purpose: Calculate total USD value of vested shares (before tax)
        # Formula: Total_Vesting_USD = Vest_FMV_USD × Vested_Quantity
        # Example: $419.49 × 3 shares = $1,258.47
        #
        # FORMULA 3: Total Vesting Income (INR) - Primary Method
        # Purpose: Get exact INR vesting income amount from RSU document (most accurate)
        # Source: Direct from RSU PDF "Total (INR)" column
        # Note: Preferred over calculated value due to rounding precision in RSU
        #
        # FORMULA 4: Total Vesting Income (INR) - Calculated Method (Fallback)
        # Purpose: Calculate INR vesting income amount if RSU total not available
        # Formula: Total_Vesting_INR = Total_Vesting_USD × RSU_Exchange_Rate
        # Example: $1,258.47 × ₹86.3632 = ₹108,685.50
        # =================================================================================
        
        vesting_events = []
        
        logger.info(f"Found {len(rsu_records)} RSU vesting records to process")

        for record in rsu_records:
            try:
                # Extract raw data from RSU PDF (most accurate source)
                vest_date = record.vesting_date
                exchange_rate = record.forex_rate
                vest_fmv_usd = record.fmv_usd
                vested_quantity = record.quantity
                
                # APPLY FORMULAS (see documentation above)
                # Formula 1: Individual share value in INR
                vest_fmv_inr = vest_fmv_usd * exchange_rate
                
                # Formula 2: Total USD value of vested shares
                total_taxable_gain_usd = vest_fmv_usd * vested_quantity
                
                # Formula 3: Use exact INR total from RSU document (preferred)
                total_taxable_gain_inr = record.total_inr  # Most accurate - from RSU PDF
                
                vesting_event = VestingEvent(
                    vest_date=vest_date,
                    grant_date=vest_date,  # Use vesting date as grant date approximation
                    grant_number=record.grant_number,
                    vested_quantity=vested_quantity,
                    vest_fmv_usd=vest_fmv_usd,
                    vest_fmv_inr=vest_fmv_inr,
                    exchange_rate=exchange_rate,
                    taxable_gain_usd=total_taxable_gain_usd,
                    taxable_gain_inr=total_taxable_gain_inr,
                    financial_year=self.calculate_financial_year(vest_date)
                )
                
                vesting_events.append(vesting_event)
                
                # Store vesting event for lookup during sales processing
                # Use combination of vest_date and grant_number as key
                vest_key = f"{vest_date}_{record.grant_number}"
                self.vesting_events[vest_key] = vesting_event
                
                logger.debug(f"Processed RSU vesting: {record.grant_number} - {vested_quantity} shares on {vest_date}, "
                           f"FMV ${vest_fmv_usd:.2f}, Rate ₹{exchange_rate:.2f}, Taxable gain ₹{total_taxable_gain_inr:,.2f}")
                           
            except Exception as e:
                logger.error(f"Error processing RSU vesting record {record.grant_number}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(vesting_events)} RSU vesting events")
        logger.info(f"Stored {len(self.vesting_events)} vesting events for sale lookup")
        return vesting_events
    
    def get_vesting_details(self, vest_date: Date, grant_number: str) -> Optional[VestingEvent]:
        """Look up vesting details for a specific vest date and grant number."""
        vest_key = f"{vest_date}_{grant_number}"
        return self.vesting_events.get(vest_key)
    
    def process_sale_events(
        self, 
        gl_records: List[GLStatementRecord]
    ) -> List[SaleEvent]:
        """Process RSU sale events from G&L statement records."""
        
        # =================================================================================
        # RSU SALE CALCULATION FORMULAS
        # =================================================================================
        #
        # RSU Sale Tax Treatment:
        # 1. Sale proceeds are calculated using sale price and quantity
        # 2. Cost basis = FMV at vesting (already taxed as income)
        # 3. Capital gain/loss = Sale proceeds - Cost basis
        # 4. Tax treatment depends on holding period (24-month rule in India)
        #
        # FORMULA 1: Sale Proceeds (USD)
        # Purpose: Calculate total USD received from sale
        # Source: Direct from G&L "Total Proceeds" column (broker calculated)
        # Formula: Sale_Proceeds_USD = Shares_Sold × Sale_Price_Per_Share
        # Example: 3 shares × $563.31 = $1,689.93
        #
        # FORMULA 2: Sale Proceeds (INR)
        # Purpose: Convert USD sale proceeds to INR using SBI TTBR rate
        # Formula: Sale_Proceeds_INR = Sale_Proceeds_USD × Sale_Date_Exchange_Rate
        # Example: $1,689.93 × ₹83.5342 = ₹141,223
        #
        # FORMULA 3: Cost Basis (USD)
        # Purpose: Get the original cost basis (FMV at vesting)
        # Source: Direct from G&L "Adjusted Cost Basis" column (broker calculated)
        # Note: For RSUs, this equals FMV at vesting since grant price is typically $0
        # Alternative: Cost_Basis_USD = Vest_FMV_USD × Shares_Sold
        #
        # FORMULA 4: Cost Basis (INR)
        # Purpose: Convert USD cost basis to INR using sale date exchange rate
        # Formula: Cost_Basis_INR = Cost_Basis_USD × Sale_Date_Exchange_Rate
        # Example: $1,420.68 × ₹83.5342 = ₹118,558
        # Note: Uses sale date rate for consistency with proceeds calculation
        #
        # FORMULA 5: Capital Gain/Loss (USD) - Primary Method
        # Purpose: Get exact capital gain from broker calculation (most accurate)
        # Source: Direct from G&L "Adjusted Gain/Loss" column
        # Note: Preferred over manual calculation due to broker precision
        #
        # FORMULA 6: Capital Gain/Loss (USD) - Calculated Method (Fallback)
        # Purpose: Calculate gain if broker value not available
        # Formula: Capital_Gain_USD = Sale_Proceeds_USD - Cost_Basis_USD
        # Example: $1,689.93 - $1,420.68 = $269.25
        #
        # FORMULA 7: Capital Gain/Loss (INR)
        # Purpose: Convert USD capital gain to INR
        # Formula: Capital_Gain_INR = Capital_Gain_USD × Sale_Date_Exchange_Rate
        # Example: $269.25 × ₹83.5342 = ₹22,488
        #
        # FORMULA 8: Holding Period Classification
        # Purpose: Determine if gain is short-term or long-term for tax purposes
        # Formula: Holding_Days = Sale_Date - Acquisition_Date (in days)
        # Rule: Long-term if Holding_Days > (24 × 30) = 720 days, else Short-term
        # Tax Impact: 
        #   - Short-term: Taxed as regular income (salary tax rates)
        #   - Long-term: Taxed at capital gains rates (typically 10% + cess)
        # =================================================================================
        
        sale_events = []
        
        # Filter for actual sale transactions
        sale_records = [
            r for r in gl_records 
            if r.record_type == 'Sell' and r.date_sold and r.quantity and r.quantity > 0
        ]
        
        logger.info(f"Found {len(sale_records)} RSU sale events to process")
        
        for record in sale_records:
            try:
                # Get exchange rate for sale date (SBI TTBR rate)
                exchange_rate = self.get_exchange_rate(record.date_sold)
                if not exchange_rate:
                    logger.error(f"No exchange rate available for sale date {record.date_sold}")
                    continue
                
                # APPLY FORMULAS (see documentation above)
                # Formula 1: Sale proceeds from broker (most accurate)
                sale_price_per_share = record.proceeds_per_share or 0
                sale_proceeds_usd = record.total_proceeds or 0
                
                # Formula 2: Convert to INR using sale date exchange rate
                sale_proceeds_inr = sale_proceeds_usd * exchange_rate
                
                # Formula 3: Cost basis from broker (FMV at vesting)
                cost_basis_usd = record.adjusted_cost_basis or 0
                
                # Formula 4: Convert cost basis to INR using sale date rate
                cost_basis_inr = cost_basis_usd * exchange_rate
                
                # Formula 5: Use broker's calculated gain (preferred) or Formula 6 (fallback)
                capital_gain_usd = record.adjusted_gain_loss or (sale_proceeds_usd - cost_basis_usd)
                
                # Formula 7: Convert capital gain to INR
                capital_gain_inr = capital_gain_usd * exchange_rate
                
                # Formula 8: Determine holding period and tax classification
                acquisition_date = record.date_acquired or record.vest_date
                if not acquisition_date:
                    logger.warning(f"No acquisition date for sale record {record.order_number}")
                    acquisition_date = record.date_sold  # Fallback
                
                holding_days = (record.date_sold - acquisition_date).days
                gain_type = "Long-term" if holding_days > (24 * 30) else "Short-term"
                
                # Get original vesting details from stored RSU data
                vesting_details = self.get_vesting_details(acquisition_date, record.grant_number or "")
                if vesting_details:
                    # Use exact vesting data from RSU PDF
                    vest_fmv_usd = vesting_details.vest_fmv_usd
                    vest_exchange_rate = vesting_details.exchange_rate
                    vest_fmv_inr = vesting_details.vest_fmv_inr
                    logger.debug(f"Found vesting details for {acquisition_date}_{record.grant_number}: "
                               f"FMV ${vest_fmv_usd:.2f}, Rate ₹{vest_exchange_rate:.4f}")
                else:
                    # Fallback calculation if vesting details not found
                    vest_fmv_usd = cost_basis_usd / record.quantity if record.quantity > 0 else 0
                    vest_exchange_rate = self.get_exchange_rate(acquisition_date) or exchange_rate
                    vest_fmv_inr = vest_fmv_usd * vest_exchange_rate
                    logger.warning(f"Vesting details not found for {acquisition_date}_{record.grant_number}, "
                                 f"using fallback calculation")
                
                # Create sale event
                sale_event = SaleEvent(
                    sale_date=record.date_sold,
                    acquisition_date=acquisition_date,
                    grant_date=record.grant_date or acquisition_date,
                    grant_number=record.grant_number or "Unknown",
                    order_number=record.order_number or "Unknown",
                    quantity_sold=record.quantity,
                    sale_price_usd=sale_price_per_share,
                    sale_proceeds_usd=sale_proceeds_usd,
                    sale_proceeds_inr=sale_proceeds_inr,
                    cost_basis_usd=cost_basis_usd,
                    cost_basis_inr=cost_basis_inr,
                    capital_gain_usd=capital_gain_usd,
                    capital_gain_inr=capital_gain_inr,
                    gain_type=gain_type,
                    exchange_rate_sale=exchange_rate,
                    vest_fmv_usd=vest_fmv_usd,
                    vest_exchange_rate=vest_exchange_rate,
                    vest_fmv_inr=vest_fmv_inr,
                    financial_year=self.calculate_financial_year(record.date_sold)
                )
                
                sale_events.append(sale_event)
                
                logger.debug(f"Processed sale: {record.quantity} shares on {record.date_sold}, "
                           f"Proceeds ₹{sale_proceeds_inr:,.2f}, {gain_type} gain ₹{capital_gain_inr:,.2f}")
                
            except Exception as e:
                logger.error(f"Error processing sale record {record.order_number}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(sale_events)} sale events")
        return sale_events
    
    def calculate_fy_summary(
        self, 
        financial_year: str,
        vesting_events: List[VestingEvent], 
        sale_events: List[SaleEvent]
    ) -> RSUCalculationSummary:
        """Calculate summary for a specific financial year."""
        
        # Filter events for this FY
        fy_vestings = [v for v in vesting_events if v.financial_year == financial_year]
        fy_sales = [s for s in sale_events if s.financial_year == financial_year]
        
        summary = RSUCalculationSummary(financial_year=financial_year)
        
        # Aggregate vesting data
        for vesting in fy_vestings:
            summary.total_vested_quantity += vesting.vested_quantity
            summary.total_taxable_gain_usd += vesting.taxable_gain_usd
            summary.total_taxable_gain_inr += vesting.taxable_gain_inr
            if vesting.taxes_withheld:
                summary.total_taxes_withheld += vesting.taxes_withheld
            summary.vesting_events_count += 1
        
        # Aggregate sale data
        for sale in fy_sales:
            summary.total_sold_quantity += sale.quantity_sold
            summary.total_sale_proceeds_usd += sale.sale_proceeds_usd
            summary.total_sale_proceeds_inr += sale.sale_proceeds_inr
            summary.total_cost_basis_usd += sale.cost_basis_usd
            summary.total_cost_basis_inr += sale.cost_basis_inr
            summary.total_capital_gains_usd += sale.capital_gain_usd
            summary.total_capital_gains_inr += sale.capital_gain_inr
            
            # Categorize by gain type
            if sale.gain_type == "Short-term":
                summary.short_term_gains_usd += sale.capital_gain_usd
                summary.short_term_gains_inr += sale.capital_gain_inr
            else:
                summary.long_term_gains_usd += sale.capital_gain_usd
                summary.long_term_gains_inr += sale.capital_gain_inr
            
            summary.sale_events_count += 1
        
        # Calculate net position
        summary.net_gain_loss_inr = summary.total_taxable_gain_inr + summary.total_capital_gains_inr
        
        gain_loss_text = "net gain" if summary.net_gain_loss_inr >= 0 else "net loss"
        logger.info(f"Calculated summary for {financial_year}: "
                   f"₹{summary.net_gain_loss_inr:,.2f} {gain_loss_text}")
        
        return summary
