"""RSU Service - Main integration service for RSU calculations."""

from datetime import date as Date
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

from loguru import logger
from rich.progress import Progress, TaskID
from rich.console import Console
from pydantic import BaseModel

from .rsu_calculator import RSUCalculator, VestingEvent, SaleEvent, RSUCalculationSummary
from ..data.loaders import (
    GLStatementLoader, SBIRatesLoader, AdobeStockDataLoader, RSULoader
)
from ..data.models import (
    GLStatementRecord, SBIRateRecord, AdobeStockRecord, RSUVestingRecord
)
from ..config.settings import Settings


class RSUCalculationResults(BaseModel):
    """Complete RSU calculation results."""
    
    calculation_date: Date
    financial_year: str
    
    # Source Data Summary
    benefit_history_records: int = 0
    gl_statement_records: int = 0
    sbi_rate_records: int = 0
    stock_data_records: int = 0
    
    # Processed Events
    vesting_events: List[VestingEvent] = []
    sale_events: List[SaleEvent] = []
    
    # Financial Year Summaries
    fy_summaries: Dict[str, RSUCalculationSummary] = {}
    
    # Overall Summary
    total_vested_quantity: float = 0.0
    total_sold_quantity: float = 0.0
    total_taxable_gain_inr: float = 0.0
    total_capital_gains_inr: float = 0.0
    net_position_inr: float = 0.0
    
    @property
    def available_financial_years(self) -> List[str]:
        """Get list of financial years with RSU activity."""
        return list(self.fy_summaries.keys())


class RSUService:
    """Main RSU calculation service."""
    
    def __init__(self, settings: Settings):
        """Initialize RSU service."""
        self.settings = settings
        self.console = Console()
        
    def load_all_data(self) -> Tuple[
        List[RSUVestingRecord], 
        List[GLStatementRecord], 
        List[SBIRateRecord], 
        List[AdobeStockRecord]
    ]:
        """Load all required data sources."""
        
        logger.info("Loading RSU calculation data from all sources")
        
        with Progress() as progress:
            # Create progress tasks
            task1 = progress.add_task("Loading RSU Vesting Data...", total=1)
            task2 = progress.add_task("Loading G&L Statements...", total=1) 
            task3 = progress.add_task("Loading SBI Rates...", total=1)
            task4 = progress.add_task("Loading Stock Data...", total=1)
            
            # Load RSU vesting data using AUTO-DISCOVERY from RSU documents directory
            all_rsu_records = []
            
            # Use auto-discovery to find all RSU PDF files in the directory
            rsu_files = self.settings.get_rsu_files(use_auto_discovery=True)
            logger.info(f"Auto-discovered {len(rsu_files)} RSU PDF files for processing")
            
            for rsu_path in rsu_files:
                try:
                    rsu_loader = RSULoader(rsu_path)
                    rsu_file_records = rsu_loader.get_validated_records(str(rsu_path))
                    all_rsu_records.extend(rsu_file_records)
                    logger.info(f"✅ Loaded {len(rsu_file_records)} RSU vesting records from {rsu_path.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load RSU data from {rsu_path}: {e}")
            
            rsu_records = all_rsu_records
            progress.update(task1, advance=1)
            logger.info(f"📊 Total RSU vesting records loaded from {len(rsu_files)} PDF files: {len(rsu_records)}")
            
            # Load G&L Statements using AUTO-DISCOVERY from G&L statements directory
            gl_records = []
            
            # Use auto-discovery to find all G&L statement files in the directory
            gl_files = self.settings.get_gl_statement_files(use_auto_discovery=True)
            logger.info(f"Auto-discovered {len(gl_files)} G&L statement files for processing")
            
            for gl_path in gl_files:
                try:
                    gl_loader = GLStatementLoader(gl_path)
                    gl_file_records = gl_loader.get_validated_records()
                    gl_records.extend(gl_file_records)
                    logger.info(f"✅ Loaded {len(gl_file_records)} G&L records from {gl_path.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load G&L data from {gl_path}: {e}")
                    
            progress.update(task2, advance=1)
            logger.info(f"📊 Total G&L records loaded from {len(gl_files)} Excel files: {len(gl_records)}")
            
            # Load SBI Exchange Rates using AUTO-DISCOVERY
            sbi_records = []
            exchange_rate_files = self.settings.discover_exchange_rate_files()
            
            if exchange_rate_files:
                # Use the first exchange rate file found, or merge multiple if needed
                primary_sbi_file = exchange_rate_files[0]  # Most common case: one main file
                logger.info(f"Using exchange rate file: {primary_sbi_file.name}")
                
                try:
                    sbi_loader = SBIRatesLoader(primary_sbi_file)
                    sbi_records = sbi_loader.get_validated_records()
                    logger.info(f"✅ Loaded {len(sbi_records)} SBI exchange rate records")
                except Exception as e:
                    logger.error(f"❌ Failed to load SBI rates from {primary_sbi_file}: {e}")
                    
            else:
                # Fallback to configured path
                logger.warning("No exchange rate files found via auto-discovery, using configured path")
                if self.settings.sbi_ttbr_rates_path.exists():
                    try:
                        sbi_loader = SBIRatesLoader(self.settings.sbi_ttbr_rates_path)
                        sbi_records = sbi_loader.get_validated_records()
                        logger.info(f"✅ Loaded {len(sbi_records)} SBI exchange rate records (fallback)")
                    except Exception as e:
                        logger.error(f"❌ Failed to load SBI rates from configured path: {e}")
                else:
                    logger.error("❌ No SBI exchange rate files found")
                    
            progress.update(task3, advance=1)
            
            # Load Adobe Stock Data using AUTO-DISCOVERY
            stock_records = []
            adobe_stock_files = self.settings.discover_adobe_stock_files()
            
            if adobe_stock_files:
                # Use the first stock file found, or merge multiple if needed
                primary_stock_file = adobe_stock_files[0]  # Most common case: one main file
                logger.info(f"Using Adobe stock file: {primary_stock_file.name}")
                
                try:
                    stock_loader = AdobeStockDataLoader(primary_stock_file)
                    stock_records = stock_loader.get_validated_records()
                    logger.info(f"✅ Loaded {len(stock_records)} Adobe stock price records")
                except Exception as e:
                    logger.error(f"❌ Failed to load Adobe stock data from {primary_stock_file}: {e}")
                    
            else:
                # Fallback to configured path  
                logger.warning("No Adobe stock files found via auto-discovery, using configured path")
                if self.settings.adobe_stock_data_path.exists():
                    try:
                        stock_loader = AdobeStockDataLoader(self.settings.adobe_stock_data_path)
                        stock_records = stock_loader.get_validated_records()
                        logger.info(f"✅ Loaded {len(stock_records)} Adobe stock price records (fallback)")
                    except Exception as e:
                        logger.error(f"❌ Failed to load Adobe stock data from configured path: {e}")
                else:
                    logger.error("❌ No Adobe stock data files found")
                    
            progress.update(task4, advance=1)
        
        return rsu_records, gl_records, sbi_records, stock_records
    
    def calculate_rsu_for_fy(
        self, 
        financial_year: Optional[str] = None,
        detailed: bool = False
    ) -> RSUCalculationResults:
        """
        Calculate RSU gains/losses for specified financial year.
        
        Args:
            financial_year: FY to calculate (e.g., 'FY2025'). If None, calculates all available FYs.
            detailed: Whether to include detailed transaction lists.
            
        Returns:
            Complete RSU calculation results.
        """
        
        logger.info(f"Starting RSU calculations for {financial_year or 'all financial years'}")
        
        # Load all data
        rsu_records, gl_records, sbi_records, stock_records = self.load_all_data()
        
        # Initialize calculator
        calculator = RSUCalculator(sbi_records, stock_records)
        
        # Process events
        self.console.print("🔄 Processing RSU transactions...")
        
        vesting_events = calculator.process_rsu_vesting_events(rsu_records)
        sale_events = calculator.process_sale_events(gl_records)
        
        logger.info(f"Processed {len(vesting_events)} vesting events and {len(sale_events)} sale events")
        
        # Determine financial years to calculate
        if financial_year:
            financial_years = [financial_year]
        else:
            # Get all unique FYs from events
            all_fys = set()
            all_fys.update(v.financial_year for v in vesting_events)
            all_fys.update(s.financial_year for s in sale_events)
            financial_years = sorted(list(all_fys))
            
        logger.info(f"Calculating summaries for financial years: {financial_years}")
        
        # Calculate summaries for each FY
        fy_summaries = {}
        for fy in financial_years:
            summary = calculator.calculate_fy_summary(fy, vesting_events, sale_events)
            fy_summaries[fy] = summary
            
            gain_loss_text = "net gain" if summary.net_gain_loss_inr >= 0 else "net loss"
            self.console.print(f"📊 {fy}: ₹{summary.net_gain_loss_inr:,.2f} {gain_loss_text}")
        
        # =================================================================================
        # RSU SERVICE AGGREGATION FORMULAS
        # =================================================================================
        #
        # This section aggregates RSU calculation results for tax reporting.
        # Key metrics for Indian tax compliance:
        #
        # FORMULA 1: Total Shares Calculation
        # Purpose: Aggregate share quantities across all events
        # Total_Vested_Shares = Σ(Vesting_Quantity) for filtered vesting events
        # Total_Sold_Shares = Σ(Sale_Quantity) for filtered sale events
        # Example: 15 + 12 + 10 = 37 total vested shares in FY24-25
        #
        # FORMULA 2: Total Vesting Income (Salary Addition)
        # Purpose: Aggregate all vesting income for salary tax calculation
        # Total_Vesting_Income_INR = Σ(Vesting_Income_INR) for filtered vesting events
        # Example: ₹72,457 + ₹118,558 + ₹201,676 = ₹1,548,193 total vesting income
        # Tax Treatment: Added to salary income, taxed at marginal rate (NOT capital gains tax)
        #
        # FORMULA 3: Total Capital Gains
        # Purpose: Aggregate all capital gains/losses for capital gains tax calculation
        # Total_Capital_Gains_INR = Σ(Sale_Capital_Gain_INR) for filtered sale events
        # Example: ₹22,548 + (₹-12,236) + (₹-11,590) = ₹-41,181 net capital loss
        # Tax Treatment: Short-term → salary rates, Long-term → 10% + cess
        #
        # FORMULA 4: Net Position (Total Financial Impact)
        # Purpose: Calculate total financial impact from RSU activities
        # Net_Position_INR = Total_Vesting_Income_INR + Total_Capital_Gains_INR
        # Example: ₹1,548,193 + (₹-41,181) = ₹1,507,012 total financial impact
        # Note: This is NOT a single tax amount - components taxed differently
        #
        # FILTERING LOGIC:
        # - If specific FY requested: Include only events in that financial year
        # - If no FY specified: Include all events across all financial years
        # Financial Year Definition: April 1 to March 31 (Indian tax year)
        # =================================================================================
        
        # Apply filtering logic based on requested financial year
        if financial_year:
            # Filter events to only include the requested financial year
            filtered_vestings = [v for v in vesting_events if v.financial_year == financial_year]
            filtered_sales = [s for s in sale_events if s.financial_year == financial_year]
        else:
            # Include all events if no specific FY requested
            filtered_vestings = vesting_events
            filtered_sales = sale_events
        
        # APPLY FORMULAS (see documentation above)
        # Formula 1: Aggregate share quantities
        total_vested = sum(v.vested_quantity for v in filtered_vestings)
        total_sold = sum(s.quantity_sold for s in filtered_sales)
        
        # Formula 2: Aggregate vesting income (taxable as salary)
        total_taxable_gain_inr = sum(v.taxable_gain_inr for v in filtered_vestings)
        
        # Formula 3: Aggregate capital gains/losses (separate tax treatment)
        total_capital_gains_inr = sum(s.capital_gain_inr for s in filtered_sales)
        
        # Formula 4: Calculate total financial impact (not a single tax category)
        net_position_inr = total_taxable_gain_inr + total_capital_gains_inr
        
        # Create results
        results = RSUCalculationResults(
            calculation_date=Date.today(),
            financial_year=financial_year or f"All ({min(financial_years)}-{max(financial_years)})",
            benefit_history_records=len(rsu_records),
            gl_statement_records=len(gl_records),
            sbi_rate_records=len(sbi_records),
            stock_data_records=len(stock_records),
            vesting_events=filtered_vestings if detailed else [],
            sale_events=filtered_sales if detailed else [],
            fy_summaries=fy_summaries,
            total_vested_quantity=total_vested,
            total_sold_quantity=total_sold,
            total_taxable_gain_inr=total_taxable_gain_inr,
            total_capital_gains_inr=total_capital_gains_inr,
            net_position_inr=net_position_inr
        )
        
        # Log summary
        logger.info(f"RSU Calculation Summary:")
        logger.info(f"  Total Vested: {total_vested:,.2f} shares")
        logger.info(f"  Total Sold: {total_sold:,.2f} shares") 
        logger.info(f"  Taxable Gains: ₹{total_taxable_gain_inr:,.2f}")
        logger.info(f"  Capital Gains: ₹{total_capital_gains_inr:,.2f}")
        logger.info(f"  Net Position: ₹{net_position_inr:,.2f}")
        
        return results
    
    def validate_data_quality(self) -> Dict[str, Any]:
        """Validate data quality for RSU calculations."""
        
        logger.info("Validating data quality for RSU calculations")
        
        validation_results = {
            'success': True,
            'errors': [],
            'data': {},
            'summary': {}
        }
        
        # Validate RSU vesting data from ALL RSU PDFs
        all_rsu_records = []
        
        for rsu_path in self.settings.rsu_pdf_paths:
            try:
                if rsu_path.exists():
                    rsu_loader = RSULoader(rsu_path)
                    rsu_file_records = rsu_loader.get_validated_records(str(rsu_path))
                    all_rsu_records.extend(rsu_file_records)
                    logger.info(f"✓ RSU data validation successful for {rsu_path.name}: {len(rsu_file_records)} records")
                else:
                    logger.warning(f"RSU PDF not found for validation: {rsu_path}")
                    
            except Exception as e:
                validation_results['success'] = False
                validation_results['errors'].append(f"RSU Data ({rsu_path.name}): {e}")
                logger.error(f"✗ RSU data validation failed for {rsu_path.name}: {e}")
        
        # Store combined RSU records
        validation_results['data']['rsu_vesting'] = all_rsu_records
        validation_results['summary']['rsu_vesting'] = len(all_rsu_records)
        logger.info(f"✓ Total RSU vesting data validation from {len(self.settings.rsu_pdf_paths)} PDFs: {len(all_rsu_records)} records")
        
        try:
            # Validate G&L Statements
            gl_records = []
            for gl_path in self.settings.gl_statements_paths:
                if gl_path.exists():
                    gl_loader = GLStatementLoader(gl_path)
                    gl_file_records = gl_loader.get_validated_records()
                    gl_records.extend(gl_file_records)
                    logger.info(f"✓ {gl_path.name} validation successful: {len(gl_file_records)} records")
            validation_results['data']['gl_statements'] = gl_records
            validation_results['summary']['gl_statements'] = len(gl_records)
            
        except Exception as e:
            validation_results['success'] = False
            validation_results['errors'].append(f"G&L Statements: {e}")
            logger.error(f"✗ G&L statements validation failed: {e}")
        
        try:
            # Validate SBI Rates
            sbi_loader = SBIRatesLoader(self.settings.sbi_ttbr_rates_path)
            sbi_records = sbi_loader.get_validated_records()
            validation_results['data']['sbi_rates'] = sbi_records
            validation_results['summary']['sbi_rates'] = len(sbi_records)
            logger.info(f"✓ SBI rates validation successful: {len(sbi_records)} records")
            
        except Exception as e:
            validation_results['success'] = False
            validation_results['errors'].append(f"SBI Rates: {e}")
            logger.error(f"✗ SBI rates validation failed: {e}")
        
        try:
            # Validate Adobe Stock Data
            stock_loader = AdobeStockDataLoader(self.settings.adobe_stock_data_path)
            stock_records = stock_loader.get_validated_records()
            validation_results['data']['stock_data'] = stock_records
            validation_results['summary']['stock_data'] = len(stock_records)
            logger.info(f"✓ Adobe stock data validation successful: {len(stock_records)} records")
            
        except Exception as e:
            validation_results['success'] = False
            validation_results['errors'].append(f"Adobe Stock Data: {e}")
            logger.error(f"✗ Adobe stock data validation failed: {e}")
        
        # Additional RSU-specific validations
        if validation_results['success']:
            logger.info("✅ Data quality validation passed")
            self.console.print("✅ All data sources validated successfully")
        else:
            logger.warning("⚠️  Data quality issues detected")
            for error in validation_results['errors']:
                self.console.print(f"⚠️  {error}")
        
        return validation_results
    
    def get_transaction_details(
        self, 
        grant_number: Optional[str] = None,
        financial_year: Optional[str] = None
    ) -> Dict[str, List]:
        """Get detailed transaction information for specific grants or FY."""
        
        # Load data and calculate
        results = self.calculate_rsu_for_fy(financial_year, detailed=True)
        
        filtered_transactions = {
            'vestings': results.vesting_events,
            'sales': results.sale_events
        }
        
        # Filter by grant number if specified
        if grant_number:
            filtered_transactions['vestings'] = [
                v for v in results.vesting_events if v.grant_number == grant_number
            ]
            filtered_transactions['sales'] = [
                s for s in results.sale_events if s.grant_number == grant_number
            ]
            
            logger.info(f"Found {len(filtered_transactions['vestings'])} vestings and "
                       f"{len(filtered_transactions['sales'])} sales for grant {grant_number}")
        
        return filtered_transactions
    
    def export_calculation_summary(self, results: RSUCalculationResults, output_path: Path) -> None:
        """Export calculation summary to file (placeholder for Phase 5)."""
        
        # This will be implemented in Phase 5: Report Generation
        logger.info(f"Export functionality will be implemented in Phase 5")
        logger.info(f"Results summary: {len(results.fy_summaries)} FY summaries, "
                   f"₹{results.net_position_inr:,.2f} net position")
