"""Foreign Assets Calculator for Indian tax compliance."""

from datetime import date as Date, datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from ..data.models import (
    BenefitHistoryRecord, 
    GLStatementRecord, 
    SBIRateRecord, 
    AdobeStockRecord,
    RSUVestingRecord
)
from ..utils.date_utils import get_calendar_year_dates
from ..utils.currency_utils import format_currency


class VestWiseDetails(BaseModel):
    """Details for individual vesting events - required for FA compliance reporting."""
    
    # Basic vesting information
    vest_date: Date = Field(description="Date of acquiring the interest (vesting date)")
    grant_number: str = Field(description="Grant number for tracking")
    initial_shares: float = Field(description="Number of shares initially vested")
    
    # Initial value at vesting
    initial_value_usd: float = Field(description="Initial value in USD at vesting")
    initial_value_inr: float = Field(description="Initial value in INR at vesting")
    initial_stock_price: float = Field(description="Stock price at vesting")
    initial_exchange_rate: float = Field(description="Exchange rate at vesting")
    
    # Peak value during the calendar year
    peak_value_inr: float = Field(description="Peak value during the CL year")
    peak_date: Optional[Date] = Field(default=None, description="Date when peak value occurred")
    peak_stock_price: float = Field(default=0.0, description="Stock price at peak")
    peak_exchange_rate: float = Field(default=0.0, description="Exchange rate at peak")
    
    # Closing value at end of calendar year
    closing_shares: float = Field(description="Remaining shares at CL year end (after any sales)")
    closing_value_inr: float = Field(description="Closing value at CL year end")
    closing_stock_price: float = Field(default=0.0, description="Stock price at CL year end")
    closing_exchange_rate: float = Field(default=0.0, description="Exchange rate at CL year end")
    
    # Income and sales
    gross_income_received: float = Field(default=0.0, description="Dividends/interest received (usually 0 for stocks)")
    shares_sold: float = Field(default=0.0, description="Number of shares sold from this vest during CL year")
    gross_proceeds_inr: float = Field(default=0.0, description="Total proceeds from sale of shares from this vest")
    
    # Status tracking
    fully_sold: bool = Field(default=False, description="Whether all shares from this vest were sold")


class EquityHolding(BaseModel):
    """Represents an equity holding for FA declaration."""
    
    holding_date: Date
    symbol: str = "ADBE"
    quantity: float
    cost_basis_usd_per_share: float
    market_value_usd_per_share: float
    cost_basis_usd_total: float
    market_value_usd_total: float
    cost_basis_inr_total: float
    market_value_inr_total: float
    exchange_rate: float
    holding_type: str  # "Vested", "Unvested", "Sold"
    grant_date: Optional[Date] = None
    grant_number: Optional[str] = None
    vest_date: Optional[Date] = None
    calendar_year: str
    
    @property
    def unrealized_gain_usd(self) -> float:
        """Calculate unrealized gain in USD."""
        return self.market_value_usd_total - self.cost_basis_usd_total
    
    @property
    def unrealized_gain_inr(self) -> float:
        """Calculate unrealized gain in INR."""
        return self.unrealized_gain_usd * self.exchange_rate


class FADeclarationSummary(BaseModel):
    """Summary of Foreign Assets for declaration purposes."""
    
    declaration_date: Date
    calendar_year: str
    
    # Share Summary for CL year (only vested shares matter for FA)
    total_vested_shares: float = 0.0      # Currently held shares (vested - sold) 
    total_vested_ever: float = 0.0        # All shares vested historically
    total_sold_in_cl: float = 0.0         # Shares sold during CL year
    total_sold_ever: float = 0.0          # All shares sold historically
    
    # Vested holdings value (unvested not relevant for FA)
    vested_holdings_usd: float = 0.0
    vested_holdings_inr: float = 0.0
    
    # Balance tracking for FA compliance (Key FA reporting requirements)
    opening_balance_inr: float = Field(default=0.0, description="Opening balance from initial vesting date (₹)")
    closing_balance_inr: float = Field(default=0.0, description="Closing balance as of Dec 31 (₹)")
    peak_balance_inr: float = Field(default=0.0, description="Peak balance during the year (₹)")
    peak_balance_date: Optional[Date] = Field(default=None, description="Date when peak balance occurred")
    
    # Exchange rates for different balance calculations
    opening_exchange_rate: float = Field(default=0.0, description="Exchange rate on initial vesting date")
    year_end_exchange_rate: float = Field(default=0.0, description="Exchange rate on Dec 31")
    peak_exchange_rate: float = Field(default=0.0, description="Exchange rate when peak occurred")
    
    # Stock prices for different balance calculations
    opening_stock_price: float = Field(default=0.0, description="Stock price on initial vesting date")
    year_end_stock_price: float = Field(default=0.0, description="Stock price on Dec 31")
    peak_stock_price: float = Field(default=0.0, description="Stock price when peak occurred")
    
    # Share counts for different balance calculations
    opening_shares: float = Field(default=0.0, description="Share count on initial vesting date")
    closing_shares: float = Field(default=0.0, description="Share count on Dec 31")
    peak_shares: float = Field(default=0.0, description="Share count when peak occurred")
    
    # Compliance thresholds (as per Indian tax law)
    fa_declaration_threshold_inr: float = Field(default=200000.0, description="₹2 lakh threshold for FA declaration")
    
    # Vest-wise details for compliance reporting
    vest_wise_details: List[VestWiseDetails] = Field(default_factory=list, description="Individual vesting event details")
    
    @property
    def exceeds_declaration_threshold(self) -> bool:
        """Check if peak balance exceeds declaration threshold."""
        # Use peak balance as it represents the highest value during the year
        return self.peak_balance_inr > self.fa_declaration_threshold_inr
    
    @property
    def declaration_required(self) -> bool:
        """Determine if FA declaration is required based on peak balance."""
        # FA declaration required if peak balance (vested only) exceeds ₹2 lakh threshold
        return self.peak_balance_inr >= self.fa_declaration_threshold_inr


class FACalculationResults(BaseModel):
    """Complete Foreign Assets calculation results."""
    
    calculation_date: Date
    calendar_year: str
    
    # Source Data Summary  
    benefit_history_records: int = 0
    stock_price_records: int = 0
    sbi_rate_records: int = 0
    
    # Processed Holdings
    equity_holdings: List[EquityHolding] = []
    
    # Calendar Year Summaries
    year_summaries: Dict[str, FADeclarationSummary] = {}
    
    # Overall Summary
    total_years_analyzed: int = 0
    years_requiring_declaration: List[str] = []
    
    @property
    def available_calendar_years(self) -> List[str]:
        """Get list of calendar years with equity holdings."""
        return list(self.year_summaries.keys())


class FACalculator:
    """Foreign Assets calculator for Indian tax compliance."""
    
    def __init__(self, sbi_rates: List[SBIRateRecord], stock_data: List[AdobeStockRecord]):
        """Initialize FA calculator with reference data."""
        self.sbi_rates = {rate.date: rate.rate for rate in sbi_rates}
        self.stock_data = {stock.date: stock for stock in stock_data}
        
        logger.info(f"Initialized FA Calculator with {len(self.sbi_rates)} exchange rates "
                   f"and {len(self.stock_data)} stock price records")
    
    def get_year_end_exchange_rate(self, calendar_year: str) -> Optional[float]:
        """Get USD to INR exchange rate for December 31st of given year."""
        try:
            year = int(calendar_year)
            year_end_date = Date(year, 12, 31)
            
            # Try exact date first
            if year_end_date in self.sbi_rates:
                return self.sbi_rates[year_end_date]
            
            # Find nearest rate around year-end (within 15 days)
            for days_offset in range(1, 16):
                # Try previous days (likely business days before New Year)
                prev_date = year_end_date - timedelta(days=days_offset)
                if prev_date in self.sbi_rates:
                    logger.debug(f"Using exchange rate from {prev_date} for {calendar_year} year-end")
                    return self.sbi_rates[prev_date]
                
                # Try next days (early January)
                next_date = year_end_date + timedelta(days=days_offset)
                if next_date in self.sbi_rates:
                    logger.debug(f"Using exchange rate from {next_date} for {calendar_year} year-end")
                    return self.sbi_rates[next_date]
            
            # Fallback: If requested year is before our data range, use earliest available rate
            if self.sbi_rates:
                earliest_date = min(self.sbi_rates.keys())
                latest_date = max(self.sbi_rates.keys())
                
                if year_end_date < earliest_date:
                    earliest_rate = self.sbi_rates[earliest_date]
                    logger.warning(f"No exchange rate data for {calendar_year}. Using earliest available rate "
                                 f"from {earliest_date} (₹{earliest_rate:.4f}) as fallback")
                    return earliest_rate
                elif year_end_date > latest_date:
                    latest_rate = self.sbi_rates[latest_date] 
                    logger.warning(f"No exchange rate data for {calendar_year}. Using latest available rate "
                                 f"from {latest_date} (₹{latest_rate:.4f}) as fallback")
                    return latest_rate
            
            logger.warning(f"No year-end exchange rate found for {calendar_year}")
            return None
            
        except ValueError:
            logger.error(f"Invalid calendar year format: {calendar_year}")
            return None
    
    def get_year_end_stock_price(self, calendar_year: str) -> Optional[float]:
        """Get Adobe stock closing price for December 31st of given year."""
        try:
            year = int(calendar_year)
            year_end_date = Date(year, 12, 31)
            
            # Try exact date first  
            if year_end_date in self.stock_data:
                return self.stock_data[year_end_date].close_price
            
            # Find nearest trading day around year-end
            for days_offset in range(1, 10):
                # Try previous days (likely last trading day of year)
                prev_date = year_end_date - timedelta(days=days_offset)
                if prev_date in self.stock_data:
                    logger.debug(f"Using stock price from {prev_date} for {calendar_year} year-end")
                    return self.stock_data[prev_date].close_price
            
            # Fallback: Use earliest or latest available price if year is outside data range
            if self.stock_data:
                earliest_date = min(self.stock_data.keys())
                latest_date = max(self.stock_data.keys())
                
                if year_end_date < earliest_date:
                    earliest_price = self.stock_data[earliest_date].close_price
                    logger.warning(f"No stock price data for {calendar_year}. Using earliest available price "
                                 f"from {earliest_date} (${earliest_price:.2f}) as fallback")
                    return earliest_price
                elif year_end_date > latest_date:
                    latest_price = self.stock_data[latest_date].close_price
                    logger.warning(f"No stock price data for {calendar_year}. Using latest available price "
                                 f"from {latest_date} (${latest_price:.2f}) as fallback")
                    return latest_price
            
            logger.warning(f"No year-end stock price found for {calendar_year}")
            return None
        
        except ValueError:
            logger.error(f"Invalid calendar year format: {calendar_year}")
            return None
    
    def get_date_specific_exchange_rate(self, target_date: Date) -> Optional[float]:
        """Get USD to INR exchange rate for a specific date."""
        # Try exact date first
        if target_date in self.sbi_rates:
            return self.sbi_rates[target_date]
        
        # Find nearest rate (within 15 days)
        for days_offset in range(1, 16):
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
        
        # Fallback: Use earliest or latest available if outside data range
        if self.sbi_rates:
            earliest_date = min(self.sbi_rates.keys())
            latest_date = max(self.sbi_rates.keys())
            
            if target_date < earliest_date:
                earliest_rate = self.sbi_rates[earliest_date]
                logger.warning(f"No exchange rate data for {target_date}. Using earliest available rate "
                             f"from {earliest_date} (₹{earliest_rate:.4f}) as fallback")
                return earliest_rate
            elif target_date > latest_date:
                latest_rate = self.sbi_rates[latest_date]
                logger.warning(f"No exchange rate data for {target_date}. Using latest available rate "
                             f"from {latest_date} (₹{latest_rate:.4f}) as fallback")
                return latest_rate
        
        logger.warning(f"No exchange rate found for {target_date}")
        return None
    
    def get_date_specific_stock_price(self, target_date: Date) -> Optional[float]:
        """Get Adobe stock closing price for a specific date."""
        # Try exact date first
        if target_date in self.stock_data:
            return self.stock_data[target_date].close_price
        
        # Find nearest trading day (within 10 days)
        for days_offset in range(1, 11):
            # Try previous days (more likely to be trading days)
            prev_date = target_date - timedelta(days=days_offset)
            if prev_date in self.stock_data:
                logger.debug(f"Using stock price from {prev_date} for {target_date}")
                return self.stock_data[prev_date].close_price
                
            # Try next days
            next_date = target_date + timedelta(days=days_offset)
            if next_date in self.stock_data:
                logger.debug(f"Using stock price from {next_date} for {target_date}")
                return self.stock_data[next_date].close_price
        
        # Fallback: Use earliest or latest available if outside data range
        if self.stock_data:
            earliest_date = min(self.stock_data.keys())
            latest_date = max(self.stock_data.keys())
            
            if target_date < earliest_date:
                earliest_price = self.stock_data[earliest_date].close_price
                logger.warning(f"No stock price data for {target_date}. Using earliest available price "
                             f"from {earliest_date} (${earliest_price:.2f}) as fallback")
                return earliest_price
            elif target_date > latest_date:
                latest_price = self.stock_data[latest_date].close_price
                logger.warning(f"No stock price data for {target_date}. Using latest available price "
                             f"from {latest_date} (${latest_price:.2f}) as fallback")
                return latest_price
        
        logger.warning(f"No stock price found for {target_date}")
        return None
    
    def calculate_calendar_year(self, target_date: Date) -> str:
        """Calculate calendar year for a given date."""
        return str(target_date.year)
    
    def process_equity_holdings(
        self, 
        benefit_records: List[BenefitHistoryRecord],
        as_of_date: Optional[Date] = None
    ) -> List[EquityHolding]:
        """Process equity holdings from BenefitHistory records."""
        
        if not as_of_date:
            as_of_date = Date.today()
        
        calendar_year = self.calculate_calendar_year(as_of_date)
        
        logger.info(f"Processing equity holdings as of {as_of_date} for calendar year {calendar_year}")
        
        # Get date-specific rates for accurate valuation  
        year_end_exchange_rate = self.get_date_specific_exchange_rate(as_of_date)
        year_end_stock_price = self.get_date_specific_stock_price(as_of_date)
        
        if not year_end_exchange_rate:
            logger.error(f"No year-end exchange rate available for {calendar_year} (even with fallbacks)")
            return []
        
        if not year_end_stock_price:
            logger.error(f"No year-end stock price available for {calendar_year} (even with fallbacks)")
            return []
        
        equity_holdings = []
        
        # Group records by grant to track holdings
        grants = defaultdict(list)
        for record in benefit_records:
            if record.grant_number:
                grants[record.grant_number].append(record)
        
        logger.info(f"Found {len(grants)} unique grants to analyze")
        
        for grant_number, grant_records in grants.items():
            try:
                # Find grant details
                grant_record = next((r for r in grant_records if r.record_type == "Grant"), None)
                if not grant_record:
                    logger.debug(f"No grant record found for {grant_number}")
                    continue
                
                # Calculate current holding status as of target date
                total_granted = sum(r.granted_qty or 0 for r in grant_records if r.record_type == "Grant")
                total_vested = sum(r.vested_qty or r.qty_or_amount or 0 for r in grant_records 
                                if r.record_type == "Event" and r.event_type == "RSU Vest" 
                                and r.vest_date and r.vest_date <= as_of_date)
                total_sold = 0  # Will be calculated from G&L data separately
                
                # Current vested but not sold shares
                current_vested_shares = max(0, total_vested - total_sold)
                
                # Current unvested shares (granted but not yet vested as of target date)
                current_unvested_shares = total_granted - total_vested
                
                if current_vested_shares > 0:
                    # Calculate cost basis for vested shares (typically $0 for RSUs or vest FMV)
                    cost_basis_per_share = grant_record.award_price or 0.0
                    
                    # Create vested holding
                    vested_holding = EquityHolding(
                        holding_date=as_of_date,
                        quantity=current_vested_shares,
                        cost_basis_usd_per_share=cost_basis_per_share,
                        market_value_usd_per_share=year_end_stock_price,
                        cost_basis_usd_total=cost_basis_per_share * current_vested_shares,
                        market_value_usd_total=year_end_stock_price * current_vested_shares,
                        cost_basis_inr_total=(cost_basis_per_share * current_vested_shares) * year_end_exchange_rate,
                        market_value_inr_total=(year_end_stock_price * current_vested_shares) * year_end_exchange_rate,
                        exchange_rate=year_end_exchange_rate,
                        holding_type="Vested",
                        grant_date=grant_record.grant_date,
                        grant_number=grant_number,
                        calendar_year=calendar_year
                    )
                    
                    equity_holdings.append(vested_holding)
                    
                    logger.debug(f"Vested holding: {current_vested_shares} shares of {grant_number}, "
                               f"value ₹{vested_holding.market_value_inr_total:,.2f}")
                
                if current_unvested_shares > 0:
                    # Create unvested holding (usually not counted for FA declaration)
                    unvested_holding = EquityHolding(
                        holding_date=as_of_date,
                        quantity=current_unvested_shares,
                        cost_basis_usd_per_share=0.0,  # Not yet owned
                        market_value_usd_per_share=year_end_stock_price,
                        cost_basis_usd_total=0.0,
                        market_value_usd_total=year_end_stock_price * current_unvested_shares,
                        cost_basis_inr_total=0.0,
                        market_value_inr_total=(year_end_stock_price * current_unvested_shares) * year_end_exchange_rate,
                        exchange_rate=year_end_exchange_rate,
                        holding_type="Unvested",
                        grant_date=grant_record.grant_date,
                        grant_number=grant_number,
                        calendar_year=calendar_year
                    )
                    
                    equity_holdings.append(unvested_holding)
                    
                    logger.debug(f"Unvested holding: {current_unvested_shares} shares of {grant_number}, "
                               f"potential value ₹{unvested_holding.market_value_inr_total:,.2f}")
                
            except Exception as e:
                logger.error(f"Error processing grant {grant_number}: {e}")
                continue
        
        logger.info(f"Processed {len(equity_holdings)} equity holdings")
        return equity_holdings
    
    def process_rsu_equity_holdings(
        self,
        rsu_records: List[RSUVestingRecord],
        gl_records: List[GLStatementRecord],
        as_of_date: Optional[Date] = None
    ) -> List[EquityHolding]:
        """Process equity holdings using RSU PDF vesting data for accurate cost basis calculation."""
        
        # =================================================================================
        # FOREIGN ASSETS (FA) EQUITY HOLDINGS CALCULATION FORMULAS
        # =================================================================================
        #
        # Foreign Assets reporting for RSU equity holdings requires:
        # 1. Current holding quantity (shares still owned)
        # 2. Market value at specific dates (opening, peak, closing)
        # 3. FIFO cost basis calculation for remaining shares
        # 4. Accurate exchange rates for each valuation date
        #
        # FORMULA 1: Current Holdings by Grant
        # Purpose: Calculate remaining shares for each grant after sales
        # Formula: Current_Holding = Total_Vested_Shares - Total_Sold_Shares
        # Example: 5 vested - 2 sold = 3 shares remaining
        # Note: Cannot go below 0 (partial sales tracked by grant)
        #
        # FORMULA 2: Total Vested Shares per Grant
        # Purpose: Sum all vesting events for a specific grant number
        # Formula: Total_Vested = Σ(Vesting_Quantity) for same grant_number
        # Example: 2 shares (Jan) + 3 shares (Jul) = 5 total vested
        # Source: RSU PDF records grouped by grant number
        #
        # FORMULA 3: Total Sold Shares per Grant
        # Purpose: Sum all sale events for a specific grant number
        # Formula: Total_Sold = Σ(Sale_Quantity) for same grant_number where Sale_Date <= As_Of_Date
        # Example: 1 share (Mar) + 1 share (Nov) = 2 total sold
        # Source: G&L statement records filtered by date and grant
        #
        # FORMULA 4: FIFO Cost Basis Calculation
        # Purpose: Calculate weighted average cost basis for remaining shares using FIFO
        # Method: Use earliest vesting events first to determine cost basis
        # Steps:
        #   a) Sort vesting records by date (earliest first)
        #   b) For each vesting, allocate shares to remaining holding
        #   c) Cost_Contribution = min(Remaining_Shares, Vesting_Quantity) × Vesting_FMV_USD
        #   d) Total_Cost_Basis_USD = Σ(Cost_Contribution)
        # Example: 3 remaining shares from earliest vestings at $400, $450, $500 = cost basis
        #
        # FORMULA 5: Average Cost Basis per Share
        # Purpose: Calculate weighted average cost per share for valuation
        # Formula: Avg_Cost_Per_Share = Total_Cost_Basis_USD ÷ Current_Holding
        # Example: $1,350 cost basis ÷ 3 shares = $450 per share average cost
        # Note: Used for FA reporting and capital gains calculations
        #
        # FORMULA 6: Market Value at Specific Date
        # Purpose: Calculate current market value for FA reporting
        # Formula: Market_Value_USD = Current_Holding × Stock_Price_At_Date
        # Formula: Market_Value_INR = Market_Value_USD × Exchange_Rate_At_Date
        # Example: 3 shares × $520 × ₹83.50 = ₹130,260
        # Note: Requires date-specific stock prices and exchange rates
        # =================================================================================
        
        if not as_of_date:
            as_of_date = Date.today()
        
        calendar_year = self.calculate_calendar_year(as_of_date)
        
        logger.info(f"Processing RSU equity holdings as of {as_of_date} for calendar year {calendar_year}")
        
        # Get date-specific rates for accurate valuation (Formula 6 inputs)
        year_end_exchange_rate = self.get_date_specific_exchange_rate(as_of_date)
        year_end_stock_price = self.get_date_specific_stock_price(as_of_date)
        
        if not year_end_exchange_rate:
            logger.error(f"No year-end exchange rate available for {calendar_year} (even with fallbacks)")
            return []
        
        if not year_end_stock_price:
            logger.error(f"No year-end stock price available for {calendar_year} (even with fallbacks)")
            return []
        
        # Filter vesting records that occurred before or on the as_of_date
        relevant_vestings = [r for r in rsu_records if r.vesting_date <= as_of_date]
        logger.info(f"Found {len(relevant_vestings)} vesting events before {as_of_date}")
        
        # APPLY FORMULA 3: Calculate total sold shares by grant
        sold_shares_by_grant = defaultdict(float)
        for gl_record in gl_records:
            if gl_record.date_sold <= as_of_date and gl_record.grant_number:
                sold_shares_by_grant[gl_record.grant_number] += gl_record.quantity or 0
        
        logger.info(f"Calculated sold shares for {len(sold_shares_by_grant)} grants from G&L data")
        
        # Group vesting records by grant for analysis (Formula 2 preparation)
        grants_vestings = defaultdict(list)
        for record in relevant_vestings:
            grants_vestings[record.grant_number].append(record)
        
        equity_holdings = []
        
        for grant_number, vesting_records in grants_vestings.items():
            try:
                # APPLY FORMULA 2: Calculate total vested shares for this grant
                total_vested_shares = sum(r.quantity for r in vesting_records)
                total_sold_shares = sold_shares_by_grant.get(grant_number, 0.0)
                
                # APPLY FORMULA 1: Current holding calculation
                current_holding = max(0.0, total_vested_shares - total_sold_shares)
                
                if current_holding > 0:
                    # APPLY FORMULA 4: FIFO cost basis calculation
                    total_cost_basis_usd = 0.0
                    remaining_shares = current_holding
                    
                    # Sort vesting records by date for FIFO (earliest first)
                    sorted_vestings = sorted(vesting_records, key=lambda x: x.vesting_date)
                    
                    for vesting_record in sorted_vestings:
                        if remaining_shares <= 0:
                            break
                        
                        # Allocate shares from this vesting to remaining holding
                        shares_to_use = min(remaining_shares, vesting_record.quantity)
                        cost_contribution = shares_to_use * vesting_record.fmv_usd
                        total_cost_basis_usd += cost_contribution
                        remaining_shares -= shares_to_use
                    
                    # APPLY FORMULA 5: Calculate weighted average cost basis per share
                    avg_cost_basis_per_share = total_cost_basis_usd / current_holding if current_holding > 0 else 0.0
                    
                    # Find the latest vesting record for additional metadata
                    latest_vesting = max(vesting_records, key=lambda x: x.vesting_date)
                    
                    # Create equity holding with accurate cost basis from RSU data
                    holding = EquityHolding(
                        holding_date=as_of_date,
                        quantity=current_holding,
                        cost_basis_usd_per_share=avg_cost_basis_per_share,
                        market_value_usd_per_share=year_end_stock_price,
                        cost_basis_usd_total=total_cost_basis_usd,
                        market_value_usd_total=year_end_stock_price * current_holding,
                        cost_basis_inr_total=total_cost_basis_usd * year_end_exchange_rate,
                        market_value_inr_total=(year_end_stock_price * current_holding) * year_end_exchange_rate,
                        exchange_rate=year_end_exchange_rate,
                        holding_type="Vested",
                        grant_date=None,  # Not available in RSU records
                        grant_number=grant_number,
                        vest_date=latest_vesting.vesting_date,
                        calendar_year=calendar_year
                    )
                    
                    equity_holdings.append(holding)
                    
                    logger.debug(f"RSU holding: {current_holding:.2f} shares of {grant_number}, "
                               f"cost basis ${avg_cost_basis_per_share:.2f}/share, "
                               f"market value ₹{holding.market_value_inr_total:,.2f}")
                
            except Exception as e:
                logger.error(f"Error processing RSU grant {grant_number}: {e}")
                continue
        
        logger.info(f"Processed {len(equity_holdings)} RSU equity holdings with accurate cost basis")
        return equity_holdings
    
    def calculate_year_balances(
        self,
        rsu_records: List[RSUVestingRecord],
        gl_records: List[GLStatementRecord],
        calendar_year: str
    ) -> Dict[str, Dict]:
        """Calculate opening, closing, and peak balances for the year."""
        
        # =================================================================================
        # FOREIGN ASSETS (FA) YEAR BALANCE CALCULATION FORMULAS
        # =================================================================================
        #
        # Foreign Assets reporting requires three key balance types:
        # 1. Opening Balance: Value from when foreign assets were first acquired (earliest vesting)
        # 2. Peak Balance: Highest value during the calendar year
        # 3. Closing Balance: Value at end of calendar year (Dec 31)
        #
        # FORMULA 1: Opening Balance Calculation
        # Purpose: Calculate FA value from when foreign assets were first acquired
        # Date: Earliest vesting date for shares held during the calendar year
        # Formula: Opening_Balance_INR = Holdings_Initial × Stock_Price_Initial × Exchange_Rate_Initial
        # Example: 5 shares × $480 × ₹82.50 = ₹198,000
        # Note: Uses actual holdings from initial vesting (more accurate than Jan 1st)
        #
        # FORMULA 2: Closing Balance Calculation
        # Purpose: Calculate FA value at end of calendar year
        # Date: December 31 of the calendar year
        # Formula: Closing_Balance_INR = Holdings_Dec31 × Stock_Price_Dec31 × Exchange_Rate_Dec31
        # Example: 3 shares × $520 × ₹83.50 = ₹130,260
        # Note: Uses remaining holdings after all sales during the year
        #
        # FORMULA 3: Peak Balance Calculation
        # Purpose: Find the highest value during the calendar year
        # Method: Calculate monthly balances and find maximum
        # Dates: Last day of each month (Jan 31, Feb 28/29, ..., Dec 31)
        # Formula: Monthly_Balance_INR = Holdings_Month_End × Stock_Price_Month_End × Exchange_Rate_Month_End
        # Peak_Balance = max(Monthly_Balance_INR) for all months
        # Example: Peak in July = 4 shares × $580 × ₹84.20 = ₹195,344
        # Note: Peak considers both quantity changes (sales) and price fluctuations
        #
        # FORMULA 4: Holdings Adjustment for Date
        # Purpose: Calculate accurate share quantity as of specific date
        # Method: Apply FIFO logic for sales up to the calculation date
        # Formula: Holdings_Date = Total_Vested_Before_Date - Total_Sold_Before_Date
        # Example: 5 vested by June - 2 sold by September = 3 shares in October
        # Note: Sales are applied chronologically to maintain accuracy
        #
        # FORMULA 5: Date-Specific Market Value
        # Purpose: Calculate market value using closest available rates
        # Priority: Exact date → Previous day → Fallback window (±15 days)
        # Formula: Market_Value = Current_Holdings × Best_Available_Stock_Price × Best_Available_Exchange_Rate
        # Fallback: Use most recent available data within reasonable window
        # Note: Critical for accurate peak detection across volatile periods
        #
        # FORMULA 6: Balance Continuity Verification
        # Purpose: Ensure consistency between calendar years
        # Rule: Closing_Balance_Year_N should approximately equal Opening_Balance_Year_N+1
        # Tolerance: Small differences acceptable due to exchange rate timing differences
        # Formula: |Closing_CY2023 - Opening_CY2024| ÷ Opening_CY2024 < Threshold
        # Example: ₹130,260 (close) vs ₹130,800 (open) = 0.4% difference (acceptable)
        # Note: Opening balance uses earliest vesting date, not Jan 1st
        # =================================================================================
        
        year = int(calendar_year)
        
        # APPLY FORMULA 1 & 2: Define key dates for opening and closing
        # Opening date is the earliest vesting date for shares held during the year
        # This provides more accurate FA reporting than using arbitrary Jan 1st
        opening_date = self.get_earliest_vesting_date_for_year(rsu_records, gl_records, calendar_year)
        closing_date = Date(year, 12, 31)
        
        # APPLY FORMULA 3: Generate monthly dates for peak balance calculation
        monthly_dates = []
        for month in range(1, 13):
            if month == 12:
                monthly_dates.append(Date(year, 12, 31))
            else:
                # Last day of each month for accurate peak detection
                next_month = Date(year, month + 1, 1)
                last_day = next_month - timedelta(days=1)
                monthly_dates.append(last_day)
        
        balance_calculations = {}
        
        logger.info(f"Calculating balances for {calendar_year} at {len(monthly_dates)} dates")
        
        # Calculate balances for each critical date (opening + monthly for peak detection)
        for calc_date in [opening_date] + monthly_dates:
            date_str = calc_date.strftime("%Y-%m-%d")
            
            try:
                # APPLY FORMULA 4: Calculate holdings as of this specific date
                holdings = self.process_rsu_equity_holdings(rsu_records, gl_records, calc_date)
                
                # APPLY FORMULA 5: Calculate total values using date-specific rates
                total_value_usd = sum(h.market_value_usd_total for h in holdings)
                vested_value_inr = sum(h.market_value_inr_total for h in holdings if h.holding_type == "Vested")
                
                # Get date-specific rates with fallback logic (Formula 5)
                exchange_rate = self.get_date_specific_exchange_rate(calc_date)
                stock_price = self.get_date_specific_stock_price(calc_date)
                
                # Store comprehensive balance data for analysis and reporting
                
                balance_calculations[date_str] = {
                    'date': calc_date,
                    'vested_value_inr': vested_value_inr,
                    'total_value_usd': total_value_usd,
                    'exchange_rate': exchange_rate,
                    'stock_price': stock_price,
                    'holdings_count': len(holdings)
                }
                
                logger.debug(f"Balance on {date_str}: ₹{vested_value_inr:,.2f}")
                
            except Exception as e:
                logger.warning(f"Could not calculate balance for {date_str}: {e}")
                balance_calculations[date_str] = {
                    'date': calc_date,
                    'vested_value_inr': 0.0,
                    'total_value_usd': 0.0,
                    'exchange_rate': 0.0,
                    'stock_price': 0.0,
                    'holdings_count': 0
                }
        
        return balance_calculations
    
    def get_earliest_vesting_date_for_year(
        self,
        rsu_records: List[RSUVestingRecord],
        gl_records: List[GLStatementRecord],
        calendar_year: str
    ) -> Date:
        """Get the earliest vesting date for shares that would be held during the calendar year.
        
        This is important for FA reporting as the initial value should be calculated from when
        the foreign assets were first acquired (vested), not from January 1st of the tax year.
        
        Args:
            rsu_records: List of RSU vesting records
            gl_records: List of G&L sale records  
            calendar_year: Calendar year to calculate for
            
        Returns:
            Earliest vesting date for shares held during the calendar year
        """
        year = int(calendar_year)
        year_start = Date(year, 1, 1)
        year_end = Date(year, 12, 31)
        
        # Find all vesting records for shares that would be held during the calendar year
        # This includes shares vested before the year that weren't fully sold before the year
        relevant_vest_dates = []
        
        for vest in rsu_records:
            # Check if any shares from this vest would still be held during the calendar year
            vest_key = f"{vest.grant_number}_{vest.vesting_date}"
            
            # Calculate how many shares from this vest were sold before the calendar year
            shares_sold_before_year = sum(
                record.quantity for record in gl_records
                if (record.grant_number == vest.grant_number and 
                    record.date_acquired == vest.vesting_date and
                    record.date_sold and record.date_sold < year_start)
            )
            
            # If some shares from this vest remain, include the vesting date
            remaining_shares = vest.quantity - shares_sold_before_year
            if remaining_shares > 0:
                relevant_vest_dates.append(vest.vesting_date)
        
        if not relevant_vest_dates:
            logger.warning(f"No relevant vesting dates found for {calendar_year}, using Jan 1st")
            return year_start
        
        earliest_vest_date = min(relevant_vest_dates)
        logger.info(f"Earliest vesting date for {calendar_year} holdings: {earliest_vest_date}")
        
        return earliest_vest_date
    
    def calculate_share_statistics(
        self,
        rsu_records: List[RSUVestingRecord],
        gl_records: List[GLStatementRecord],
        calendar_year: str
    ) -> Dict[str, float]:
        """Calculate comprehensive share statistics for the calendar year."""
        
        year = int(calendar_year)
        
        # Calculate total shares vested ever (before and during CL year)
        total_vested_ever = sum(r.quantity for r in rsu_records)
        
        # Calculate total shares sold ever
        total_sold_ever = sum(r.quantity for r in gl_records if r.quantity)
        
        # Calculate shares sold during CL year
        cl_start = Date(year, 1, 1)
        cl_end = Date(year, 12, 31)
        total_sold_in_cl = sum(
            r.quantity for r in gl_records 
            if r.quantity and cl_start <= r.date_sold <= cl_end
        )
        
        # Calculate shares vested before CL year
        vested_before_cl = sum(
            r.quantity for r in rsu_records 
            if r.vesting_date < cl_start
        )
        
        # Calculate shares sold before CL year
        sold_before_cl = sum(
            r.quantity for r in gl_records 
            if r.quantity and r.date_sold < cl_start
        )
        
        # Opening balance shares = vested before CL - sold before CL
        opening_shares = max(0.0, vested_before_cl - sold_before_cl)
        
        # Current holdings = total vested ever - total sold ever
        current_holdings = max(0.0, total_vested_ever - total_sold_ever)
        
        logger.info(f"Share Statistics for {calendar_year}:")
        logger.info(f"  Total vested ever: {total_vested_ever:.2f}")
        logger.info(f"  Total sold ever: {total_sold_ever:.2f}")
        logger.info(f"  Sold in CL{calendar_year}: {total_sold_in_cl:.2f}")
        logger.info(f"  Vested before CL: {vested_before_cl:.2f}")
        logger.info(f"  Sold before CL: {sold_before_cl:.2f}")
        logger.info(f"  Opening shares: {opening_shares:.2f}")
        logger.info(f"  Current holdings: {current_holdings:.2f}")
        
        return {
            'total_vested_ever': total_vested_ever,
            'total_sold_ever': total_sold_ever,
            'total_sold_in_cl': total_sold_in_cl,
            'opening_shares': opening_shares,
            'current_holdings': current_holdings,
            'vested_before_cl': vested_before_cl,
            'sold_before_cl': sold_before_cl
        }

    def calculate_vest_wise_details(
        self,
        rsu_records: List[RSUVestingRecord],
        gl_records: List[GLStatementRecord],
        calendar_year: str
    ) -> List[VestWiseDetails]:
        """Calculate detailed vest-wise information for FA compliance reporting."""
        
        logger.info(f"Calculating vest-wise details for CL{calendar_year}")
        
        # Get calendar year dates
        try:
            year_int = int(calendar_year)
            year_start, year_end = get_calendar_year_dates(year_int)
            logger.debug(f"Calendar year dates: {year_start} to {year_end}")
        except Exception as e:
            logger.error(f"Error getting calendar year dates for {calendar_year}: {e}")
            raise
        
        # Group sold shares by grant and acquisition date for current year sales
        sold_shares_by_vest_current_year = {}
        # Group total sold shares by grant and acquisition date (all years)
        total_sold_shares_by_vest = {}
        
        try:
            for record in gl_records:
                logger.debug(f"Processing GL record: grant={record.grant_number}, date_sold={record.date_sold}, acq_date={record.date_acquired}")
                vest_key = f"{record.grant_number}_{record.date_acquired}"
                
                # Track total sales across all years
                total_sold_shares_by_vest[vest_key] = total_sold_shares_by_vest.get(vest_key, 0.0) + record.quantity
                
                # Track current year sales separately
                if record.date_sold and year_start <= record.date_sold <= year_end:
                    sold_shares_by_vest_current_year[vest_key] = sold_shares_by_vest_current_year.get(vest_key, 0.0) + record.quantity
        except Exception as e:
            logger.error(f"Error processing GL records: {e}")
            raise
        
        # Filter vests to only include those relevant to the current calendar year:
        # 1. Vests that still have shares remaining at the END of current calendar year, OR
        # 2. Vests that had sales activity during the current calendar year
        try:
            relevant_vests = []
            for vest in rsu_records:
                if vest.vesting_date <= year_end:
                    vest_key = f"{vest.grant_number}_{vest.vesting_date}"
                    
                    # Calculate sales that occurred BEFORE or DURING the current calendar year
                    sales_through_current_year = 0.0
                    for record in gl_records:
                        if (record.date_sold and record.date_sold <= year_end and 
                            record.grant_number == vest.grant_number and 
                            record.date_acquired == vest.vesting_date):
                            sales_through_current_year += record.quantity
                    
                    current_year_sales = sold_shares_by_vest_current_year.get(vest_key, 0.0)
                    shares_remaining_at_year_end = vest.quantity - sales_through_current_year
                    
                    # Include if either:
                    # 1. Has shares remaining at end of current year, OR
                    # 2. Had sales activity in current year (even if now fully sold)
                    if shares_remaining_at_year_end > 0 or current_year_sales > 0:
                        relevant_vests.append(vest)
                        logger.debug(f"Including vest {vest.grant_number} ({vest.vesting_date}): remaining at year-end={shares_remaining_at_year_end:.2f}, CY sales={current_year_sales:.2f}")
                    else:
                        logger.debug(f"Excluding vest {vest.grant_number} ({vest.vesting_date}): fully sold by end of current year")
            
            logger.debug(f"Found {len(relevant_vests)} relevant vests for {calendar_year} (filtered from {len([v for v in rsu_records if v.vesting_date <= year_end])} total)")
        except Exception as e:
            logger.error(f"Error filtering vesting records: {e}")
            raise
        
        vest_details = []
        
        try:
            for i, vest in enumerate(relevant_vests):
                logger.debug(f"Processing vest {i+1}/{len(relevant_vests)}: {vest.grant_number} on {vest.vesting_date}")
                vest_key = f"{vest.grant_number}_{vest.vesting_date}"
                shares_sold_from_vest_current_year = sold_shares_by_vest_current_year.get(vest_key, 0.0)
                
                # Calculate shares sold through the end of current calendar year (not all years)
                shares_sold_through_current_year = 0.0
                for record in gl_records:
                    if (record.date_sold and record.date_sold <= year_end and 
                        record.grant_number == vest.grant_number and 
                        record.date_acquired == vest.vesting_date):
                        shares_sold_through_current_year += record.quantity
                
                remaining_shares = max(0.0, vest.quantity - shares_sold_through_current_year)
                
                # Calculate initial value at vesting
                initial_value_usd = vest.quantity * vest.fmv_usd
                initial_value_inr = initial_value_usd * vest.forex_rate  # Calculate correctly instead of using potentially incorrect PDF value
                
                # Calculate peak value during the calendar year
                peak_value_inr = 0.0
                peak_date = None
                peak_stock_price = 0.0
                peak_exchange_rate = 0.0
                
                # Get year-end date for calculations
                year_end_date = Date(int(calendar_year), 12, 31)
                
                # Calculate monthly values to find peak (only from vesting date onwards)
                vest_month = vest.vesting_date.month
                start_month = vest_month if vest.vesting_date.year == int(calendar_year) else 1
                
                for month in range(start_month, 13):
                    year_int = int(calendar_year)
                    if month == 12:
                        calc_date = Date(year_int, 12, 31)  # Use Dec 31 for year-end
                    else:
                        # Use last day of month
                        if month < 12:
                            next_month_num = month + 1
                            next_year = year_int
                        else:
                            next_month_num = 1
                            next_year = year_int + 1
                        
                        next_month = Date(next_year, next_month_num, 1)
                        calc_date = next_month - timedelta(days=1)
                    
                    # Only calculate value if this date is after vesting
                    if calc_date >= vest.vesting_date:
                        stock_price = self.get_date_specific_stock_price(calc_date)
                        exchange_rate = self.get_date_specific_exchange_rate(calc_date)
                        
                        # Calculate shares remaining at this date (considering sales)
                        shares_at_date = vest.quantity
                        if shares_sold_from_vest_current_year > 0:
                            # For simplicity, assume sales happened at end of year
                            # (more complex logic could track exact sale dates)
                            shares_at_date = vest.quantity if calc_date < year_end_date else remaining_shares
                        
                        month_value_inr = shares_at_date * stock_price * exchange_rate
                        
                        if month_value_inr > peak_value_inr:
                            peak_value_inr = month_value_inr
                            peak_date = calc_date
                            peak_stock_price = stock_price
                            peak_exchange_rate = exchange_rate
                
                # Calculate closing values
                closing_stock_price = self.get_date_specific_stock_price(year_end_date)
                closing_exchange_rate = self.get_date_specific_exchange_rate(year_end_date)
                closing_value_inr = remaining_shares * closing_stock_price * closing_exchange_rate
                
                # Calculate gross proceeds from sales
                gross_proceeds_inr = 0.0
                if shares_sold_from_vest_current_year > 0:
                    # Find sales from this specific vest
                    for record in gl_records:
                        if (record.date_sold and year_start <= record.date_sold <= year_end and
                            record.grant_number == vest.grant_number and 
                            record.date_acquired == vest.vesting_date):
                            # Use the proceeds from G&L statement (in USD, convert to INR)
                            sale_exchange_rate = self.get_date_specific_exchange_rate(record.date_sold)
                            gross_proceeds_inr += record.quantity * record.proceeds_per_share * sale_exchange_rate
                
                vest_detail = VestWiseDetails(
                    vest_date=vest.vesting_date,
                    grant_number=vest.grant_number,
                    initial_shares=vest.quantity,
                    initial_value_usd=initial_value_usd,
                    initial_value_inr=initial_value_inr,
                    initial_stock_price=vest.fmv_usd,
                    initial_exchange_rate=vest.forex_rate,
                    peak_value_inr=peak_value_inr,
                    peak_date=peak_date,
                    peak_stock_price=peak_stock_price,
                    peak_exchange_rate=peak_exchange_rate,
                    closing_shares=remaining_shares,
                    closing_value_inr=closing_value_inr,
                    closing_stock_price=closing_stock_price,
                    closing_exchange_rate=closing_exchange_rate,
                    gross_income_received=0.0,  # Assuming no dividends for Adobe stock
                    shares_sold=shares_sold_from_vest_current_year,
                    gross_proceeds_inr=gross_proceeds_inr,
                    fully_sold=(remaining_shares == 0.0)
                )
                
                vest_details.append(vest_detail)
        except Exception as e:
            logger.error(f"Error in vest processing loop: {e}")
            raise
        
        # Sort by vest date for consistent reporting
        vest_details.sort(key=lambda x: x.vest_date)
        
        logger.info(f"Calculated vest-wise details for {len(vest_details)} vesting events")
        return vest_details
    
    def calculate_fa_summary(
        self, 
        calendar_year: str,
        equity_holdings: List[EquityHolding],
        rsu_records: List[RSUVestingRecord] = None,
        gl_records: List[GLStatementRecord] = None
    ) -> FADeclarationSummary:
        """Calculate FA declaration summary with opening, closing, and peak balances."""
        
        # Filter holdings for this calendar year
        year_holdings = [h for h in equity_holdings if h.calendar_year == calendar_year]
        
        summary = FADeclarationSummary(
            declaration_date=Date.today(),
            calendar_year=calendar_year
        )
        
        # Calculate comprehensive share statistics and balance analysis if data is available
        if rsu_records and gl_records:
            logger.info(f"Calculating comprehensive balance analysis for {calendar_year}")
            
            # Calculate detailed share statistics
            share_stats = self.calculate_share_statistics(rsu_records, gl_records, calendar_year)
            
            # Populate share statistics in summary
            summary.total_vested_shares = share_stats['current_holdings']  # Currently held
            summary.total_vested_ever = share_stats['total_vested_ever']
            summary.total_sold_in_cl = share_stats['total_sold_in_cl']
            summary.total_sold_ever = share_stats['total_sold_ever']
            
            # Calculate balance timelines
            balance_calculations = self.calculate_year_balances(rsu_records, gl_records, calendar_year)
            
            # Extract opening balance (Jan 1)
            opening_key = f"{calendar_year}-01-01"
            if opening_key in balance_calculations:
                opening_data = balance_calculations[opening_key]
                summary.opening_balance_inr = opening_data['vested_value_inr']
                summary.opening_exchange_rate = opening_data['exchange_rate']
                summary.opening_stock_price = opening_data['stock_price']
                # Calculate shares from USD value and stock price
                if opening_data['stock_price'] > 0:
                    summary.opening_shares = opening_data['total_value_usd'] / opening_data['stock_price']
            
            # Extract closing balance (Dec 31)
            closing_key = f"{calendar_year}-12-31"
            if closing_key in balance_calculations:
                closing_data = balance_calculations[closing_key]
                summary.closing_balance_inr = closing_data['vested_value_inr']
                summary.year_end_exchange_rate = closing_data['exchange_rate']
                summary.year_end_stock_price = closing_data['stock_price']
                # Calculate shares from USD value and stock price
                if closing_data['stock_price'] > 0:
                    summary.closing_shares = closing_data['total_value_usd'] / closing_data['stock_price']
            
            # Find peak balance
            peak_value = 0.0
            peak_date = None
            peak_rate = 0.0
            peak_stock_price = 0.0
            peak_shares = 0.0
            
            for date_str, balance_data in balance_calculations.items():
                vested_value = balance_data['vested_value_inr']
                if vested_value > peak_value:
                    peak_value = vested_value
                    peak_date = balance_data['date']
                    peak_rate = balance_data['exchange_rate']
                    peak_stock_price = balance_data['stock_price']
                    # Calculate peak shares from USD value and stock price
                    if balance_data['stock_price'] > 0:
                        peak_shares = balance_data['total_value_usd'] / balance_data['stock_price']
            
            summary.peak_balance_inr = peak_value
            summary.peak_balance_date = peak_date
            summary.peak_exchange_rate = peak_rate
            summary.peak_stock_price = peak_stock_price
            summary.peak_shares = peak_shares
            
            # Calculate vest-wise details for compliance reporting
            summary.vest_wise_details = self.calculate_vest_wise_details(rsu_records, gl_records, calendar_year)
            
            logger.info(f"Balance Analysis Complete:")
            logger.info(f"  Opening (Jan 1): ₹{summary.opening_balance_inr:,.2f} ({share_stats['opening_shares']:.2f} shares)")
            logger.info(f"  Peak: ₹{summary.peak_balance_inr:,.2f} on {peak_date}")
            logger.info(f"  Closing (Dec 31): ₹{summary.closing_balance_inr:,.2f} ({share_stats['current_holdings']:.2f} shares)")
        
        # Aggregate vested holdings value (from year-end holdings)
        for holding in year_holdings:
            if holding.holding_type == "Vested":
                # Don't override total_vested_shares - already calculated correctly above
                summary.vested_holdings_usd += holding.market_value_usd_total
                summary.vested_holdings_inr += holding.market_value_inr_total
            
            # Update year-end exchange rate if not already set
            if holding.exchange_rate > 0 and summary.year_end_exchange_rate == 0.0:
                summary.year_end_exchange_rate = holding.exchange_rate
        
        # Set closing balance from year-end holdings if not calculated from balance analysis
        if summary.closing_balance_inr == 0.0:
            summary.closing_balance_inr = summary.vested_holdings_inr
        
        logger.info(f"FA Summary for {calendar_year}: "
                   f"₹{summary.vested_holdings_inr:,.2f} vested year-end, "
                   f"₹{summary.peak_balance_inr:,.2f} peak, "
                   f"Declaration required: {summary.declaration_required}")
        
        return summary
