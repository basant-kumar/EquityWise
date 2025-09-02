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
    GLStatementLoader, SBIRatesLoader, AdobeStockDataLoader, ESOPLoader
)
from ..data.models import (
    GLStatementRecord, SBIRateRecord, AdobeStockRecord, ESOPVestingRecord
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
        List[ESOPVestingRecord], 
        List[GLStatementRecord], 
        List[SBIRateRecord], 
        List[AdobeStockRecord]
    ]:
        """Load all required data sources."""
        
        logger.info("Loading RSU calculation data from all sources")
        
        with Progress() as progress:
            # Create progress tasks
            task1 = progress.add_task("Loading ESOP Vesting Data...", total=1)
            task2 = progress.add_task("Loading G&L Statements...", total=1) 
            task3 = progress.add_task("Loading SBI Rates...", total=1)
            task4 = progress.add_task("Loading Stock Data...", total=1)
            
            # Load ESOP vesting data from ALL ESOP PDFs for comprehensive history
            all_esop_records = []
            
            # Load from all configured ESOP PDF paths
            for esop_path in self.settings.esop_pdf_paths:
                if esop_path.exists():
                    try:
                        esop_loader = ESOPLoader(esop_path)
                        esop_file_records = esop_loader.get_validated_records(str(esop_path))
                        all_esop_records.extend(esop_file_records)
                        logger.info(f"Loaded {len(esop_file_records)} ESOP vesting records from {esop_path.name}")
                    except Exception as e:
                        logger.error(f"Failed to load ESOP data from {esop_path}: {e}")
                else:
                    logger.warning(f"ESOP PDF not found: {esop_path}")
            
            esop_records = all_esop_records
            progress.update(task1, advance=1)
            logger.info(f"Total ESOP vesting records loaded from {len(self.settings.esop_pdf_paths)} PDFs: {len(esop_records)}")
            
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
        
        return esop_records, gl_records, sbi_records, stock_records
    
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
        esop_records, gl_records, sbi_records, stock_records = self.load_all_data()
        
        # Initialize calculator
        calculator = RSUCalculator(sbi_records, stock_records)
        
        # Process events
        self.console.print("🔄 Processing RSU transactions...")
        
        vesting_events = calculator.process_esop_vesting_events(esop_records)
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
            benefit_history_records=len(esop_records),
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
        """Validate data quality for ESOP-based RSU calculations."""
        
        logger.info("Validating data quality for RSU calculations")
        
        validation_results = {
            'success': True,
            'errors': [],
            'data': {},
            'summary': {}
        }
        
        # Validate ESOP vesting data from ALL ESOP PDFs
        all_esop_records = []
        
        for esop_path in self.settings.esop_pdf_paths:
            try:
                if esop_path.exists():
                    esop_loader = ESOPLoader(esop_path)
                    esop_file_records = esop_loader.get_validated_records(str(esop_path))
                    all_esop_records.extend(esop_file_records)
                    logger.info(f"✓ ESOP data validation successful for {esop_path.name}: {len(esop_file_records)} records")
                else:
                    logger.warning(f"ESOP PDF not found for validation: {esop_path}")
                    
            except Exception as e:
                validation_results['success'] = False
                validation_results['errors'].append(f"ESOP Data ({esop_path.name}): {e}")
                logger.error(f"✗ ESOP data validation failed for {esop_path.name}: {e}")
        
        # Store combined ESOP records
        validation_results['data']['esop_vesting'] = all_esop_records
        validation_results['summary']['esop_vesting'] = len(all_esop_records)
        logger.info(f"✓ Total ESOP vesting data validation from {len(self.settings.esop_pdf_paths)} PDFs: {len(all_esop_records)} records")
        
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
