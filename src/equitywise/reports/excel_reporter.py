"""Excel report generation for RSU and FA calculations."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from loguru import logger

from ..calculators.rsu_calculator import RSUCalculationSummary, VestingEvent, SaleEvent
from ..calculators.fa_calculator import FADeclarationSummary, EquityHolding, VestWiseDetails


class ExcelReporter:
    """Excel report generator for RSU and FA calculations."""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize Excel reporter.
        
        Args:
            output_dir: Directory to save Excel reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Excel styling
        self.header_font = Font(bold=True, color="FFFFFF", size=12)
        self.header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        self.currency_format = '₹#,##0.00'
        self.number_format = '#,##0.00'
        self.date_format = 'DD/MM/YYYY'
        
        # Borders
        thin_border = Side(border_style="thin", color="000000")
        self.border = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)
    
    def generate_rsu_report(
        self,
        summary: RSUCalculationSummary,
        vesting_events: List[VestingEvent],
        sale_events: List[SaleEvent],
        bank_transactions: Optional[List[Dict]] = None,
        financial_year: str = None,
        detailed: bool = True
    ) -> Path:
        """Generate comprehensive RSU Excel report.
        
        Args:
            summary: RSU calculation summary
            vesting_events: List of vesting events
            sale_events: List of sale events  
            bank_transactions: Bank statement transactions
            financial_year: Financial year for the report
            detailed: Include detailed breakdowns
            
        Returns:
            Path to generated Excel file
        """
        logger.info(f"Generating RSU Excel report for {financial_year or 'all years'}")
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fy_suffix = f"_{financial_year}" if financial_year else ""
        filename = f"RSU_Report{fy_suffix}_{timestamp}.xlsx"
        filepath = self.output_dir / filename
        
        # Create workbook
        wb = Workbook()
        
        # Remove default sheet
        wb.remove(wb.active)
        
        # Create sheets
        self._create_rsu_summary_sheet(wb, summary, financial_year)
        
        if detailed:
            if vesting_events:
                self._create_vesting_events_sheet(wb, vesting_events)
            if sale_events:
                self._create_sale_events_sheet(wb, sale_events)
            if bank_transactions:
                self._create_bank_reconciliation_sheet(wb, sale_events, bank_transactions)
        
        # Save workbook
        wb.save(filepath)
        logger.info(f"RSU Excel report saved: {filepath}")
        
        return filepath
    
    def generate_fa_report(
        self,
        summary: FADeclarationSummary,
        equity_holdings: List[EquityHolding] = None,
        vest_wise_details: List[VestWiseDetails] = None,
        calendar_year: str = None,
        detailed: bool = True
    ) -> Path:
        """Generate comprehensive FA Excel report.
        
        Args:
            summary: FA declaration summary
            equity_holdings: Current equity holdings
            vest_wise_details: Vest-wise breakdown details
            calendar_year: Calendar year for the report
            detailed: Include detailed breakdowns
            
        Returns:
            Path to generated Excel file
        """
        logger.info(f"Generating FA Excel report for {calendar_year or 'all years'}")
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cy_suffix = f"_{calendar_year}" if calendar_year else ""
        filename = f"FA_Report{cy_suffix}_{timestamp}.xlsx"
        filepath = self.output_dir / filename
        
        # Create workbook
        wb = Workbook()
        
        # Remove default sheet
        wb.remove(wb.active)
        
        # Create sheets
        self._create_fa_summary_sheet(wb, summary, calendar_year)
        self._create_company_details_sheet(wb)  # Add company & account details sheet
        
        if detailed:
            if equity_holdings:
                self._create_equity_holdings_sheet(wb, equity_holdings)
            if vest_wise_details:
                self._create_vest_wise_details_sheet(wb, vest_wise_details)
        
        # Save workbook
        wb.save(filepath)
        logger.info(f"FA Excel report saved: {filepath}")
        
        return filepath
    
    def _create_rsu_summary_sheet(self, wb: Workbook, summary: RSUCalculationSummary, financial_year: str):
        """Create RSU summary sheet."""
        ws = wb.create_sheet("RSU Summary")
        
        # Title
        ws.merge_cells('A1:D1')
        title_cell = ws['A1']
        title_cell.value = f"RSU Tax Summary - {financial_year or 'All Years'}"
        title_cell.font = Font(bold=True, size=16, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        
        # Summary data
        summary_data = [
            ["", "Metric", "USD Amount", "INR Amount"],
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
        
        # Add data to sheet
        for row_idx, row_data in enumerate(summary_data, start=3):
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                
                # Style header row
                if row_idx == 3:
                    cell.font = self.header_font
                    cell.fill = self.header_fill
                    cell.alignment = Alignment(horizontal="center")
                
                # Style totals row
                elif "Net Financial Impact" in str(value):
                    cell.font = Font(bold=True, size=12)
                    cell.fill = PatternFill(start_color="D6EAF8", end_color="D6EAF8", fill_type="solid")
                
                cell.border = self.border
        
        # Auto-adjust column widths (skip merged cells)
        for col_index, col in enumerate(ws.columns, 1):
            max_length = 0
            column_letter = None
            for cell in col:
                # Skip merged cells by checking if the cell has column_letter attribute
                if hasattr(cell, 'column_letter'):
                    column_letter = cell.column_letter
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
            if column_letter:
                adjusted_width = min(max_length + 2, 30)
                ws.column_dimensions[column_letter].width = adjusted_width
    
    def _create_vesting_events_sheet(self, wb: Workbook, vesting_events: List[VestingEvent]):
        """Create vesting events sheet."""
        ws = wb.create_sheet("Vesting Events")
        
        # Convert to DataFrame for easier manipulation
        vesting_data = []
        for event in vesting_events:
            vesting_data.append({
                'Vesting Date': event.vest_date.strftime('%d/%m/%Y'),
                'Grant Number': event.grant_number,
                'Shares Vested': f"{event.vested_quantity:.0f}",
                'FMV per Share (USD)': f"${event.vest_fmv_usd:.2f}",
                'Exchange Rate': f"₹{event.exchange_rate:.4f}",
                'Vesting Value (USD)': f"${event.taxable_gain_usd:.2f}",
                'Vesting Value (INR)': f"₹{event.taxable_gain_inr:.2f}",
                'Financial Year': event.financial_year
            })
        
        df = pd.DataFrame(vesting_data)
        
        # Add title
        ws.merge_cells('A1:H1')
        title_cell = ws['A1']
        title_cell.value = "RSU Vesting Events"
        title_cell.font = Font(bold=True, size=14, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        
        # Add DataFrame to sheet
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=3):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)
                
                # Style header row
                if r_idx == 3:
                    cell.font = self.header_font
                    cell.fill = self.header_fill
                    cell.alignment = Alignment(horizontal="center")
                
                cell.border = self.border
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter if hasattr(col[0], 'column_letter') else None
            if not column:
                continue
            for cell in col:
                if hasattr(cell, 'column_letter') and cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = min(max_length + 2, 25)
            ws.column_dimensions[column].width = adjusted_width
    
    def _create_sale_events_sheet(self, wb: Workbook, sale_events: List[SaleEvent]):
        """Create sale events sheet."""
        ws = wb.create_sheet("Sale Events")
        
        # Convert to DataFrame
        sale_data = []
        for event in sale_events:
            sale_data.append({
                'Sale Date': event.sale_date.strftime('%d/%m/%Y'),
                'Vest Date': event.acquisition_date.strftime('%d/%m/%Y'),
                'Grant Number': event.grant_number,
                'Shares Sold': f"{event.quantity_sold:.0f}",
                'Sale Price (USD)': f"${event.sale_price_usd:.2f}",
                'Exchange Rate': f"₹{event.exchange_rate_sale:.4f}",
                'Sale Proceeds (USD)': f"${event.sale_proceeds_usd:.2f}",
                'Sale Proceeds (INR)': f"₹{event.sale_proceeds_inr:.2f}",
                'Cost Basis (USD)': f"${event.cost_basis_usd:.2f}",
                'Cost Basis (INR)': f"₹{event.cost_basis_inr:.2f}",
                'Capital Gain (USD)': f"${event.capital_gain_usd:.2f}",
                'Capital Gain (INR)': f"₹{event.capital_gain_inr:.2f}",
                'Holding Period': f"{event.holding_period_days} days",
                'Gain Type': event.gain_type,
                'Financial Year': event.financial_year
            })
        
        df = pd.DataFrame(sale_data)
        
        # Add title
        ws.merge_cells('A1:O1')
        title_cell = ws['A1']
        title_cell.value = "RSU Sale Events"
        title_cell.font = Font(bold=True, size=14, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        
        # Add DataFrame to sheet
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=3):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)
                
                # Style header row
                if r_idx == 3:
                    cell.font = self.header_font
                    cell.fill = self.header_fill
                    cell.alignment = Alignment(horizontal="center")
                
                cell.border = self.border
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter if hasattr(col[0], 'column_letter') else None
            if not column:
                continue
            for cell in col:
                if hasattr(cell, 'column_letter') and cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = min(max_length + 2, 20)
            ws.column_dimensions[column].width = adjusted_width
    
    def _create_bank_reconciliation_sheet(self, wb: Workbook, sale_events: List[SaleEvent], bank_transactions: List[Dict]):
        """Create bank reconciliation sheet."""
        ws = wb.create_sheet("Bank Reconciliation")
        
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
            
            expected_inr = total_usd * events[0].exchange_rate_sale
            bank_received_inr = bank_match.get('inr_after_gst', 0) if bank_match else 0
            # Net Difference: Final Received - Expected (positive=gain, negative=loss)
            net_difference = bank_received_inr - expected_inr if bank_match else 0
            
            recon_data.append({
                'Sale Date': sale_date.strftime('%d/%m/%Y'),
                'Expected USD': f"${total_usd:.2f}",
                'Expected INR': f"₹{expected_inr:.2f}",
                'Bank Received USD': f"${bank_match.get('usd_amount', 0):.2f}" if bank_match else "Not Found",
                'Bank Received INR': f"₹{bank_received_inr:.2f}" if bank_match else "Not Found",
                'Net Difference INR': f"₹{net_difference:.2f}" if bank_match else "N/A",
                'Transfer Expense': f"${total_usd - bank_match.get('usd_amount', 0):.2f}" if bank_match else "N/A",
                'Exchange Rate Diff': f"₹{bank_match.get('exchange_rate_gain_loss', 0):.2f}" if bank_match else "N/A"
            })
        
        df = pd.DataFrame(recon_data)
        
        # Add title
        ws.merge_cells('A1:H1')
        title_cell = ws['A1']
        title_cell.value = "Bank Reconciliation"
        title_cell.font = Font(bold=True, size=14, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        
        # Add DataFrame to sheet
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=3):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)
                
                # Style header row
                if r_idx == 3:
                    cell.font = self.header_font
                    cell.fill = self.header_fill
                    cell.alignment = Alignment(horizontal="center")
                
                cell.border = self.border
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter if hasattr(col[0], 'column_letter') else None
            if not column:
                continue
            for cell in col:
                if hasattr(cell, 'column_letter') and cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = min(max_length + 2, 20)
            ws.column_dimensions[column].width = adjusted_width
    
    def _create_fa_summary_sheet(self, wb: Workbook, summary: FADeclarationSummary, calendar_year: str):
        """Create FA summary sheet."""
        ws = wb.create_sheet("FA Summary")
        
        # Title
        ws.merge_cells('A1:D1')
        title_cell = ws['A1']
        title_cell.value = f"Foreign Assets Declaration - {calendar_year or 'All Years'}"
        title_cell.font = Font(bold=True, size=16, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        
        # Summary data
        summary_data = [
            ["", "Metric", "Value", "Notes"],
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
        
        # Add data to sheet
        for row_idx, row_data in enumerate(summary_data, start=3):
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                
                # Style header row
                if row_idx == 3:
                    cell.font = self.header_font
                    cell.fill = self.header_fill
                    cell.alignment = Alignment(horizontal="center")
                
                # Style declaration row
                elif "Declaration Required" in str(value):
                    cell.font = Font(bold=True, size=12)
                    if "YES" in str(row_data[2]):
                        cell.fill = PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid")
                    else:
                        cell.fill = PatternFill(start_color="D5F4E6", end_color="D5F4E6", fill_type="solid")
                
                cell.border = self.border
        
        # Auto-adjust column widths (skip merged cells)
        for col_index, col in enumerate(ws.columns, 1):
            max_length = 0
            column_letter = None
            for cell in col:
                # Skip merged cells by checking if the cell has column_letter attribute
                if hasattr(cell, 'column_letter'):
                    column_letter = cell.column_letter
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
            if column_letter:
                adjusted_width = min(max_length + 2, 30)
                ws.column_dimensions[column_letter].width = adjusted_width
    
    def _create_equity_holdings_sheet(self, wb: Workbook, equity_holdings: List[EquityHolding]):
        """Create equity holdings sheet."""
        ws = wb.create_sheet("Equity Holdings")
        
        # Convert to DataFrame
        holdings_data = []
        for holding in equity_holdings:
            holdings_data.append({
                'Grant Number': holding.grant_number or 'N/A',
                'Vest Date': holding.vest_date.strftime('%d/%m/%Y') if holding.vest_date else 'N/A',
                'Holding Date': holding.holding_date.strftime('%d/%m/%Y'),
                'Shares Held': f"{holding.quantity:.0f}",
                'Cost Basis per Share (USD)': f"${holding.cost_basis_usd_per_share:.2f}",
                'Market Price per Share (USD)': f"${holding.market_value_usd_per_share:.2f}",
                'Total Cost Basis (USD)': f"${holding.cost_basis_usd_total:.2f}",
                'Total Market Value (USD)': f"${holding.market_value_usd_total:.2f}",
                'Total Market Value (INR)': f"₹{holding.market_value_inr_total:.2f}",
                'Exchange Rate': f"₹{holding.exchange_rate:.4f}",
                'Unrealized Gain (USD)': f"${holding.unrealized_gain_usd:.2f}",
                'Unrealized Gain (INR)': f"₹{holding.unrealized_gain_inr:.2f}",
                'Calendar Year': holding.calendar_year
            })
        
        df = pd.DataFrame(holdings_data)
        
        # Add title
        ws.merge_cells('A1:M1')
        title_cell = ws['A1']
        title_cell.value = "Current Equity Holdings"
        title_cell.font = Font(bold=True, size=14, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        
        # Add DataFrame to sheet
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=3):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)
                
                # Style header row
                if r_idx == 3:
                    cell.font = self.header_font
                    cell.fill = self.header_fill
                    cell.alignment = Alignment(horizontal="center")
                
                cell.border = self.border
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter if hasattr(col[0], 'column_letter') else None
            if not column:
                continue
            for cell in col:
                if hasattr(cell, 'column_letter') and cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = min(max_length + 2, 20)
            ws.column_dimensions[column].width = adjusted_width
    
    def _create_vest_wise_details_sheet(self, wb: Workbook, vest_wise_details: List[VestWiseDetails]):
        """Create vest-wise details sheet."""
        ws = wb.create_sheet("Vest-wise Details")
        
        # Convert to DataFrame
        vest_data = []
        for detail in vest_wise_details:
            vest_data.append({
                'Grant Number': detail.grant_number,
                'Vest Date': detail.vest_date.strftime('%d/%m/%Y'),
                'Initial Value (INR)': f"₹{detail.initial_value_inr:.2f}",
                'Peak Value (INR)': f"₹{detail.peak_value_inr:.2f}",
                'Closing Value (INR)': f"₹{detail.closing_value_inr:.2f}",
                'Gross Income (INR)': f"₹{detail.gross_income_received:.2f}",
                'Sale Proceeds (INR)': f"₹{detail.gross_proceeds_inr:.2f}",
                'Shares at Year-end': f"{detail.closing_shares:.0f}",
                'Shares Sold': f"{detail.shares_sold:.0f}"
            })
        
        df = pd.DataFrame(vest_data)
        
        # Add title
        ws.merge_cells('A1:H1')
        title_cell = ws['A1']
        title_cell.value = "Vest-wise Investment Details"
        title_cell.font = Font(bold=True, size=14, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        
        # Add DataFrame to sheet
        data_start_row = 3
        current_row = data_start_row
        
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=data_start_row):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)
                
                # Style header row
                if r_idx == data_start_row:
                    cell.font = self.header_font
                    cell.fill = self.header_fill
                    cell.alignment = Alignment(horizontal="center")
                
                cell.border = self.border
            current_row = r_idx
        
        # Add total row for Sale Proceeds
        total_sale_proceeds = sum(detail.gross_proceeds_inr for detail in vest_wise_details if detail.gross_proceeds_inr > 0)
        
        if total_sale_proceeds > 0:
            total_row = current_row + 1
            
            # Column mapping based on DataFrame structure:
            # 1: Grant Number, 2: Vest Date, 3: Initial Value, 4: Peak Value, 
            # 5: Closing Value, 6: Gross Income, 7: Sale Proceeds, 8: Shares at Year-end, 9: Shares Sold
            
            # Add TOTAL label in first column
            total_cell = ws.cell(row=total_row, column=1, value="TOTAL")
            total_cell.font = Font(bold=True)
            total_cell.border = self.border
            
            # Add dashes for columns 2-6 (Vest Date through Gross Income)
            for col in range(2, 7):
                cell = ws.cell(row=total_row, column=col, value="-")
                cell.font = Font(bold=True)
                cell.border = self.border
                cell.alignment = Alignment(horizontal="center")
            
            # Add total sale proceeds in the Sale Proceeds column (column 7)  
            proceeds_cell = ws.cell(row=total_row, column=7, value=f"₹{total_sale_proceeds:,.2f}")
            proceeds_cell.font = Font(bold=True)
            proceeds_cell.border = self.border
            proceeds_cell.alignment = Alignment(horizontal="right")
            
            # Add dashes for remaining columns (8-9: Shares at Year-end, Shares Sold)
            for col in range(8, len(df.columns) + 1):
                cell = ws.cell(row=total_row, column=col, value="-")
                cell.font = Font(bold=True)
                cell.border = self.border
                cell.alignment = Alignment(horizontal="center")
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter if hasattr(col[0], 'column_letter') else None
            if not column:
                continue
            for cell in col:
                if hasattr(cell, 'column_letter') and cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = min(max_length + 2, 20)
            ws.column_dimensions[column].width = adjusted_width
    def _create_company_details_sheet(self, wb: Workbook):
        """Create company and depository account details sheet for FA filing."""
        from ..data.models import create_default_company_records
        
        ws = wb.create_sheet("Company & Account Details")
        
        # Get company and depository account details
        employer_company, foreign_company, depository_account = create_default_company_records()
        
        # Title
        ws.merge_cells('A1:F1')
        title_cell = ws['A1']
        title_cell.value = "Company & Depository Account Details for FA Filing"
        title_cell.font = Font(bold=True, size=16, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="2F75B5", end_color="2F75B5", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        
        # Company Information Section
        row = 3
        ws.merge_cells(f'A{row}:F{row}')
        section_cell = ws[f'A{row}']
        section_cell.value = "📋 Company Information"
        section_cell.font = Font(bold=True, size=14)
        section_cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
        section_cell.alignment = Alignment(horizontal="center")
        
        # Company headers
        row += 1
        headers = ["Type", "Company Name", "Address", "City/State", "ZIP/PIN", "ID/TAN"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            cell.border = self.border
        
        # Employer company data
        row += 1
        employer_data = [
            "Employer (India)",
            employer_company.company_name,
            employer_company.address_line1,
            f"{employer_company.city}, {employer_company.state}",
            employer_company.pin_code,
            employer_company.tan
        ]
        for col, value in enumerate(employer_data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = self.border
        
        # Foreign company data
        row += 1
        foreign_data = [
            "Foreign Entity",
            foreign_company.company_name,
            foreign_company.address_line1,
            f"{foreign_company.city}, {foreign_company.state_province}",
            foreign_company.zip_code,
            f"Country Code: {foreign_company.country_code}"
        ]
        for col, value in enumerate(foreign_data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = self.border
        
        # Depository Account Information Section
        row += 3
        ws.merge_cells(f'A{row}:F{row}')
        section_cell = ws[f'A{row}']
        section_cell.value = "🏛️ Foreign Depository Account Information"
        section_cell.font = Font(bold=True, size=14)
        section_cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
        section_cell.alignment = Alignment(horizontal="center")
        
        # Account headers
        row += 1
        account_headers = ["Institution", "Address", "Account Number", "Status", "Opening Date", "Country"]
        for col, header in enumerate(account_headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            cell.border = self.border
        
        # Depository account data
        row += 1
        institution_address = f"{depository_account.institution_address}, {depository_account.institution_city}, {depository_account.institution_state} {depository_account.institution_zip}"
        account_data = [
            depository_account.institution_name,
            institution_address,
            depository_account.account_number,
            depository_account.account_status,
            depository_account.account_opening_date.strftime("%d/%m/%Y"),
            f"{depository_account.institution_country} (Code: {depository_account.institution_country_code})"
        ]
        for col, value in enumerate(account_data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = self.border
        
        # ITR Schedule References Section
        row += 3
        ws.merge_cells(f'A{row}:F{row}')
        section_cell = ws[f'A{row}']
        section_cell.value = "📄 ITR Schedule References"
        section_cell.font = Font(bold=True, size=14)
        section_cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
        section_cell.alignment = Alignment(horizontal="center")
        
        # ITR reference notes
        row += 2
        itr_notes = [
            "Schedule A1 - Foreign Depository Accounts:",
            f"  • Institution: {depository_account.institution_name}",
            f"  • Account: {depository_account.account_number} ({depository_account.account_status})",
            f"  • Address: {institution_address}",
            "",
            "Schedule A3 - Foreign Equity and Debt Interest:",
            f"  • Entity: {foreign_company.company_name}",
            f"  • Address: {foreign_company.address_line1}, {foreign_company.city}, {foreign_company.state_province} {foreign_company.zip_code}",
            f"  • Country: {foreign_company.country_name} (Code: {foreign_company.country_code})",
            f"  • Nature: {foreign_company.nature_of_entity}",
            "",
            "💡 Important Notes:",
            "  • These details are extracted from your previous ITR filing",
            "  • Country Code 2 = United States of America",
            "  • Use these exact details when filling FA schedules to maintain consistency"
        ]
        
        for note in itr_notes:
            ws.cell(row=row, column=1, value=note)
            row += 1
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter if hasattr(col[0], 'column_letter') else None
            if not column:
                continue
            for cell in col:
                if hasattr(cell, 'column_letter') and cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = min(max_length + 2, 30)  # Slightly wider for this sheet
            ws.column_dimensions[column].width = adjusted_width
