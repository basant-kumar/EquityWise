"""CSV report generation for RSU and FA calculations."""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from loguru import logger

from ..calculators.rsu_calculator import RSUCalculationSummary, VestingEvent, SaleEvent
from ..calculators.fa_calculator import FADeclarationSummary, EquityHolding, VestWiseDetails


class CSVReporter:
    """CSV report generator for RSU and FA calculations."""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize CSV reporter.
        
        Args:
            output_dir: Directory to save CSV reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_rsu_report(
        self,
        summary: RSUCalculationSummary,
        vesting_events: List[VestingEvent],
        sale_events: List[SaleEvent],
        bank_transactions: Optional[List[Dict]] = None,
        financial_year: str = None,
        detailed: bool = True
    ) -> List[Path]:
        """Generate comprehensive RSU CSV reports.
        
        Args:
            summary: RSU calculation summary
            vesting_events: List of vesting events
            sale_events: List of sale events  
            bank_transactions: Bank statement transactions
            financial_year: Financial year for the report
            detailed: Include detailed breakdowns
            
        Returns:
            List of paths to generated CSV files
        """
        logger.info(f"Generating RSU CSV reports for {financial_year or 'all years'}")
        
        # Create base filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fy_suffix = f"_{financial_year}" if financial_year else ""
        
        generated_files = []
        
        # Generate summary CSV
        summary_file = self._create_rsu_summary_csv(summary, financial_year, timestamp, fy_suffix)
        generated_files.append(summary_file)
        
        if detailed:
            # Generate vesting events CSV
            if vesting_events:
                vesting_file = self._create_vesting_events_csv(vesting_events, timestamp, fy_suffix)
                generated_files.append(vesting_file)
            
            # Generate sale events CSV
            if sale_events:
                sale_file = self._create_sale_events_csv(sale_events, timestamp, fy_suffix)
                generated_files.append(sale_file)
            
            # Generate bank reconciliation CSV
            if bank_transactions:
                bank_file = self._create_bank_reconciliation_csv(sale_events, bank_transactions, timestamp, fy_suffix)
                generated_files.append(bank_file)
        
        logger.info(f"Generated {len(generated_files)} RSU CSV files")
        return generated_files
    
    def generate_fa_report(
        self,
        summary: FADeclarationSummary,
        equity_holdings: List[EquityHolding] = None,
        vest_wise_details: List[VestWiseDetails] = None,
        calendar_year: str = None,
        detailed: bool = True
    ) -> List[Path]:
        """Generate comprehensive FA CSV reports.
        
        Args:
            summary: FA declaration summary
            equity_holdings: Current equity holdings
            vest_wise_details: Vest-wise breakdown details
            calendar_year: Calendar year for the report
            detailed: Include detailed breakdowns
            
        Returns:
            List of paths to generated CSV files
        """
        logger.info(f"Generating FA CSV reports for {calendar_year or 'all years'}")
        
        # Create base filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cy_suffix = f"_{calendar_year}" if calendar_year else ""
        
        generated_files = []
        
        # Generate summary CSV
        summary_file = self._create_fa_summary_csv(summary, calendar_year, timestamp, cy_suffix)
        generated_files.append(summary_file)
        
        if detailed:
            # Generate equity holdings CSV
            if equity_holdings:
                holdings_file = self._create_equity_holdings_csv(equity_holdings, timestamp, cy_suffix)
                generated_files.append(holdings_file)
            
            # Generate vest-wise details CSV
            if vest_wise_details:
                vest_file = self._create_vest_wise_details_csv(vest_wise_details, timestamp, cy_suffix)
                generated_files.append(vest_file)
        
        logger.info(f"Generated {len(generated_files)} FA CSV files")
        return generated_files
    
    def _create_rsu_summary_csv(self, summary: RSUCalculationSummary, financial_year: str, timestamp: str, fy_suffix: str) -> Path:
        """Create RSU summary CSV file."""
        filename = f"RSU_Summary{fy_suffix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Prepare summary data
        summary_data = [
            ["RSU Tax Summary", financial_year or "All Years", "", ""],
            ["", "", "", ""],
            ["Category", "Metric", "USD Amount", "INR Amount"],
            ["Vesting", "Total Vested Shares", f"{summary.total_vested_quantity:.0f} shares", ""],
            ["", "Total Vesting Income", f"${summary.total_taxable_gain_usd:,.2f}", f"₹{summary.total_taxable_gain_inr:,.2f}"],
            ["", "Average Exchange Rate", f"₹{summary.average_exchange_rate:.4f}/USD", ""],
            ["", "", "", ""],
            ["Sales", "Total Sold Shares", f"{summary.total_sold_quantity:.0f} shares", ""],
            ["", "Total Capital Gains", f"${summary.total_capital_gains_usd:,.2f}", f"₹{summary.total_capital_gains_inr:,.2f}"],
            ["", "Short-term Gains", f"${summary.short_term_gains_usd:,.2f}", f"₹{summary.short_term_gains_inr:,.2f}"],
            ["", "Long-term Gains", f"${summary.long_term_gains_usd:,.2f}", f"₹{summary.long_term_gains_inr:,.2f}"],
            ["", "", "", ""],
            ["Total", "Net Financial Impact", "", f"₹{summary.net_gain_loss_inr:,.2f}"],
        ]
        
        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(summary_data)
        
        logger.info(f"RSU summary CSV saved: {filepath}")
        return filepath
    
    def _create_vesting_events_csv(self, vesting_events: List[VestingEvent], timestamp: str, fy_suffix: str) -> Path:
        """Create vesting events CSV file."""
        filename = f"RSU_Vesting_Events{fy_suffix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Convert to DataFrame for easy CSV export
        vesting_data = []
        for event in vesting_events:
            vesting_data.append({
                'Vesting Date': event.vest_date.strftime('%d/%m/%Y'),
                'Grant Number': event.grant_number,
                'Shares Vested': f"{event.vested_quantity:.0f}",
                'FMV per Share (USD)': f"{event.vest_fmv_usd:.2f}",
                'Exchange Rate': f"{event.exchange_rate:.4f}",
                'Vesting Value (USD)': f"{event.taxable_gain_usd:.2f}",
                'Vesting Value (INR)': f"{event.taxable_gain_inr:.2f}",
                'Financial Year': event.financial_year
            })
        
        df = pd.DataFrame(vesting_data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Vesting events CSV saved: {filepath}")
        return filepath
    
    def _create_sale_events_csv(self, sale_events: List[SaleEvent], timestamp: str, fy_suffix: str) -> Path:
        """Create sale events CSV file."""
        filename = f"RSU_Sale_Events{fy_suffix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Convert to DataFrame
        sale_data = []
        for event in sale_events:
            sale_data.append({
                'Sale Date': event.sale_date.strftime('%d/%m/%Y'),
                'Vest Date': event.acquisition_date.strftime('%d/%m/%Y'),
                'Grant Number': event.grant_number,
                'Shares Sold': f"{event.quantity_sold:.0f}",
                'Sale Price (USD)': f"{event.sale_price_usd:.2f}",
                'Exchange Rate': f"{event.exchange_rate_sale:.4f}",
                'Sale Proceeds (USD)': f"{event.sale_proceeds_usd:.2f}",
                'Sale Proceeds (INR)': f"{event.sale_proceeds_inr:.2f}",
                'Cost Basis (USD)': f"{event.cost_basis_usd:.2f}",
                'Capital Gain (USD)': f"{event.capital_gain_usd:.2f}",
                'Capital Gain (INR)': f"{event.capital_gain_inr:.2f}",
                'Holding Period (Days)': f"{event.holding_period_days}",
                'Gain Type': event.gain_type,
                'Financial Year': event.financial_year
            })
        
        df = pd.DataFrame(sale_data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Sale events CSV saved: {filepath}")
        return filepath
    
    def _create_bank_reconciliation_csv(self, sale_events: List[SaleEvent], bank_transactions: List[Dict], timestamp: str, fy_suffix: str) -> Path:
        """Create bank reconciliation CSV file."""
        filename = f"RSU_Bank_Reconciliation{fy_suffix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Group sale events by sale date for reconciliation
        from collections import defaultdict
        
        sale_by_date = defaultdict(list)
        for event in sale_events:
            sale_by_date[event.sale_date].append(event)
        
        # Create reconciliation data
        recon_data = []
        for sale_date, events in sale_by_date.items():
            total_usd = sum(event.sale_proceeds_usd for event in events)
            
            # Find matching bank transaction
            bank_match = None
            for tx in bank_transactions:
                if abs((tx['bank_date'] - sale_date).days) <= 7:  # Within 7 days
                    bank_match = tx
                    break
            
            recon_data.append({
                'Sale Date': sale_date.strftime('%d/%m/%Y'),
                'Expected USD': f"{total_usd:.2f}",
                'Expected INR': f"{total_usd * events[0].exchange_rate_sale:.2f}",
                'Bank Received USD': f"{bank_match.get('usd_amount', 0):.2f}" if bank_match else "Not Found",
                'Bank Received INR': f"{bank_match.get('inr_after_gst', 0):.2f}" if bank_match else "Not Found",
                'Transfer Expense (USD)': f"{total_usd - bank_match.get('usd_amount', 0):.2f}" if bank_match else "N/A",
                'Exchange Rate Diff (INR)': f"{bank_match.get('exchange_rate_gain_loss', 0):.2f}" if bank_match else "N/A"
            })
        
        df = pd.DataFrame(recon_data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Bank reconciliation CSV saved: {filepath}")
        return filepath
    
    def _create_fa_summary_csv(self, summary: FADeclarationSummary, calendar_year: str, timestamp: str, cy_suffix: str) -> Path:
        """Create FA summary CSV file."""
        filename = f"FA_Summary{cy_suffix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Prepare summary data
        summary_data = [
            ["Foreign Assets Declaration Summary", calendar_year or "All Years", "", ""],
            ["", "", "", ""],
            ["Category", "Metric", "Value", "Notes"],
            ["Holdings", "Total Vested Shares", f"{summary.total_vested_shares:.0f} shares", ""],
            ["", "Closing Balance", f"₹{summary.closing_balance_inr:,.2f}", "As on Dec 31"],
            ["", "Peak Balance", f"₹{summary.peak_balance_inr:,.2f}", f"Peak Date: {summary.peak_balance_date or 'N/A'}"],
            ["", "Opening Balance", f"₹{summary.opening_balance_inr:,.2f}", "As on Jan 1"],
            ["", "", "", ""],
            ["Exchange Rates", "Year-end Rate", f"₹{summary.year_end_exchange_rate:.4f}/USD", "Dec 31 rate"],
            ["", "Opening Rate", f"₹{summary.opening_exchange_rate:.4f}/USD", "Jan 1 rate"],
            ["", "Peak Rate", f"₹{summary.peak_exchange_rate:.4f}/USD", "Highest during year"],
            ["", "", "", ""],
            ["Declaration", "Declaration Required?", "YES" if summary.closing_balance_inr >= summary.fa_declaration_threshold_inr else "NO", f"Threshold: ₹{summary.fa_declaration_threshold_inr:,.0f}"],
            ["", "Total Value (USD)", f"${summary.vested_holdings_usd:,.2f}", "At year-end rates"],
            ["", "Total Value (INR)", f"₹{summary.vested_holdings_inr:,.2f}", "At year-end rates"]
        ]
        
        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(summary_data)
        
        logger.info(f"FA summary CSV saved: {filepath}")
        return filepath
    
    def _create_equity_holdings_csv(self, equity_holdings: List[EquityHolding], timestamp: str, cy_suffix: str) -> Path:
        """Create equity holdings CSV file."""
        filename = f"FA_Equity_Holdings{cy_suffix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Convert to DataFrame
        holdings_data = []
        for holding in equity_holdings:
            holdings_data.append({
                'Grant Number': holding.grant_number or 'N/A',
                'Vest Date': holding.vest_date.strftime('%d/%m/%Y') if holding.vest_date else 'N/A',
                'Holding Date': holding.holding_date.strftime('%d/%m/%Y'),
                'Shares Held': f"{holding.quantity:.0f}",
                'Cost Basis per Share (USD)': f"{holding.cost_basis_usd_per_share:.2f}",
                'Market Price per Share (USD)': f"{holding.market_value_usd_per_share:.2f}",
                'Total Cost Basis (USD)': f"{holding.cost_basis_usd_total:.2f}",
                'Total Market Value (USD)': f"{holding.market_value_usd_total:.2f}",
                'Total Market Value (INR)': f"{holding.market_value_inr_total:.2f}",
                'Exchange Rate': f"{holding.exchange_rate:.4f}",
                'Unrealized Gain (USD)': f"{holding.unrealized_gain_usd:.2f}",
                'Unrealized Gain (INR)': f"{holding.unrealized_gain_inr:.2f}",
                'Calendar Year': holding.calendar_year
            })
        
        df = pd.DataFrame(holdings_data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Equity holdings CSV saved: {filepath}")
        return filepath
    
    def _create_vest_wise_details_csv(self, vest_wise_details: List[VestWiseDetails], timestamp: str, cy_suffix: str) -> Path:
        """Create vest-wise details CSV file."""
        filename = f"FA_Vest_Wise_Details{cy_suffix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Convert to DataFrame
        vest_data = []
        for detail in vest_wise_details:
            vest_data.append({
                'Grant Number': detail.grant_number,
                'Vest Date': detail.vest_date.strftime('%d/%m/%Y'),
                'Initial Value (INR)': f"{detail.initial_value_inr:.2f}",
                'Peak Value (INR)': f"{detail.peak_value_inr:.2f}",
                'Closing Value (INR)': f"{detail.closing_value_inr:.2f}",
                'Gross Income (INR)': f"{detail.gross_income_received:.2f}",
                'Sale Proceeds (INR)': f"{detail.gross_proceeds_inr:.2f}",
                'Shares at Year-end': f"{detail.closing_shares:.0f}",
                'Shares Sold': f"{detail.shares_sold:.0f}"
            })
        
        df = pd.DataFrame(vest_data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Vest-wise details CSV saved: {filepath}")
        return filepath
    
    def generate_fa_declaration_csv(
        self,
        summary: FADeclarationSummary,
        calendar_year: str = None,
        template_path: Optional[Path] = None
    ) -> Path:
        """Generate FA declaration CSV ready for tax form import using template format.
        
        Args:
            summary: FA declaration summary with vest-wise details
            calendar_year: Calendar year for the report
            template_path: Path to FA declaration CSV template (optional)
            
        Returns:
            Path to generated FA declaration CSV file
        """
        logger.info(f"Generating FA declaration CSV for {calendar_year or 'current year'}")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cy_suffix = f"_{calendar_year}" if calendar_year else ""
        filename = f"FA_Declaration{cy_suffix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Load template headers if template provided
        template_headers = self._load_template_headers(template_path)
        
        # Create CSV data based on vest-wise details
        csv_data = self._create_fa_declaration_data(summary.vest_wise_details, template_headers)
        
        # Write CSV file
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write headers
            if template_headers:
                writer.writerow(template_headers)
            else:
                # Fallback headers if no template
                writer.writerow([
                    "Country/Region name",
                    "Country Name and Code", 
                    "Name of entity",
                    "Address of entity",
                    "ZIP Code",
                    "Nature of entity",
                    "Date of acquiring the interest",
                    "Initial value of the investment",
                    "Peak value of investment during the Period",
                    "Closing balance",
                    "Total gross amount paid/credited with respect to the holding during the period",
                    "Total gross proceeds from sale or redemption of investment during the period"
                ])
            
            # Write data rows
            writer.writerows(csv_data)
        
        logger.info(f"FA declaration CSV saved: {filepath}")
        logger.info(f"Generated {len(csv_data)} vest-wise entries for FA declaration")
        return filepath
    
    def _load_template_headers(self, template_path: Optional[Path]) -> Optional[List[str]]:
        """Load CSV headers from template file.
        
        Args:
            template_path: Path to template CSV file
            
        Returns:
            List of header strings, or None if no template
        """
        if not template_path or not template_path.exists():
            logger.debug("No template file provided or template file not found")
            return None
            
        try:
            with open(template_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader)  # Read first row as headers
                # Clean headers - remove empty strings and strip whitespace
                headers = [h.strip() for h in headers if h.strip()]
                logger.info(f"Loaded {len(headers)} headers from template: {template_path}")
                return headers
        except Exception as e:
            logger.error(f"Failed to load template headers: {e}")
            return None
    
    def _create_fa_declaration_data(self, vest_wise_details: List[VestWiseDetails], headers: Optional[List[str]]) -> List[List[str]]:
        """Create FA declaration data rows from vest-wise details.
        
        Args:
            vest_wise_details: List of vest-wise detail records
            headers: Optional list of headers to determine column order
            
        Returns:
            List of data rows for CSV export
        """
        csv_data = []
        
        for detail in vest_wise_details:
            # Standard row data
            row = [
                "United States of America",  # Country/Region name
                "United States of America (US)",  # Country Name and Code
                "Adobe Inc.",  # Name of entity
                "345 Park Avenue, San Jose, CA 95110-2704, United States",  # Address of entity
                "95110",  # ZIP Code
                "Listed Company",  # Nature of entity
                detail.vest_date.strftime("%d/%m/%Y"),  # Date of acquiring the interest
                f"{detail.initial_value_inr:.2f}",  # Initial value of the investment
                f"{detail.peak_value_inr:.2f}",  # Peak value during the Period
                f"{detail.closing_value_inr:.2f}",  # Closing balance
                "0.00",  # Total gross amount paid/credited during the period (vesting is non-cash)
                f"{detail.gross_proceeds_inr:.2f}" if detail.gross_proceeds_inr > 0 else "0.00"  # Sale proceeds
            ]
            
            csv_data.append(row)
        
        logger.debug(f"Created {len(csv_data)} data rows for FA declaration")
        return csv_data