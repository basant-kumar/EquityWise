"""Foreign Assets Service - Main integration service for FA calculations."""

from datetime import date as Date
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from loguru import logger
from rich.progress import Progress, TaskID
from rich.console import Console
from pydantic import BaseModel

from .fa_calculator import FACalculator, EquityHolding, FADeclarationSummary, FACalculationResults
from ..data.loaders import (
    BenefitHistoryLoader, SBIRatesLoader, AdobeStockDataLoader, DataValidator,
    RSULoader, GLStatementLoader
)
from ..data.models import (
    BenefitHistoryRecord, SBIRateRecord, AdobeStockRecord,
    RSUVestingRecord, GLStatementRecord, ForeignCompanyRecord,
    EmployerCompanyRecord, ForeignDepositoryAccountRecord,
    create_default_company_records
)
from ..config.settings import Settings

 
class FAService:
    """Main Foreign Assets calculation service."""
    
    def __init__(self, settings: Settings):
        """Initialize FA service."""
        self.settings = settings
        self.console = Console()
        
        # Load company and depository account information
        self.employer_company, self.foreign_company, self.depository_account = create_default_company_records()
    
    def get_company_details(self) -> Tuple[EmployerCompanyRecord, ForeignCompanyRecord, ForeignDepositoryAccountRecord]:
        """Get company and depository account details for FA reporting."""
        return self.employer_company, self.foreign_company, self.depository_account
        
    def load_required_data(self) -> Tuple[
        List[RSUVestingRecord],
        List[GLStatementRecord], 
        List[SBIRateRecord], 
        List[AdobeStockRecord]
    ]:
        """Load required data sources for FA calculations using RSU and G&L data."""
        
        logger.info("Loading Foreign Assets calculation data from required sources")
        
        with Progress() as progress:
            # Create progress tasks
            task1 = progress.add_task("Loading RSU Vesting Data...", total=1)
            task2 = progress.add_task("Loading G&L Statements...", total=1)
            task3 = progress.add_task("Loading SBI Rates...", total=1) 
            task4 = progress.add_task("Loading Stock Data...", total=1)
            
            # Load RSU vesting data from ALL RSU PDFs for comprehensive history
            all_rsu_records = []
            
            # Load from all configured RSU PDF paths
            for rsu_path in self.settings.rsu_pdf_paths:
                if rsu_path.exists():
                    try:
                        rsu_loader = RSULoader(rsu_path)
                        rsu_file_records = rsu_loader.get_validated_records(str(rsu_path))
                        all_rsu_records.extend(rsu_file_records)
                        logger.info(f"Loaded {len(rsu_file_records)} RSU vesting records from {rsu_path.name}")
                    except Exception as e:
                        logger.error(f"Failed to load RSU data from {rsu_path}: {e}")
                else:
                    logger.warning(f"RSU PDF not found: {rsu_path}")
            
            rsu_records = all_rsu_records
            progress.update(task1, advance=1)
            logger.info(f"Total RSU vesting records loaded from {len(self.settings.rsu_pdf_paths)} PDFs: {len(rsu_records)}")
            
            # Load G&L Statements
            gl_records = []
            for gl_path in self.settings.gl_statements_paths:
                if gl_path.exists():
                    gl_loader = GLStatementLoader(gl_path)
                    gl_file_records = gl_loader.get_validated_records()
                    gl_records.extend(gl_file_records)
                    logger.info(f"Loaded {len(gl_file_records)} records from {gl_path.name}")
            progress.update(task2, advance=1)
            logger.info(f"Total G&L records: {len(gl_records)}")
            
            # Load SBI Rates
            sbi_loader = SBIRatesLoader(self.settings.sbi_ttbr_rates_path)
            sbi_records = sbi_loader.get_validated_records()
            progress.update(task3, advance=1)
            logger.info(f"Loaded {len(sbi_records)} SBI exchange rate records")
            
            # Load Stock Data
            stock_loader = AdobeStockDataLoader(self.settings.adobe_stock_data_path)
            stock_records = stock_loader.get_validated_records()
            progress.update(task4, advance=1)
            logger.info(f"Loaded {len(stock_records)} Adobe stock price records")
        
        return rsu_records, gl_records, sbi_records, stock_records
    
    def calculate_fa_for_year(
        self, 
        calendar_year: Optional[str] = None,
        as_of_date: Optional[Date] = None,
        detailed: bool = False
    ) -> FACalculationResults:
        """
        Calculate Foreign Assets for specified calendar year.
        
        Args:
            calendar_year: Calendar year to calculate (e.g., '2024'). If None, uses current year.
            as_of_date: Date to calculate holdings as of. If None, uses December 31 of target year.
            detailed: Whether to include detailed holding lists.
            
        Returns:
            Complete FA calculation results.
        """
        
        # =================================================================================
        # FOREIGN ASSETS (FA) SERVICE CALCULATION ORCHESTRATION
        # =================================================================================
        #
        # FA compliance requires tracking three key balances for each calendar year:
        # 1. Opening Balance (Initial Vesting): Value from when assets were first acquired
        # 2. Peak Balance: Highest value during the calendar year  
        # 3. Closing Balance (Dec 31): Value at end of calendar year
        #
        # CALCULATION WORKFLOW:
        #
        # STEP 1: Date and Year Determination
        # Purpose: Establish calculation boundaries
        # Default: Calendar year = current year, as_of_date = Dec 31
        # Note: Calendar year runs Jan 1 to Dec 31 (different from financial year)
        #
        # STEP 2: Data Loading and Validation
        # Purpose: Load all required data sources
        # Sources: RSU PDFs, G&L statements, SBI rates, Adobe stock prices
        # Validation: Ensure data completeness for the target year
        #
        # STEP 3: Equity Holdings Processing
        # Purpose: Calculate current holdings and cost basis using FIFO
        # Method: Use RSU PDF data for accurate vesting costs
        # Formula: Current_Holdings = Total_Vested_Before_Date - Total_Sold_Before_Date
        # Cost_Basis: FIFO allocation from earliest vestings
        #
        # STEP 4: Balance Analysis
        # Purpose: Calculate opening, peak, and closing balances
        # Method: Monthly calculations to identify peak value
        # Opening_Balance = Holdings_Initial × Stock_Price_Initial × Exchange_Rate_Initial
        # Peak_Balance = max(Monthly_Balance) for all months in year
        # Closing_Balance = Holdings_Dec31 × Stock_Price_Dec31 × Exchange_Rate_Dec31
        #
        # STEP 5: Declaration Requirement Assessment
        # Purpose: Determine if FA declaration is required
        # Threshold: ₹20 lakhs for any balance during the year
        # Rule: Declaration required if Opening OR Peak OR Closing > ₹20,00,000
        #
        # STEP 6: Results Compilation
        # Purpose: Package all calculations for reporting
        # Includes: Balance summary, holdings details, vest-wise breakdown
        # Output: Structured results for tax compliance and analysis
        # =================================================================================
        
        # STEP 1: Determine target year and calculation date
        if not calendar_year:
            calendar_year = str(Date.today().year)
        
        if not as_of_date:
            try:
                year = int(calendar_year)
                as_of_date = Date(year, 12, 31)  # Default to year-end for FA calculations
            except ValueError:
                logger.error(f"Invalid calendar year: {calendar_year}")
                as_of_date = Date.today()
        
        logger.info(f"Starting FA calculations for calendar year {calendar_year} as of {as_of_date}")
        
        # STEP 2: Load all required data sources
        rsu_records, gl_records, sbi_records, stock_records = self.load_required_data()
        
        # STEP 3: Initialize calculator with rate and price data
        calculator = FACalculator(sbi_records, stock_records)
        
        # STEP 4: Process equity holdings using RSU data for accurate cost basis
        self.console.print("🔄 Processing equity holdings with RSU data...")
        
        equity_holdings = calculator.process_rsu_equity_holdings(rsu_records, gl_records, as_of_date)
        
        logger.info(f"Processed {len(equity_holdings)} equity holdings")
        
        # STEP 5: Calculate comprehensive FA summary with balance analysis
        fa_summary = calculator.calculate_fa_summary(calendar_year, equity_holdings, rsu_records, gl_records)
        
        # Create results
        results = FACalculationResults(
            calculation_date=Date.today(),
            calendar_year=calendar_year,
            benefit_history_records=len(rsu_records),  # Now using RSU records count
            stock_price_records=len(stock_records),
            sbi_rate_records=len(sbi_records),
            equity_holdings=equity_holdings if detailed else [],
            year_summaries={calendar_year: fa_summary},
            total_years_analyzed=1,
            years_requiring_declaration=[calendar_year] if fa_summary.declaration_required else []
        )
        
        # Log summary
        logger.info(f"FA Calculation Summary for {calendar_year}:")
        logger.info(f"  Vested Holdings: ₹{fa_summary.vested_holdings_inr:,.2f}")
        logger.info(f"  Current Holdings: {fa_summary.total_vested_shares:.0f} shares")
        logger.info(f"  Total Vested Ever: {fa_summary.total_vested_ever:.0f} shares")
        logger.info(f"  Total Sold Ever: {fa_summary.total_sold_ever:.0f} shares")
        logger.info(f"  Declaration Required: {fa_summary.declaration_required}")
        
        return results
    
    def calculate_fa_multi_year(self, detailed: bool = False) -> FACalculationResults:
        """Calculate Foreign Assets for all available years with automatic year detection."""
        
        logger.info("Starting multi-year FA calculations for all available data")
        
        # Determine available years from vesting data
        rsu_records, gl_records, sbi_records, stock_records = self.load_required_data()
        
        # Get date range from vesting events
        all_vesting_dates = [record.vesting_date for record in rsu_records]
        all_sale_dates = [record.date_sold for record in gl_records if record.date_sold]
        
        if not (all_vesting_dates or all_sale_dates):
            logger.warning("No vesting or sale data found")
            return FACalculationResults(
                calculation_date=Date.today(),
                calendar_year="N/A",
                year_summaries={},
                equity_holdings=[],
                benefit_history_records=0,
                sbi_rate_records=len(sbi_records),
                stock_price_records=len(stock_records)
            )
        
        # Determine year range from available data
        min_year = 9999
        max_year = 0
        
        for date in all_vesting_dates + all_sale_dates:
            if date:
                min_year = min(min_year, date.year)
                max_year = max(max_year, date.year)
        
        # Add surrounding years for complete analysis
        start_year = max(min_year - 1, 2022)  # Don't go too far back
        end_year = min(max_year + 1, 2025)    # Don't go too far forward
        
        logger.info(f"Analyzing years {start_year} to {end_year}")
        
        # Calculate for each year
        year_summaries = {}
        all_holdings = []
        
        for year in range(start_year, end_year + 1):
            year_str = str(year)
            
            try:
                self.console.print(f"🔄 Processing CL{year}...")
                
                # Calculate FA for this year
                single_year_results = self.calculate_fa_for_year(year_str, detailed=False)
                
                if single_year_results.year_summaries:
                    year_summary = list(single_year_results.year_summaries.values())[0]
                    year_summaries[year_str] = year_summary
                    
                    if detailed:
                        all_holdings.extend(single_year_results.equity_holdings)
                    
                    logger.info(f"CL{year}: Opening ₹{year_summary.opening_balance_inr:,.0f}, "
                              f"Peak ₹{year_summary.peak_balance_inr:,.0f}, "
                              f"Closing ₹{year_summary.closing_balance_inr:,.0f}")
                
            except Exception as e:
                logger.warning(f"Could not calculate FA for {year}: {e}")
                continue
        
        # Create comprehensive results
        results = FACalculationResults(
            calculation_date=Date.today(),
            calendar_year=f"{start_year}-{end_year}",
            year_summaries=year_summaries,
            equity_holdings=all_holdings if detailed else [],
            benefit_history_records=len(rsu_records),
            sbi_rate_records=len(sbi_records),
            stock_price_records=len(stock_records)
        )
        
        return results
    
    def calculate_multi_year_fa(
        self, 
        start_year: str,
        end_year: str,
        detailed: bool = False
    ) -> FACalculationResults:
        """Calculate FA for multiple years."""
        
        logger.info(f"Starting multi-year FA calculations from {start_year} to {end_year}")
        
        # Load all data once
        benefit_records, sbi_records, stock_records = self.load_required_data()
        
        # Initialize calculator
        calculator = FACalculator(sbi_records, stock_records)
        
        # Calculate for each year
        all_holdings = []
        year_summaries = {}
        years_requiring_declaration = []
        
        try:
            start_yr = int(start_year)
            end_yr = int(end_year)
            
            for year in range(start_yr, end_yr + 1):
                year_str = str(year)
                as_of_date = Date(year, 12, 31)
                
                self.console.print(f"🔄 Processing {year_str}...")
                
                # Process holdings for this year
                equity_holdings = calculator.process_equity_holdings(benefit_records, as_of_date)
                
                # Calculate summary
                fa_summary = calculator.calculate_fa_summary(year_str, equity_holdings)
                year_summaries[year_str] = fa_summary
                
                if fa_summary.declaration_required:
                    years_requiring_declaration.append(year_str)
                
                if detailed:
                    all_holdings.extend(equity_holdings)
                
                logger.info(f"{year_str}: ₹{fa_summary.total_equity_value_inr:,.2f} total equity, "
                           f"Declaration required: {fa_summary.declaration_required}")
        
        except ValueError as e:
            logger.error(f"Invalid year range: {e}")
            return FACalculationResults(
                calculation_date=Date.today(),
                calendar_year=f"{start_year}-{end_year}",
                benefit_history_records=len(benefit_records),
                stock_price_records=len(stock_records),
                sbi_rate_records=len(sbi_records)
            )
        
        # Create results
        results = FACalculationResults(
            calculation_date=Date.today(),
            calendar_year=f"{start_year}-{end_year}",
            benefit_history_records=len(benefit_records),
            stock_price_records=len(stock_records),
            sbi_rate_records=len(sbi_records),
            equity_holdings=all_holdings,
            year_summaries=year_summaries,
            total_years_analyzed=len(year_summaries),
            years_requiring_declaration=years_requiring_declaration
        )
        
        logger.info(f"Multi-year FA calculation complete: {len(year_summaries)} years analyzed, "
                   f"{len(years_requiring_declaration)} years requiring declaration")
        
        return results
    
    def validate_fa_data_quality(self) -> Dict[str, any]:
        """Validate data quality before FA calculations."""
        
        logger.info("Validating data quality for FA calculations")
        
        # Use existing DataValidator, but only check required sources
        validator = DataValidator()
        
        # FA calculations only need BenefitHistory, SBI rates, and stock data
        # G&L statements are not required for FA calculations
        validation_results = {
            'success': True,
            'errors': [],
            'warnings': [],
            'sources_validated': 0,
            'total_records': 0
        }
        
        try:
            # Validate BenefitHistory
            benefit_loader = BenefitHistoryLoader(self.settings.benefit_history_path)
            benefit_records = benefit_loader.get_validated_records()
            validation_results['total_records'] += len(benefit_records)
            validation_results['sources_validated'] += 1
            logger.info(f"✅ BenefitHistory validated: {len(benefit_records)} records")
            
            # Validate SBI rates
            sbi_loader = SBIRatesLoader(self.settings.sbi_ttbr_rates_path)
            sbi_records = sbi_loader.get_validated_records()
            validation_results['total_records'] += len(sbi_records)
            validation_results['sources_validated'] += 1
            logger.info(f"✅ SBI rates validated: {len(sbi_records)} records")
            
            # Validate stock data
            stock_loader = AdobeStockDataLoader(self.settings.adobe_stock_data_path)
            stock_records = stock_loader.get_validated_records()
            validation_results['total_records'] += len(stock_records)
            validation_results['sources_validated'] += 1
            logger.info(f"✅ Stock data validated: {len(stock_records)} records")
            
            self.console.print("✅ All FA data sources validated successfully")
            
        except Exception as e:
            validation_results['success'] = False
            validation_results['errors'].append(f"Data validation failed: {e}")
            logger.error(f"FA data validation error: {e}")
        
        return validation_results
    
    def get_compliance_summary(
        self, 
        results: FACalculationResults
    ) -> Dict[str, any]:
        """Generate compliance summary for FA declaration purposes."""
        
        compliance_summary = {
            'years_analyzed': results.total_years_analyzed,
            'years_requiring_declaration': len(results.years_requiring_declaration),
            'declaration_years': results.years_requiring_declaration,
            'compliance_details': {}
        }
        
        for year, summary in results.year_summaries.items():
            compliance_summary['compliance_details'][year] = {
                'vested_holdings_inr': summary.vested_holdings_inr,
                'declaration_required': summary.declaration_required,
                'exceeds_threshold': summary.exceeds_declaration_threshold,
                'year_end_exchange_rate': summary.year_end_exchange_rate,
                'current_shares': summary.total_vested_shares,
                'total_vested_ever': summary.total_vested_ever,
                'total_sold_ever': summary.total_sold_ever,
                'sold_in_cl': summary.total_sold_in_cl
            }
        
        logger.info(f"Compliance summary: {compliance_summary['years_requiring_declaration']}/{compliance_summary['years_analyzed']} years require FA declaration")
        
        return compliance_summary
    
    def export_fa_declaration(self, results: FACalculationResults, output_path: Path) -> None:
        """Export FA declaration data to file (placeholder for Phase 5)."""
        
        # This will be implemented in Phase 5: Report Generation
        logger.info(f"FA declaration export functionality will be implemented in Phase 5")
        logger.info(f"Results summary: {len(results.year_summaries)} year summaries, "
                   f"{len(results.years_requiring_declaration)} years requiring declaration")
