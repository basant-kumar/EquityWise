"""
Main CLI interface for EquityWise.

This module provides the primary command-line interface for EquityWise,
a comprehensive solution for calculating tax obligations on equity compensation (RSU, ESOP, ESPP)
and Foreign Assets compliance under Indian tax law from E*Trade data.

Key Features:
- Interactive mode with guided workflows
- RSU tax calculations for Indian Financial Years (April-March)
- Foreign Assets compliance for Calendar Years (January-December)
- Multiple output formats (Excel, CSV, console)
- Comprehensive data validation and error handling
- Progress tracking with Rich UI components

Commands:
- generate-reports: Generate both RSU and FA reports for one financial year
- calculate-rsu: Calculate RSU capital gains and tax obligations
- calculate-fa: Calculate Foreign Assets declaration requirements
- validate-data: Validate input data files for completeness and accuracy
- help-guide: Display comprehensive help documentation

Example Usage:
    # Interactive mode (recommended for first-time users)
    uv run equitywise
    
    # Calculate RSU taxes for specific financial year
    uv run equitywise calculate-rsu --financial-year FY24-25 --output-format excel

    # Generate both annual RSU and FA reports with one command
    uv run equitywise generate-reports --financial-year FY24-25
    
    # Check Foreign Assets declaration requirement
    uv run equitywise calculate-fa --calendar-year 2024 --check-only

Author: EquityWise Development Team
License: MIT
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import click
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
import time

from equitywise.config.settings import settings
from equitywise.calculators.rsu_service import RSUService
from equitywise.calculators.fa_service import FAService
from equitywise.data.loaders import DataValidator
from equitywise.reports import ExcelReporter, CSVReporter
from equitywise.validation import CrossValidator, ValidationResult


console = Console()


def setup_logging(log_level: str, log_file: Optional[Path] = None) -> None:
    """Set up logging configuration."""
    logger.remove()  # Remove default handler
    
    # Console handler with colors
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True,
    )
    
    # File handler if specified
    if log_file:
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="1 week",
        )


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Set logging verbosity level for troubleshooting",
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Save logs to specified file path",
)
@click.version_option(version="1.1.0")
@click.pass_context
def cli(ctx: click.Context, log_level: str, log_file: Optional[str]) -> None:
    """🎯 EquityWise - Smart Equity Tax Calculations
    
    A comprehensive Python tool to process E*Trade data and calculate:
    • RSU, ESOP, ESPP tax obligations for Indian Financial Year filings
    • Foreign Assets declarations for Calendar Year compliance  
    • Complete bank reconciliation and professional reporting
    
    📁 REQUIRED DATA FILES:
        BenefitHistory.xlsx     - E*Trade RSU vesting history
        G&L statements         - E*Trade Gain & Loss reports
        Reference Rates.csv    - SBI TTBR exchange rates
        HistoricalData.csv     - Adobe stock price history
    
    🚀 QUICK START:
        equitywise interactive                    # Guided setup
        equitywise validate-data                  # Check file setup
        equitywise generate-reports --financial-year FY24-25
        equitywise calculate-rsu --financial-year FY24-25
        equitywise calculate-fa --calendar-year 2024
    
    💡 COMMON WORKFLOWS:
        # Complete tax preparation
        equitywise generate-reports --financial-year FY24-25 --output-format both
        
        # Single year analysis
        equitywise calculate-rsu --financial-year FY24-25 --detailed
        
        # Multi-year compliance check
        equitywise calculate-fa --detailed
    
    🔧 TROUBLESHOOTING:
        equitywise validate-data               # Check data files
        equitywise --log-level DEBUG [command] # Verbose logging
        equitywise interactive                 # Guided troubleshooting
    
    For detailed command help, use: equitywise COMMAND --help
    """
    # Ensure output directory exists
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_file_path = Path(log_file) if log_file else None
    setup_logging(log_level, log_file_path)
    
    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    ctx.obj["log_file"] = log_file_path
    
    logger.info("EquityWise started")


@cli.command()
@click.option(
    "--financial-year",
    type=str,
    help="Financial year for RSU calculations (e.g., 'FY24-25'). If not specified, calculates for all available years.",
    metavar="FY<YY>-<YY>",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed RSU calculations including individual transactions, vesting events, and bank reconciliation.",
)
@click.option(
    "--output-format",
    type=click.Choice(["excel", "csv", "both"], case_sensitive=False),
    default="excel",
    help="Output format for reports. 'excel' creates comprehensive XLSX files, 'csv' creates lightweight CSV files, 'both' creates both formats.",
    show_default=True,
)
@click.option(
    "--validate-first",
    is_flag=True,
    help="Validate data files before starting calculations to catch issues early.",
)
@click.option(
    "--validate",
    is_flag=True,
    help="Enable comprehensive cross-validation between data sources and calculation methods.",
)
def calculate_rsu(
    financial_year: Optional[str],
    detailed: bool,
    output_format: str,
    validate_first: bool,
    validate: bool,
) -> None:
    """Calculate RSU gain/loss for the specified financial year.
    
    This command processes E*Trade BenefitHistory.xlsx and G&L statements to calculate:
    - Vesting income (taxable as salary income)
    - Capital gains/losses from stock sales (short-term vs long-term)
    - Complete financial year summaries with currency conversion
    
    Examples:
        equitywise calculate-rsu --financial-year FY24-25
        equitywise calculate-rsu --detailed --output-format both
        equitywise calculate-rsu --validate-first
    """
    console.print(Panel.fit(
        Text("RSU Calculation", style="bold purple"),
        title="[bold green]EquityWise[/bold green]",
        border_style="purple"
    ))
    
    # Validate financial year format if provided
    if financial_year and not _validate_financial_year_format(financial_year):
        console.print(f"[red]❌ Invalid financial year format: {financial_year}[/red]")
        console.print("[yellow]Expected format: FY<YY>-<YY> (e.g., FY24-25, FY23-24)[/yellow]")
        return
    
    logger.info(f"Starting RSU calculation for FY: {financial_year or 'all available years'}")
    
    try:
        # Validate data files first if requested
        if validate_first:
            console.print("\n🔍 [bold purple]Pre-flight Data Validation...[/bold purple]")
            if not _validate_required_files():
                console.print("[red]❌ Data validation failed! Please fix file issues before proceeding.[/red]")
                return
            console.print("[green]✅ All required files are accessible[/green]")
        # Use progress indicators for long operations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            
            # Initialize RSU service
            init_task = progress.add_task("[cyan]Initializing RSU service...", total=100)
            progress.update(init_task, advance=30)
            rsu_service = RSUService(settings)
            progress.update(init_task, advance=70, description="[cyan]RSU service ready")
            
            # Validate data quality first
            validation_task = progress.add_task("[purple]Validating data quality...", total=100)
            validation_results = rsu_service.validate_data_quality()
            progress.update(validation_task, advance=100, description="[purple]Data validation complete")
            
            if not validation_results['success']:
                console.print("\n[red]❌ Data validation failed![/red]")
                for error in validation_results['errors']:
                    console.print(f"   [red]• {error}[/red]")
                return
            
            # Perform RSU calculations
            calc_task = progress.add_task("[green]Calculating RSU gains/losses...", total=100)
            results = rsu_service.calculate_rsu_for_fy(financial_year, detailed)
            progress.update(calc_task, advance=100, description="[green]RSU calculations complete")
        
        # Bank remittances are loaded by the service before summaries are
        # calculated so confirmed sale expenses reduce capital gains exactly once.
        bank_transactions = results.bank_transactions if detailed else {}
        
        # Display results
        console.print(f"\n✅ [bold green]RSU Calculation Complete for {results.financial_year}[/bold green]")
        
        # Display summary in table format
        _display_rsu_summary_table(results, console)
        
        # Show FY breakdown if multiple years
        if len(results.fy_summaries) > 1:
            console.print("\n📅 [bold cyan]Financial Year Breakdown:[/bold cyan]")
            for fy, summary in results.fy_summaries.items():
                console.print(f"   {fy}: [white]₹{summary.net_gain_loss_inr:,.2f}[/white] "
                            f"({summary.vesting_events_count} vestings, {summary.sale_events_count} sales)")

        # Show detailed transactions if requested
        if detailed and (results.vesting_events or results.sale_events):
            console.print("\n📋 [bold cyan]Detailed Transactions:[/bold cyan]")
            
            # Display improved vesting events table
            if results.vesting_events:
                _display_vesting_events_table(results.vesting_events, console)
            
            # Display improved sale events table
            if results.sale_events:
                _display_sale_events_table(results.sale_events, console)
                
            # Display sale date-wise proceedings table
            if results.sale_events:
                _display_sale_date_proceedings_table(results.sale_events, console, bank_transactions)
        
        # Generate reports if requested with progress indicators
        if output_format in ["excel", "both", "csv"]:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                
                if output_format in ["excel", "both"]:
                    try:
                        excel_task = progress.add_task("[blue]Generating Excel report...", total=100)
                        excel_reporter = ExcelReporter()
                        progress.update(excel_task, advance=20)
                        
                        # Get the summary for the requested financial year
                        summary = results.fy_summaries.get(financial_year) if financial_year and financial_year in results.fy_summaries else None
                        if not summary and results.fy_summaries:
                            # Use the first/only summary if no specific FY requested
                            summary = list(results.fy_summaries.values())[0]
                        progress.update(excel_task, advance=30)
                        
                        if summary:
                            excel_file = excel_reporter.generate_rsu_report(
                                summary=summary,
                                vesting_events=results.vesting_events,
                                sale_events=results.sale_events,
                                bank_transactions=list(bank_transactions.values()) if bank_transactions else None,
                                financial_year=financial_year,
                                detailed=detailed
                            )
                            progress.update(excel_task, advance=50, description="[blue]Excel report complete")
                            console.print(f"\n✅ Excel report saved: [cyan]{excel_file}[/cyan]")
                        else:
                            progress.update(excel_task, advance=50, description="[yellow]No Excel data available")
                            console.print("\n[yellow]⚠️ No summary data available for Excel report[/yellow]")
                    except Exception as e:
                        progress.update(excel_task, advance=50, description="[red]Excel report failed")
                        _handle_report_generation_error(e, "RSU", "Excel")
                        logger.error(f"Excel report generation error: {e}")
                
                if output_format in ["csv", "both"]:
                    try:
                        csv_task = progress.add_task("[blue]Generating CSV reports...", total=100)
                        csv_reporter = CSVReporter()
                        progress.update(csv_task, advance=20)
                        
                        # Get the summary for the requested financial year
                        summary = results.fy_summaries.get(financial_year) if financial_year and financial_year in results.fy_summaries else None
                        if not summary and results.fy_summaries:
                            # Use the first/only summary if no specific FY requested
                            summary = list(results.fy_summaries.values())[0]
                        progress.update(csv_task, advance=30)
                        
                        if summary:
                            csv_files = csv_reporter.generate_rsu_report(
                                summary=summary,
                                vesting_events=results.vesting_events,
                                sale_events=results.sale_events,
                                bank_transactions=list(bank_transactions.values()) if bank_transactions else None,
                                financial_year=financial_year,
                                detailed=detailed
                            )
                            progress.update(csv_task, advance=50, description="[blue]CSV reports complete")
                            for csv_file in csv_files:
                                console.print(f"\n✅ CSV report saved: [cyan]{csv_file}[/cyan]")
                        else:
                            progress.update(csv_task, advance=50, description="[yellow]No CSV data available")
                            console.print("\n[yellow]⚠️ No summary data available for CSV reports[/yellow]")
                    except Exception as e:
                        progress.update(csv_task, advance=50, description="[red]CSV reports failed")
                        _handle_report_generation_error(e, "RSU", "CSV")
                        logger.error(f"CSV report generation error: {e}")
        
        # Perform comprehensive validation if requested
        if validate:
            console.print("\n")  # Add spacing
            console.print(Panel.fit(
                Text("Cross-Validation in Progress", style="bold yellow"),
                title="[bold green]Validation[/bold green]",
                border_style="yellow"
            ))
            
            try:
                # Initialize validator
                validator = CrossValidator()
                
                # Get ALL events for validation (across all financial years)
                all_events_result = rsu_service.calculate_rsu_for_fy(
                    financial_year=None,  # Get all years
                    detailed=True         # Include event details
                )
                
                # Prepare RSU data for validation
                # Note: Pass ALL events from all years, validation will filter by FY
                rsu_data = {
                    "vesting_events": all_events_result.vesting_events,  # All events from all years
                    "sale_events": all_events_result.sale_events,        # All events from all years  
                    "summary": results                                    # FY-specific summary
                }
                
                # Get raw data for cross-validation
                from equitywise.data.loaders import BenefitHistoryLoader, GLStatementLoader
                
                # Load BenefitHistory data
                benefit_history_records = []
                if settings.benefit_history_path.exists():
                    benefit_loader = BenefitHistoryLoader(settings.benefit_history_path)
                    benefit_history_records = benefit_loader.get_validated_records()
                
                # Load G&L statement data  
                gl_records = []
                for gl_path in settings.get_gl_statement_files(use_auto_discovery=True):
                    if gl_path.exists():
                        gl_loader = GLStatementLoader(gl_path)
                        gl_file_records = gl_loader.get_validated_records()
                        gl_records.extend(gl_file_records)
                
                # Determine overlap year based on financial_year
                overlap_year = None
                if financial_year:
                    # Extract year from FY format (e.g., FY24-25 -> 2024)
                    try:
                        if financial_year.startswith("FY") and "-" in financial_year:
                            year_part = financial_year[2:4]  # Get "24" from "FY24-25"
                            overlap_year = f"20{year_part}"  # Convert to "2024"
                    except:
                        pass
                
                # Perform validation
                validation_result = validator.validate_comprehensive(
                    rsu_data=rsu_data,
                    benefit_history_records=benefit_history_records,
                    gl_records=gl_records,
                    overlap_year=overlap_year,
                    financial_year=financial_year
                )
                
                # Display validation results
                if validation_result.is_valid:
                    console.print("\n[green]✅ Comprehensive validation PASSED![/green]")
                    console.print(f"[dim]• {validation_result.get_warning_count()} warnings[/dim]")
                else:
                    console.print("\n[red]❌ Comprehensive validation FAILED![/red]")
                    console.print(f"[red]• {validation_result.get_error_count()} errors[/red]")
                    console.print(f"[yellow]• {validation_result.get_warning_count()} warnings[/yellow]")
                
                # Show detailed validation report if there are issues
                if not validation_result.is_valid or validation_result.get_warning_count() > 0:
                    console.print("\n[bold yellow]📋 Validation Report:[/bold yellow]")
                    validation_report = validator.generate_validation_report(validation_result)
                    console.print(validation_report)
                    
                    # Save validation report to file
                    from pathlib import Path
                    output_dir = Path("output")
                    output_dir.mkdir(exist_ok=True)
                    validation_file = output_dir / f"validation_report_RSU_{financial_year or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    validation_file.write_text(validation_report)
                    console.print(f"\n[cyan]📄 Validation report saved: {validation_file}[/cyan]")
                    
            except Exception as e:
                console.print(f"\n[red]❌ Validation failed: {e}[/red]")
                logger.error(f"Cross-validation error: {e}")
        
        # Ensure all Rich output is complete before logging
        console.print("")  # Force flush Rich output
        logger.info(f"RSU calculation completed successfully: ₹{results.net_position_inr:,.2f} net position")
        
    except Exception as e:
        _handle_calculation_error(e, "RSU", f"Financial Year: {financial_year or 'all years'}")
        logger.error(f"RSU calculation error: {e}")
        if detailed:
            import traceback
            console.print(f"\n[dim]🔍 Detailed stack trace:[/dim]")
            console.print(f"[red]{traceback.format_exc()}[/red]")


@cli.command()
@click.option(
    "--calendar-year",
    type=click.IntRange(min=2018, max=2030),
    help="Calendar year for Foreign Assets calculations (2018-2030). If not specified, calculates for all available years.",
    metavar="YYYY",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed FA calculations including vest-wise breakdowns, balance summaries, and compliance analysis.",
)
@click.option(
    "--output-format",
    type=click.Choice(["excel", "csv", "both"], case_sensitive=False),
    default="excel",
    help="Output format for reports. 'excel' creates comprehensive XLSX files, 'csv' creates lightweight CSV files, 'both' creates both formats.",
    show_default=True,
)
@click.option(
    "--validate-first",
    is_flag=True,
    help="Validate data files before starting calculations to catch issues early.",
)
@click.option(
    "--export-fa-csv",
    is_flag=True,
    help="Generate FA declaration CSV file ready for import into tax filing software using template format.",
)
@click.option(
    "--validate",
    is_flag=True,
    help="Enable comprehensive cross-validation between data sources and calculation methods.",
)
def calculate_fa(
    calendar_year: Optional[int],
    detailed: bool,
    output_format: str,
    validate_first: bool,
    export_fa_csv: bool,
    validate: bool,
) -> None:
    """Calculate Foreign Assets declaration data for the specified calendar year.
    
    This command processes RSU holding data to determine:
    - Peak balance calculations for FA declaration requirements (₹2 lakh threshold)
    - Year-end equity valuations using market prices and exchange rates
    - Complete compliance analysis for Indian tax requirements
    - FA declaration CSV export ready for tax software import
    
    Examples:
        equitywise calculate-fa --calendar-year 2024
        equitywise calculate-fa --detailed --output-format both
        equitywise calculate-fa --calendar-year 2024 --export-fa-csv
        equitywise calculate-fa --validate-first --export-fa-csv
    """
    console.print(Panel.fit(
        Text("Foreign Assets Calculation", style="bold purple"),
        title="[bold green]EquityWise[/bold green]",
        border_style="purple"
    ))
    
    if calendar_year:
        logger.info(f"Starting FA calculation for CY: {calendar_year}")
    else:
        logger.info("Starting FA calculation for all available years")
    
    try:
        # Validate data files first if requested
        if validate_first:
            console.print("\n🔍 [bold purple]Pre-flight Data Validation...[/bold purple]")
            if not _validate_required_files():
                console.print("[red]❌ Data validation failed! Please fix file issues before proceeding.[/red]")
                return
            console.print("[green]✅ All required files are accessible[/green]")
        
        # Use progress indicators for long operations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            
            # Initialize FA service
            init_task = progress.add_task("[cyan]Initializing FA service...", total=100)
            progress.update(init_task, advance=30)
            fa_service = FAService(settings)
            progress.update(init_task, advance=70, description="[cyan]FA service ready")
            
            # Validate data quality first
            validation_task = progress.add_task("[purple]Validating FA data quality...", total=100)
            validation_results = fa_service.validate_fa_data_quality()
            progress.update(validation_task, advance=100, description="[purple]FA data validation complete")
            
            if not validation_results['success']:
                console.print("\n[red]❌ Data validation failed![/red]")
                for error in validation_results['errors']:
                    console.print(f"   [red]• {error}[/red]")
                return
        
        if calendar_year:
            # Single year calculation with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                calc_task = progress.add_task(f"[green]Calculating FA for {calendar_year}...", total=100)
                results = fa_service.calculate_fa_for_year(str(calendar_year), detailed=detailed)
                progress.update(calc_task, advance=100, description=f"[green]FA calculation for {calendar_year} complete")
            
            _display_single_year_results(results, detailed, console)
            
            # Perform comprehensive validation if requested
            if validate:
                console.print("\n")  # Add spacing
                console.print(Panel.fit(
                    Text("Cross-Validation in Progress", style="bold yellow"),
                    title="[bold green]Validation[/bold green]",
                    border_style="yellow"
                ))
                
                try:
                    # Initialize validator
                    validator = CrossValidator()
                    
                    # Prepare FA data for validation
                    summary = list(results.year_summaries.values())[0] if results.year_summaries else None
                    fa_data = {
                        "summary": summary,
                        "equity_holdings": results.equity_holdings,
                        "vest_wise_details": summary.vest_wise_details if summary else []
                    }
                    
                    # Get raw data for cross-validation
                    from equitywise.data.loaders import BenefitHistoryLoader
                    
                    # Load BenefitHistory data
                    benefit_history_records = []
                    if settings.benefit_history_path.exists():
                        benefit_loader = BenefitHistoryLoader(settings.benefit_history_path)
                        benefit_history_records = benefit_loader.get_validated_records()
                    
                    # Use calendar_year for overlap validation
                    overlap_year = str(calendar_year) if calendar_year else None
                    
                    # Perform validation
                    validation_result = validator.validate_comprehensive(
                        fa_data=fa_data,
                        benefit_history_records=benefit_history_records,
                        overlap_year=overlap_year
                    )
                    
                    # Display validation results
                    if validation_result.is_valid:
                        console.print("\n[green]✅ Comprehensive validation PASSED![/green]")
                        console.print(f"[dim]• {validation_result.get_warning_count()} warnings[/dim]")
                    else:
                        console.print("\n[red]❌ Comprehensive validation FAILED![/red]")
                        console.print(f"[red]• {validation_result.get_error_count()} errors[/red]")
                        console.print(f"[yellow]• {validation_result.get_warning_count()} warnings[/yellow]")
                    
                    # Show detailed validation report if there are issues
                    if not validation_result.is_valid or validation_result.get_warning_count() > 0:
                        console.print("\n[bold yellow]📋 Validation Report:[/bold yellow]")
                        validation_report = validator.generate_validation_report(validation_result)
                        console.print(validation_report)
                        
                        # Save validation report to file
                        from pathlib import Path
                        output_dir = Path("output")
                        output_dir.mkdir(exist_ok=True)
                        validation_file = output_dir / f"validation_report_FA_{calendar_year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        validation_file.write_text(validation_report)
                        console.print(f"\n[cyan]📄 Validation report saved: {validation_file}[/cyan]")
                        
                except Exception as e:
                    console.print(f"\n[red]❌ Validation failed: {e}[/red]")
                    logger.error(f"Cross-validation error: {e}")
            
            # Generate reports for single year
            if output_format in ["excel", "both"]:
                try:
                    console.print("\n📄 [bold blue]Generating Excel Report...[/bold blue]")
                    excel_reporter = ExcelReporter()
                    summary = list(results.year_summaries.values())[0] if results.year_summaries else None
                    if summary:
                        excel_file = excel_reporter.generate_fa_report(
                            summary=summary,
                            equity_holdings=results.equity_holdings,
                            vest_wise_details=summary.vest_wise_details,
                            calendar_year=str(calendar_year),
                            detailed=detailed
                        )
                        console.print(f"   ✅ Excel report saved: [cyan]{excel_file}[/cyan]")
                except Exception as e:
                    _handle_report_generation_error(e, "FA", "Excel")
                    logger.error(f"Excel report generation error: {e}")
            
            if output_format in ["csv", "both"]:
                try:
                    console.print("\n📄 [bold blue]Generating CSV Reports...[/bold blue]")
                    csv_reporter = CSVReporter()
                    summary = list(results.year_summaries.values())[0] if results.year_summaries else None
                    if summary:
                        csv_files = csv_reporter.generate_fa_report(
                            summary=summary,
                            equity_holdings=results.equity_holdings,
                            vest_wise_details=getattr(results, 'vest_wise_details', []),
                            calendar_year=str(calendar_year),
                            detailed=detailed
                        )
                        for csv_file in csv_files:
                            console.print(f"   ✅ CSV report saved: [cyan]{csv_file}[/cyan]")
                except Exception as e:
                    _handle_report_generation_error(e, "FA", "CSV")
                    logger.error(f"CSV report generation error: {e}")
                    
            # Generate FA declaration CSV if requested
            if export_fa_csv:
                try:
                    console.print("\n📋 [bold green]Generating FA Declaration CSV for Tax Forms...[/bold green]")
                    csv_reporter = CSVReporter()
                    summary = list(results.year_summaries.values())[0] if results.year_summaries else None
                    if summary:
                        fa_csv_file = csv_reporter.generate_fa_declaration_csv(
                            summary=summary,
                            calendar_year=str(calendar_year),
                            template_path=settings.fa_declaration_template_path
                        )
                        console.print(f"   ✅ FA Declaration CSV saved: [cyan]{fa_csv_file}[/cyan]")
                        console.print(f"   📊 [dim]{len(summary.vest_wise_details)} vest-wise entries ready for tax software import[/dim]")
                        console.print(f"   💰 [dim]Total closing value: ₹{summary.closing_balance_inr:,.2f}[/dim]")
                except Exception as e:
                    _handle_report_generation_error(e, "FA Declaration", "CSV")
                    logger.error(f"FA Declaration CSV generation error: {e}")
        else:
            # Multi-year calculation with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                calc_task = progress.add_task("[green]Calculating FA for all years...", total=100)
                results = fa_service.calculate_fa_multi_year(detailed=detailed)
                progress.update(calc_task, advance=100, description="[green]Multi-year FA calculation complete")
            
            _display_multi_year_summary_table(results, console, detailed)
            
            # Perform comprehensive validation if requested (multi-year)
            if validate:
                console.print("\n")  # Add spacing
                console.print(Panel.fit(
                    Text("Cross-Validation in Progress (Multi-Year)", style="bold yellow"),
                    title="[bold green]Validation[/bold green]",
                    border_style="yellow"
                ))
                
                try:
                    # Initialize validator
                    validator = CrossValidator()
                    
                    # Prepare multi-year FA data for validation (use most recent year for overlap)
                    latest_year = max(results.year_summaries.keys()) if results.year_summaries else None
                    latest_summary = results.year_summaries.get(latest_year) if latest_year else None
                    
                    fa_data = {
                        "summary": latest_summary,
                        "equity_holdings": results.equity_holdings,
                        "vest_wise_details": latest_summary.vest_wise_details if latest_summary else []
                    }
                    
                    # Get raw data for cross-validation  
                    from equitywise.data.loaders import BenefitHistoryLoader
                    
                    # Load BenefitHistory data
                    benefit_history_records = []
                    if settings.benefit_history_path.exists():
                        benefit_loader = BenefitHistoryLoader(settings.benefit_history_path)
                        benefit_history_records = benefit_loader.get_validated_records()
                    
                    # Use latest year for overlap validation
                    overlap_year = latest_year if latest_year else None
                    
                    # Perform validation
                    validation_result = validator.validate_comprehensive(
                        fa_data=fa_data,
                        benefit_history_records=benefit_history_records,
                        overlap_year=overlap_year
                    )
                    
                    # Display validation results
                    if validation_result.is_valid:
                        console.print("\n[green]✅ Comprehensive validation PASSED![/green]")
                        console.print(f"[dim]• {validation_result.get_warning_count()} warnings[/dim]")
                    else:
                        console.print("\n[red]❌ Comprehensive validation FAILED![/red]")
                        console.print(f"[red]• {validation_result.get_error_count()} errors[/red]")
                        console.print(f"[yellow]• {validation_result.get_warning_count()} warnings[/yellow]")
                    
                    # Show detailed validation report if there are issues
                    if not validation_result.is_valid or validation_result.get_warning_count() > 0:
                        console.print("\n[bold yellow]📋 Validation Report:[/bold yellow]")
                        validation_report = validator.generate_validation_report(validation_result)
                        console.print(validation_report)
                        
                        # Save validation report to file
                        from pathlib import Path
                        output_dir = Path("output")
                        output_dir.mkdir(exist_ok=True)
                        validation_file = output_dir / f"validation_report_FA_multi_year_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        validation_file.write_text(validation_report)
                        console.print(f"\n[cyan]📄 Validation report saved: {validation_file}[/cyan]")
                        
                except Exception as e:
                    console.print(f"\n[red]❌ Validation failed: {e}[/red]")
                    logger.error(f"Cross-validation error: {e}")
            
            # Generate reports for all years
            if output_format in ["excel", "both"]:
                try:
                    console.print("\n📄 [bold blue]Generating Excel Reports (Multi-Year)...[/bold blue]")
                    excel_reporter = ExcelReporter()
                    for year, summary in results.year_summaries.items():
                        excel_file = excel_reporter.generate_fa_report(
                            summary=summary,
                            equity_holdings=results.equity_holdings,
                            vest_wise_details=summary.vest_wise_details,
                            calendar_year=year,
                            detailed=detailed
                        )
                        console.print(f"   ✅ Excel report for {year}: [cyan]{excel_file}[/cyan]")
                except Exception as e:
                    console.print(f"   [red]❌ Excel reports failed: {e}[/red]")
                    logger.error(f"Excel report generation error: {e}")
            
            if output_format in ["csv", "both"]:
                try:
                    console.print("\n📄 [bold blue]Generating CSV Reports (Multi-Year)...[/bold blue]")
                    csv_reporter = CSVReporter()
                    for year, summary in results.year_summaries.items():
                        csv_files = csv_reporter.generate_fa_report(
                            summary=summary,
                            equity_holdings=results.equity_holdings,
                            vest_wise_details=summary.vest_wise_details,
                            calendar_year=year,
                            detailed=detailed
                        )
                        for csv_file in csv_files:
                            console.print(f"   ✅ CSV report for {year}: [cyan]{csv_file}[/cyan]")
                except Exception as e:
                    console.print(f"   [red]❌ CSV reports failed: {e}[/red]")
                    logger.error(f"CSV report generation error: {e}")

        
    except Exception as e:
        _handle_calculation_error(e, "Foreign Assets", f"Calendar Year: {calendar_year or 'all years'}")
        logger.error(f"FA calculation error: {e}")
        if detailed:
            import traceback
            console.print(f"\n[dim]🔍 Detailed stack trace:[/dim]")
            console.print(f"[red]{traceback.format_exc()}[/red]")


@cli.command("generate-reports")
@click.option(
    "--financial-year",
    required=True,
    type=str,
    help=(
        "Indian financial year for both reports (e.g., FY25-26). "
        "The FA report uses the calendar year ending within that FY."
    ),
    metavar="FY<YY>-<YY>",
)
@click.option(
    "--detailed/--summary-only",
    default=True,
    show_default=True,
    help="Generate detailed transaction sheets or summary sheets only.",
)
@click.option(
    "--output-format",
    type=click.Choice(["excel", "csv", "both"], case_sensitive=False),
    default="excel",
    show_default=True,
    help="Output format for both RSU and FA reports.",
)
@click.option(
    "--validate-first",
    is_flag=True,
    help="Validate required input files before each calculation.",
)
@click.option(
    "--validate",
    is_flag=True,
    help="Run comprehensive cross-validation for both calculations.",
)
@click.option(
    "--export-fa-csv",
    is_flag=True,
    help="Also generate the tax-software-ready FA declaration CSV.",
)
@click.pass_context
def generate_reports(
    ctx: click.Context,
    financial_year: str,
    detailed: bool,
    output_format: str,
    validate_first: bool,
    validate: bool,
    export_fa_csv: bool,
) -> None:
    """Generate RSU and Foreign Assets reports for one financial year.

    Example:
        equitywise generate-reports --financial-year FY25-26
    """
    financial_year = financial_year.upper()
    try:
        fa_calendar_year = _financial_year_to_fa_calendar_year(financial_year)
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="--financial-year") from exc

    console.print(Panel.fit(
        Text("Annual RSU + FA Reports", style="bold purple"),
        title="[bold green]EquityWise[/bold green]",
        border_style="purple",
    ))
    console.print(
        f"[cyan]{financial_year}[/cyan] → RSU financial year "
        f"and FA calendar year [cyan]{fa_calendar_year}[/cyan]"
    )

    console.print("\n[bold green]1/2 Generating RSU report...[/bold green]")
    ctx.invoke(
        calculate_rsu,
        financial_year=financial_year,
        detailed=detailed,
        output_format=output_format,
        validate_first=validate_first,
        validate=validate,
    )

    console.print("\n[bold green]2/2 Generating Foreign Assets report...[/bold green]")
    ctx.invoke(
        calculate_fa,
        calendar_year=fa_calendar_year,
        detailed=detailed,
        output_format=output_format,
        validate_first=validate_first,
        export_fa_csv=export_fa_csv,
        validate=validate,
    )

    console.print(
        "\n[bold green]Finished running the annual RSU and FA report commands.[/bold green]"
    )


def _display_single_year_results(results, detailed: bool, console) -> None:
    """Display results for a single calendar year."""
    from rich.table import Table
    
    console.print(f"\n✅ [bold green]FA Calculation Complete for {results.calendar_year}[/bold green]")
    
    # Display company and depository account details for FA filing
    _display_company_and_account_details(console)
    
    if results.year_summaries:
        summary = list(results.year_summaries.values())[0]
        
        console.print("\n📈 [bold cyan]Foreign Assets Summary:[/bold cyan]")
        console.print(f"   Currently Held Shares: [green]{summary.total_vested_shares:,.0f}[/green]")
        console.print(f"   Total Vested (Ever): [cyan]{summary.total_vested_ever:,.0f}[/cyan]")
        console.print(f"   Sold in CL{results.calendar_year}: [red]{summary.total_sold_in_cl:,.0f}[/red]")
        console.print(f"   Total Sold (Ever): [dim red]{summary.total_sold_ever:,.0f}[/dim red]")
        
        # Create single-year comprehensive balance summary table with dynamic sizing
        balance_table = Table(
            title=f"📊 Foreign Assets Balance Summary - CL{results.calendar_year}", 
            show_header=True, 
            header_style="bold magenta",
            expand=True,
            show_lines=False  # Keep structure but reduce clutter
        )
        balance_table.add_column("Balance Type", style="cyan", min_width=10, max_width=18, no_wrap=False)
        balance_table.add_column("Amount (₹)", style="white", justify="right", min_width=12, max_width=25, no_wrap=False)
        balance_table.add_column("Shares", style="purple", justify="right", min_width=6, max_width=12)
        balance_table.add_column("Stock Price", style="magenta", justify="right", min_width=9, max_width=18, no_wrap=False)
        balance_table.add_column("Forex Rate", style="yellow", justify="right", min_width=9, max_width=18, no_wrap=False)
        balance_table.add_column("Date", style="white", min_width=15, max_width=20, no_wrap=False)  # Better date display
        balance_table.add_column("Declaration", style="white", min_width=10, max_width=20, no_wrap=False)
        
        # Opening Balance (from initial vesting date, not Jan 1st)
        opening_date = "Initial" if summary.opening_balance_inr > 0 else "-"
        opening_shares = f"{summary.opening_shares:.1f}" if summary.opening_shares > 0 else "0.0"
        opening_stock_price = f"${summary.opening_stock_price:.2f}" if summary.opening_stock_price > 0 else "-"
        opening_forex_rate = f"₹{summary.opening_exchange_rate:.4f}" if summary.opening_exchange_rate > 0 else "-"
        
        balance_table.add_row(
            "[purple]Opening[/purple]",
            f"₹{summary.opening_balance_inr:,.2f}" if summary.opening_balance_inr > 0 else "₹0.00",
            opening_shares,
            opening_stock_price,
            opening_forex_rate,
            opening_date,
            "-"
        )
        
        # Peak Balance  
        peak_date = summary.peak_balance_date.strftime("%b %d") if summary.peak_balance_date else "-"
        declaration = "[red]Required[/red]" if summary.declaration_required else "[green]Not Req'd[/green]"
        peak_shares = f"{summary.peak_shares:.1f}" if summary.peak_shares > 0 else "0.0"
        peak_stock_price = f"${summary.peak_stock_price:.2f}" if summary.peak_stock_price > 0 else "-"
        peak_forex_rate = f"₹{summary.peak_exchange_rate:.4f}" if summary.peak_exchange_rate > 0 else "-"
        
        balance_table.add_row(
            "[red]Peak[/red]",
            f"₹{summary.peak_balance_inr:,.2f}" if summary.peak_balance_inr > 0 else "₹0.00",
            peak_shares,
            peak_stock_price,
            peak_forex_rate,
            peak_date,
            declaration
        )
        
        # Closing Balance
        closing_date = "Dec 31" if summary.closing_balance_inr > 0 else "-"
        closing_shares = f"{summary.closing_shares:.1f}" if summary.closing_shares > 0 else "0.0"
        closing_stock_price = f"${summary.year_end_stock_price:.2f}" if summary.year_end_stock_price > 0 else "-"
        closing_forex_rate = f"₹{summary.year_end_exchange_rate:.4f}" if summary.year_end_exchange_rate > 0 else "-"
        
        balance_table.add_row(
            "[green]Closing[/green]",
            f"₹{summary.closing_balance_inr:,.2f}" if summary.closing_balance_inr > 0 else "₹0.00",
            closing_shares,
            closing_stock_price,
            closing_forex_rate,
            closing_date,
            "-"
        )
        
        console.print(balance_table)
        
        # Display vest-wise details table
        if summary.vest_wise_details:
            _display_vest_wise_details_table(summary, results.calendar_year, console, detailed)
        
        # Declaration requirement
        if summary.declaration_required:
            console.print(f"\n🚨 [bold red]FA Declaration Required![/bold red]")
            console.print(f"   Peak balance (₹{summary.peak_balance_inr:,.2f}) exceeds ₹{summary.fa_declaration_threshold_inr:,.2f} threshold")
        else:
            console.print(f"\n✅ [bold green]No FA Declaration Required[/bold green]")
            console.print(f"   Peak balance (₹{summary.peak_balance_inr:,.2f}) below ₹{summary.fa_declaration_threshold_inr:,.2f} threshold")
        
        # Check for incomplete data warnings
        from datetime import date
        current_year = date.today().year
        
        if int(results.calendar_year) >= current_year:
            console.print(f"\n⚠️  [bold yellow]Data Completeness Notice:[/bold yellow]")
            if int(results.calendar_year) > current_year:
                console.print(f"   [yellow]• CL{results.calendar_year}: Using projected data (future year)[/yellow]")
            else:
                console.print(f"   [yellow]• CL{results.calendar_year}: Using partial data with fallbacks for remaining months[/yellow]")
            console.print(f"   [dim]Future calculations use latest available exchange rates and stock prices as fallbacks.[/dim]")
    
    # Show detailed holdings if requested (only vested shares for FA)
    if detailed and results.equity_holdings:
        vested_holdings = [h for h in results.equity_holdings if h.holding_type == "Vested"]
        
        if vested_holdings:
            console.print("\n📋 [bold cyan]Current Vested Holdings (FA Declaration Relevant):[/bold cyan]")
            for holding in vested_holdings[:10]:  # Show first 10
                console.print(f"   {holding.grant_number}: {holding.quantity:,.0f} shares @ "
                            f"₹{holding.market_value_inr_total/holding.quantity:,.2f}/share = ₹{holding.market_value_inr_total:,.2f}")
                
            if len(vested_holdings) > 10:
                console.print(f"   ... and {len(vested_holdings) - 10} more vested holdings")
    
    if results.year_summaries:
        summary = list(results.year_summaries.values())[0]
        logger.info(f"FA calculation completed successfully: ₹{summary.vested_holdings_inr:,.2f} total vested value")


def _display_rsu_summary_table(results, console) -> None:
    """Display RSU calculation summary in a structured table format."""
    from rich.table import Table
    
    # Create vesting details table
    vesting_table = Table(
        title="🔸 RSU Vesting Details",
        show_header=True, 
        header_style="bold green"
    )
    
    # Fixed columns with proper truncation for terminal readability
    vesting_table.add_column("Metric", style="cyan", width=20)
    vesting_table.add_column("Value", style="white", justify="right", width=18)
    vesting_table.add_column("Description", style="dim", width=65, overflow="ellipsis")
    
    # Add vesting summary rows
    vesting_table.add_row(
        "Total Vested Shares",
        f"{results.total_vested_quantity:,.0f}",
        "RSU shares vested in financial year"
    )
    vesting_table.add_row(
        "Vesting Income",
        f"₹{results.total_taxable_gain_inr:,.2f}",
        "Income from vesting (treated as salary income)"
    )
    
    console.print("\n")
    console.print(vesting_table)
    
    # Create sold details table
    sold_table = Table(
        title="💰 RSU Sale Details",
        show_header=True, 
        header_style="bold yellow"
    )
    
    # Fixed columns with proper truncation for terminal readability
    sold_table.add_column("Metric", style="cyan", width=20)
    sold_table.add_column("Value", style="white", justify="right", width=18)
    sold_table.add_column("Description", style="dim", width=65, overflow="ellipsis")
    
    # Add sale summary rows
    sold_table.add_row(
        "Total Sold Shares", 
        f"{results.total_sold_quantity:,.0f}",
        "RSU shares sold in financial year"
    )
    
    # Total purchase amount (cost basis of sold shares)
    sold_table.add_row(
        "Total Purchase Amount",
        f"₹{results.total_cost_basis_inr:,.2f}",
        "Cost basis of all shares sold in financial year"
    )
    
    # Total sold amount (sale proceeds)
    sold_table.add_row(
        "Total Sold Amount",
        f"₹{results.total_sale_proceeds_inr:,.2f}",
        "Gross sale proceeds from all shares sold in financial year"
    )

    sold_table.add_row(
        "Deductible Sale Expense",
        f"${results.total_sale_expenses_usd:,.2f} / ₹{results.total_sale_expenses_inr:,.2f}",
        "Selling expense omitted from broker G&L and deducted under Section 48"
    )
    
    # Short-term capital gains
    short_term_color = "red" if results.short_term_gains_inr < 0 else "green"
    short_term_text = f"[{short_term_color}]₹{results.short_term_gains_inr:,.2f}[/{short_term_color}]"
    
    sold_table.add_row(
        "Capital Gain (Short-term)",
        short_term_text,
        "Short-term capital gain/loss after deductible sale expenses"
    )
    
    # Long-term capital gains  
    long_term_color = "red" if results.long_term_gains_inr < 0 else "green"
    long_term_text = f"[{long_term_color}]₹{results.long_term_gains_inr:,.2f}[/{long_term_color}]"
    
    sold_table.add_row(
        "Capital Gain (Long-term)",
        long_term_text,
        "Long-term capital gain/loss after deductible sale expenses"
    )
    
    console.print("\n")
    console.print(sold_table)


def _display_vesting_events_table(vesting_events, console) -> None:
    """Display vesting events in an improved table format."""
    from rich.table import Table
    
    console.print("\n🔸 [bold yellow]Vesting Events[/bold yellow]")
    
    # Create vesting table with dynamic column sizing and proper structure
    vesting_table = Table(
        show_header=True, 
        header_style="bold green",
        expand=True,
        show_lines=False  # Keep table structure but reduce visual clutter
    )
    
    # Dynamic columns with improved constraints and text wrapping
    vesting_table.add_column("Vest Date", style="cyan", min_width=15, max_width=20, no_wrap=False)  # More space for dates
    vesting_table.add_column("Grant", style="yellow", min_width=8, max_width=15, no_wrap=False)
    vesting_table.add_column("Shares", style="white", justify="right", min_width=6, max_width=12)
    vesting_table.add_column("FMV/Share", style="green", justify="right", min_width=10, max_width=20, no_wrap=False)
    vesting_table.add_column("USD Value", style="green", justify="right", min_width=10, max_width=20, no_wrap=False)
    vesting_table.add_column("Exchange Rate", style="purple", justify="right", min_width=10, max_width=18, no_wrap=False)
    vesting_table.add_column("INR Value", style="green", justify="right", min_width=12, max_width=25, no_wrap=False)
    vesting_table.add_column("Vesting Value", style="magenta", justify="right", min_width=12, max_width=25, no_wrap=False)
    vesting_table.add_column("FY", style="cyan", min_width=6, max_width=12)
    
    total_shares = 0
    total_value_usd = 0
    total_value_inr = 0
    total_vesting_inr = 0
    
    for vesting in vesting_events:
        vest_value_usd = vesting.taxable_gain_usd
        vest_value_inr = vesting.taxable_gain_inr
        total_shares += vesting.vested_quantity
        total_value_usd += vest_value_usd
        total_value_inr += vest_value_inr
        total_vesting_inr += vesting.taxable_gain_inr
        
        vesting_table.add_row(
            vesting.vest_date.strftime("%Y-%m-%d"),
            vesting.grant_number[-8:],  # Show last 8 chars
            f"{vesting.vested_quantity:.0f}",
            f"${vesting.vest_fmv_usd:.2f}",
            f"${vest_value_usd:,.2f}",
            f"₹{vesting.exchange_rate:.4f}",
            f"₹{vest_value_inr:,.0f}",
            f"₹{vesting.taxable_gain_inr:,.0f}",
            vesting.financial_year
        )
    
    # Add totals row
    vesting_table.add_row(
        "[bold]TOTAL[/bold]",
        "[bold]-[/bold]",
        f"[bold]{total_shares:.0f}[/bold]",
        "[bold]-[/bold]",
        f"[bold]${total_value_usd:,.2f}[/bold]",
        "[bold]-[/bold]",
        f"[bold]₹{total_value_inr:,.0f}[/bold]",
        f"[bold]₹{total_vesting_inr:,.0f}[/bold]",
        "[bold]-[/bold]"
    )
    
    console.print(vesting_table)
    
    if len(vesting_events) > 20:
        console.print(f"\n   [dim]... showing all {len(vesting_events)} vesting events[/dim]")


def _display_sale_events_table(sale_events, console) -> None:
    """Display sale events in an improved table format."""
    from rich.table import Table
    
    console.print(f"\n🔹 [bold cyan]Sale Events[/bold cyan]")
    
    # Create sales table with dynamic column sizing and proper structure
    sales_table = Table(
        show_header=True, 
        header_style="bold magenta",
        expand=True,
        show_lines=False  # Keep table structure but reduce visual clutter
    )
    
    # Dynamic columns with enhanced constraints and text wrapping
    sales_table.add_column("Vest Date", style="cyan", min_width=15, max_width=20, no_wrap=False)  # Better date display
    sales_table.add_column("Sale Date", style="cyan", min_width=15, max_width=20, no_wrap=False)  # Better date display
    sales_table.add_column("Grant", style="yellow", min_width=6, max_width=15, no_wrap=False)
    sales_table.add_column("Shares", style="white", justify="right", min_width=6, max_width=12)
    sales_table.add_column("Hold Period", style="dim", justify="center", min_width=8, max_width=15, no_wrap=False)
    sales_table.add_column("Cost Basis", style="yellow", justify="right", min_width=10, max_width=20, no_wrap=False)
    sales_table.add_column("Sale Price", style="green", justify="right", min_width=10, max_width=20, no_wrap=False)
    sales_table.add_column("Rule 115 Rate", style="magenta", justify="right", min_width=10, max_width=20, no_wrap=False)
    sales_table.add_column("USD Proceeds", style="green", justify="right", min_width=11, max_width=22, no_wrap=False)
    sales_table.add_column("INR Proceeds", style="green", justify="right", min_width=12, max_width=25, no_wrap=False)
    sales_table.add_column("Sale Exp (USD)", style="red", justify="right", min_width=10, max_width=18, no_wrap=False)
    sales_table.add_column("Capital Gain (USD)", justify="right", min_width=13, max_width=25, no_wrap=False)  # Wrap instead of ellipsis
    sales_table.add_column("Capital Gain (INR)", justify="right", min_width=13, max_width=25, no_wrap=False)  # Wrap instead of ellipsis
    sales_table.add_column("Type", style="magenta", justify="center", min_width=4, max_width=10)
    sales_table.add_column("FY", style="cyan", min_width=6, max_width=12)
    
    total_shares_sold = 0
    total_cost_basis = 0
    total_usd_proceeds = 0
    total_inr_proceeds = 0
    total_sale_expenses_usd = 0
    total_capital_gains_usd = 0
    total_capital_gains_inr = 0
    
    for sale in sale_events:
        holding_days = (sale.sale_date - sale.acquisition_date).days
        gain_color = "red" if sale.capital_gain_inr < 0 else "green"
        cost_basis = sale.cost_basis_inr
        usd_proceeds = sale.sale_proceeds_usd
        capital_gain_usd = sale.capital_gain_usd
        
        total_shares_sold += sale.quantity_sold
        total_cost_basis += cost_basis
        total_usd_proceeds += usd_proceeds
        total_inr_proceeds += sale.sale_proceeds_inr
        total_sale_expenses_usd += sale.sale_expense_usd
        total_capital_gains_usd += capital_gain_usd
        total_capital_gains_inr += sale.capital_gain_inr
        
        sales_table.add_row(
            sale.acquisition_date.strftime("%Y-%m-%d"),
            sale.sale_date.strftime("%Y-%m-%d"),
            sale.grant_number[-8:],  # Show last 8 chars
            f"{sale.quantity_sold:.0f}",
            f"{holding_days}d",
            f"₹{cost_basis:,.0f}",
            f"${sale.sale_price_usd:.2f}",
            f"₹{(sale.capital_gains_exchange_rate or sale.exchange_rate_sale):.4f}",
            f"${usd_proceeds:.2f}",
            f"₹{sale.sale_proceeds_inr:,.0f}",
            f"${sale.sale_expense_usd:,.2f}",
            f"[{gain_color}]${capital_gain_usd:,.2f}[/{gain_color}]",
            f"[{gain_color}]₹{sale.capital_gain_inr:,.0f}[/{gain_color}]",
            sale.gain_type[:1],  # S for Short, L for Long
            sale.financial_year
        )
    
    # Add totals row
    total_gain_color_usd = "red" if total_capital_gains_usd < 0 else "green"
    total_gain_color_inr = "red" if total_capital_gains_inr < 0 else "green"
    sales_table.add_row(
        "[bold]TOTAL[/bold]",
        "[bold]-[/bold]",
        "[bold]-[/bold]",
        f"[bold]{total_shares_sold:.0f}[/bold]",
        "[bold]-[/bold]",
        f"[bold]₹{total_cost_basis:,.0f}[/bold]",
        "[bold]-[/bold]",
        "[bold]-[/bold]",
        f"[bold]${total_usd_proceeds:,.2f}[/bold]",
        f"[bold]₹{total_inr_proceeds:,.0f}[/bold]",
        f"[bold]${total_sale_expenses_usd:,.2f}[/bold]",
        f"[bold][{total_gain_color_usd}]${total_capital_gains_usd:,.2f}[/{total_gain_color_usd}][/bold]",
        f"[bold][{total_gain_color_inr}]₹{total_capital_gains_inr:,.0f}[/{total_gain_color_inr}][/bold]",
        "[bold]-[/bold]",
        "[bold]-[/bold]"
    )
    
    console.print(sales_table)
    
    if len(sale_events) > 20:
        console.print(f"\n   [dim]... showing all {len(sale_events)} sale events[/dim]")


def _display_sale_date_proceedings_table(sale_events, console, bank_transactions=None) -> None:
    """Display sale date-wise total proceedings for broker calculation with bank reconciliation."""
    from rich.table import Table
    from collections import defaultdict

    console.print(f"\n💰 [bold green]Sale Date-wise Broker Proceedings[/bold green]")

    # Group sales by date and calculate totals
    date_proceedings = defaultdict(lambda: {
        'total_shares': 0,
        'total_proceeds_usd': 0,
        'total_proceeds_inr': 0,
        'exchange_rate': 0,
        'tax_exchange_rate': 0,
        'transaction_count': 0
    })

    for sale in sale_events:
        date_key = sale.sale_date
        date_proceedings[date_key]['total_shares'] += sale.quantity_sold
        date_proceedings[date_key]['total_proceeds_usd'] += sale.sale_proceeds_usd
        date_proceedings[date_key]['total_proceeds_inr'] += (
            sale.sale_proceeds_usd * sale.exchange_rate_sale
        )
        date_proceedings[date_key]['exchange_rate'] = sale.exchange_rate_sale  # Use the last rate for the date
        date_proceedings[date_key]['tax_exchange_rate'] = (
            sale.capital_gains_exchange_rate or sale.exchange_rate_sale
        )
        date_proceedings[date_key]['transaction_count'] += 1

    # Use bank transactions passed from calling function (loaded earlier to avoid logs in middle of tables)
    if bank_transactions is None:
        bank_transactions = {}

    # Create proceedings table with compact terminal display (detailed data in Excel)
    proceedings_table = Table(
        show_header=True,
        header_style="bold green"
    )

    # Compact columns with truncation for terminal readability
    proceedings_table.add_column("Sale Date", style="cyan", width=10, overflow="ellipsis")
    proceedings_table.add_column("Txns", style="dim", justify="center", width=4)
    proceedings_table.add_column("Shares", style="white", justify="right", width=6)
    proceedings_table.add_column("Expected (USD)", style="green", justify="right", width=10, overflow="ellipsis")
    proceedings_table.add_column("Exp Rate", style="purple", justify="right", width=8, overflow="ellipsis")
    proceedings_table.add_column("Expected (INR)", style="green", justify="right", width=10, overflow="ellipsis")
    proceedings_table.add_column("Bank Rcvd (USD)", style="green", justify="right", width=10, overflow="ellipsis")
    proceedings_table.add_column("Bank Rate", style="purple", justify="right", width=8, overflow="ellipsis")
    proceedings_table.add_column("Bank Rcvd (INR)", style="green", justify="right", width=10, overflow="ellipsis")
    proceedings_table.add_column("Exchange GST", style="red", justify="right", width=9, overflow="ellipsis")
    proceedings_table.add_column("Final Rcvd (INR)", style="green", justify="right", width=10, overflow="ellipsis")
    proceedings_table.add_column("Net Diff (INR)", justify="right", width=10, overflow="ellipsis")
    proceedings_table.add_column("Sale Exp (USD)", style="red", justify="right", width=10, overflow="ellipsis")
    proceedings_table.add_column("Sale Exp (Tax INR)", style="red", justify="right", width=10, overflow="ellipsis")
    proceedings_table.add_column("FX Gain/Loss", style="magenta", justify="right", width=9, overflow="ellipsis")
    proceedings_table.add_column("Status", style="yellow", width=6, overflow="ellipsis")

    total_shares = 0
    total_usd_proceeds = 0
    total_expected_inr = 0
    total_bank_usd = 0
    total_inr_before_gst = 0
    total_gst = 0
    total_inr_after_gst = 0
    total_net_difference_inr = 0
    total_transfer_expense_usd = 0
    total_transfer_expense_inr = 0
    total_exchange_rate_gain_loss = 0

    # Sort by date
    for sale_date in sorted(date_proceedings.keys()):
        data = date_proceedings[sale_date]
        bank_data = bank_transactions.get(sale_date, {})
        
        # G&L statement data
        usd_proceeds = data['total_proceeds_usd']
        expected_rate = data['exchange_rate']
        expected_inr = data['total_proceeds_inr']
        
        # Update totals
        total_shares += data['total_shares']
        total_usd_proceeds += usd_proceeds
        total_expected_inr += expected_inr
        
        if bank_data:
            # Bank statement data
            bank_usd = bank_data.get('bank_usd_amount', 0)
            bank_rate = bank_data.get('bank_exchange_rate', 0)
            inr_before_gst = bank_data.get('inr_before_gst', 0)
            gst_amount = bank_data.get('gst_amount', 0)
            calculated_inr_after_gst = bank_data.get('inr_after_gst', 0)
            actual_received = bank_data.get('actual_received', calculated_inr_after_gst)
            
            # =================================================================================
            # FINANCIAL FORMULAS FOR RSU BROKER PROCEEDINGS RECONCILIATION
            # =================================================================================
            
            # FORMULA 1: Transfer Expense (USD)
            # Purpose: Calculate the USD amount lost due to brokerage/transfer costs
            # Formula: Transfer_Expense_USD = Expected_USD - Bank_Received_USD
            # Example: $6,238.87 - $6,213.87 = $25.00
            transfer_expense_usd = bank_data.get(
                'sale_expense_usd', usd_proceeds - bank_usd
            )
            
            # FORMULA 2: Transfer Expense (INR) 
            # Purpose: Convert the deductible selling expense for capital-gain tax.
            # Rule 115 uses the prescribed prior month-end rate, not the bank rate.
            transfer_expense_inr = (
                transfer_expense_usd * data['tax_exchange_rate']
            )
            
            # FORMULA 3: Exchange Rate Gain/Loss (INR)
            # Purpose: Calculate impact of exchange rate differences on actual bank proceeds
            # Formula: Exchange_Rate_Gain_Loss = (Bank_Rate - Expected_Rate) × Bank_Received_USD
            # Example: (₹87.04 - ₹86.64) × $6,213.87 = ₹0.40 × $6,213.87 = ₹2,461
            # Positive = Bank rate better than expected (gain)
            # Negative = Bank rate worse than expected (loss)
            exchange_rate_gain_loss = (bank_rate - expected_rate) * bank_usd
            
            # =================================================================================
            # RSU TAXATION STRUCTURE (IMPORTANT):
            # 1. Vesting Income: FMV at vesting is taxed as regular income (salary tax rates)
            # 2. Capital Gains: Difference between sale price and cost basis (FMV at vesting)
            #    - Short-term (<24 months): Taxed as regular income
            #    - Long-term (>=24 months): Taxed at capital gains rates (typically 10% + cess)
            # 3. Net Position: Vesting Income + Capital Gains (financial impact, not tax amount)
            # =================================================================================
            
            # =================================================================================
            # RECONCILIATION BREAKDOWN:
            # Expected Total (G&L): Expected_USD × Expected_Rate
            # Bank Before GST: Bank_USD × Bank_Rate = inr_before_gst  
            # GST Deduction: Extracted from bank transaction remarks
            # Final Received: inr_before_gst - gst_amount = inr_after_gst
            # =================================================================================
            
            # FORMULA 4: Net Difference (INR) - Gain/Loss Analysis
            # Purpose: Calculate gain/loss between expected and final received amounts
            # Formula: Net_Difference = Final_Received_INR - Expected_INR
            # Positive = Gain (received more than expected, e.g., better exchange rates)
            # Negative = Loss (received less than expected, e.g., transfer charges, GST, poor rates)
            # This captures the total impact of transfer charges, GST, and exchange rate differences
            # Note: This is for ITR filing reference only and does not affect capital gains calculations
            net_difference_inr = actual_received - expected_inr
            
            # Update totals
            total_bank_usd += bank_usd
            total_inr_before_gst += inr_before_gst
            total_gst += gst_amount
            total_inr_after_gst += actual_received
            total_net_difference_inr += net_difference_inr
            total_transfer_expense_usd += transfer_expense_usd
            total_transfer_expense_inr += transfer_expense_inr
            total_exchange_rate_gain_loss += exchange_rate_gain_loss
            
            status = "✅ Rcvd"
            
            # Format values
            bank_usd_text = f"${bank_usd:,.2f}"
            bank_rate_text = f"₹{bank_rate:.4f}"
            bank_inr_text = f"₹{inr_before_gst:,.0f}"
            gst_text = f"₹{gst_amount:,.0f}"
            final_inr_text = f"₹{actual_received:,.2f}"
            
            # Color-code net difference: green for gain, red for loss
            net_diff_color = "green" if net_difference_inr >= 0 else "red"
            net_diff_text = f"[{net_diff_color}]₹{net_difference_inr:,.0f}[/{net_diff_color}]"
            
            transfer_usd_text = f"${transfer_expense_usd:,.2f}"
            transfer_inr_text = f"₹{transfer_expense_inr:,.0f}"
            exchange_gain_loss_text = f"₹{exchange_rate_gain_loss:,.0f}"
            
        else:
            status = "⏳ Pending"
            bank_usd_text = "-"
            bank_rate_text = "-"
            bank_inr_text = "-"
            gst_text = "-"
            final_inr_text = "-"
            net_diff_text = "-"
            transfer_usd_text = "-"
            transfer_inr_text = "-"
            exchange_gain_loss_text = "-"

        proceedings_table.add_row(
            sale_date.strftime("%Y-%m-%d"),
            f"{data['transaction_count']}",
            f"{data['total_shares']:.0f}",
            f"${usd_proceeds:,.2f}",
            f"₹{expected_rate:.4f}",
            f"₹{expected_inr:,.0f}",
            bank_usd_text,
            bank_rate_text,
            bank_inr_text,
            gst_text,
            final_inr_text,
            net_diff_text,
            transfer_usd_text,
            transfer_inr_text,
            exchange_gain_loss_text,
            status
        )

    # Add totals row with color-coded net difference
    total_net_diff_color = "green" if total_net_difference_inr >= 0 else "red"
    proceedings_table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{len(date_proceedings)}[/bold]",
        f"[bold]{total_shares:.0f}[/bold]",
        f"[bold]${total_usd_proceeds:,.2f}[/bold]",
        "[bold]-[/bold]",  # No avg rate for totals
        f"[bold]₹{total_expected_inr:,.0f}[/bold]",
        f"[bold]${total_bank_usd:,.2f}[/bold]",
        "[bold]-[/bold]",  # No avg rate for totals
        f"[bold]₹{total_inr_before_gst:,.0f}[/bold]",
        f"[bold]₹{total_gst:,.0f}[/bold]",
        f"[bold]₹{total_inr_after_gst:,.0f}[/bold]",
        f"[bold {total_net_diff_color}]₹{total_net_difference_inr:,.0f}[/bold {total_net_diff_color}]",
        f"[bold]${total_transfer_expense_usd:,.2f}[/bold]",
        f"[bold]₹{total_transfer_expense_inr:,.0f}[/bold]",
        f"[bold]₹{total_exchange_rate_gain_loss:,.0f}[/bold]",
        f"[bold]{len(bank_transactions)} rcvd[/bold]"
    )

    console.print(proceedings_table)

    # Add detailed summary information
    if bank_transactions:
        console.print(f"\n[green]✅ Detailed Bank Statement Reconciliation:[/green]")
        console.print(f"   Expected Total: ${total_usd_proceeds:,.2f} → ₹{total_expected_inr:,.0f}")
        console.print(f"   Bank Received: ${total_bank_usd:,.2f} → ₹{total_inr_before_gst:,.0f}")
        console.print(f"   Exchange GST Paid: ₹{total_gst:,.0f}")
        console.print(f"   Final Amount: ₹{total_inr_after_gst:,.0f}")
        # Show net difference with proper gain/loss labeling
        if total_net_difference_inr >= 0:
            console.print(f"   [green]Net Difference (Final - Expected): +₹{total_net_difference_inr:,.0f} GAIN[/green]")
        else:
            console.print(f"   [red]Net Difference (Final - Expected): ₹{total_net_difference_inr:,.0f} LOSS[/red]")
        console.print(f"   Deductible Sale Expense: ${total_transfer_expense_usd:,.2f} (USD) | ₹{total_transfer_expense_inr:,.2f} (Rule 115 INR)")
        console.print(f"   Exchange Rate Gain/Loss: ₹{total_exchange_rate_gain_loss:,.0f}")
        
        if total_expected_inr > 0:
            gst_percentage = (total_gst / total_inr_before_gst) * 100
            transfer_percentage_inr = (total_transfer_expense_inr / total_expected_inr) * 100
            transfer_percentage_usd = (total_transfer_expense_usd / total_usd_proceeds) * 100
            net_efficiency = ((total_inr_after_gst) / total_expected_inr) * 100
            
            console.print(f"\n[cyan]📊 Cost Breakdown:[/cyan]")
            console.print(f"   Exchange GST Rate: {gst_percentage:.2f}% (of bank amount)")
            console.print(f"   Sale Expense Cost (USD): {transfer_percentage_usd:.2f}% of expected USD")
            console.print(f"   Sale Expense Cost (Tax INR): {transfer_percentage_inr:.2f}% of expected INR")
            console.print(f"   Net Efficiency: {net_efficiency:.1f}% (received vs expected)")
    else:
        console.print(f"\n[yellow]⚠️ No bank transactions found - add bank statements to see detailed breakdown[/yellow]")
    
    console.print(f"\n[dim]💡 This table shows a compact overview - full detailed breakdown available in Excel report[/dim]")
    console.print(f"[dim]📋 Capital gain deducts the confirmed sale expense; GST, FX spread, and bank rounding remain reconciliation-only.[/dim]")


def _display_company_and_account_details(console) -> None:
    """Display company and depository account details for FA filing."""
    from rich.table import Table
    from rich.panel import Panel
    from .data.models import create_default_company_records
    
    # Get company and depository account details
    employer_company, foreign_company, depository_account = create_default_company_records()
    
    console.print(f"\n🏢 [bold blue]Company & Account Details for FA Filing:[/bold blue]")
    
    # Create company details table
    company_table = Table(title="📋 Company Information", show_header=True, header_style="bold cyan")
    company_table.add_column("Type", style="white", width=18)
    company_table.add_column("Company Name", style="green", width=35)
    company_table.add_column("Address", style="yellow", width=45)
    company_table.add_column("ID/TAN", style="purple", width=12)
    
    # Employer company row
    employer_address = f"{employer_company.address_line1}, {employer_company.city}, {employer_company.state} {employer_company.pin_code}"
    company_table.add_row(
        "[cyan]Employer (India)[/cyan]",
        employer_company.company_name,
        employer_address,
        employer_company.tan
    )
    
    # Foreign company row
    foreign_address = f"{foreign_company.address_line1}, {foreign_company.city}, {foreign_company.state_province} {foreign_company.zip_code}"
    company_table.add_row(
        "[magenta]Foreign Entity[/magenta]",
        foreign_company.company_name,
        foreign_address,
        f"Code: {foreign_company.country_code}"
    )
    
    console.print(company_table)
    
    # Create depository account details table  
    account_table = Table(title="🏛️ Foreign Depository Account", show_header=True, header_style="bold cyan")
    account_table.add_column("Institution", style="green", width=18)
    account_table.add_column("Address", style="yellow", width=35)
    account_table.add_column("Account Number", style="purple", width=15)
    account_table.add_column("Status", style="white", width=18)
    account_table.add_column("Since", style="cyan", width=12)
    
    # Depository account row
    institution_address = f"{depository_account.institution_address}, {depository_account.institution_city}, {depository_account.institution_state} {depository_account.institution_zip}"
    account_table.add_row(
        depository_account.institution_name,
        institution_address,
        depository_account.account_number,
        depository_account.account_status,
        depository_account.account_opening_date.strftime("%d/%m/%Y")
    )
    
    console.print(account_table)
    
    # Add important notes
    console.print(f"\n[dim]💡 These details are pre-filled from your previous ITR for FA Schedule A1 & A3 sections[/dim]")
    console.print(f"[dim]📄 Country Code 2 = United States of America | Account Status: Beneficial Owner[/dim]")


def _display_vest_wise_details_table(summary, calendar_year: str, console, detailed: bool = False) -> None:
    """Display detailed vest-wise FA details table for compliance reporting."""
    from rich.table import Table
    
    if not summary.vest_wise_details:
        return
    
    # Create vest-wise details table
    vest_table = Table(
        title=f"📋 Foreign Assets Vest-wise Details - CL{calendar_year}",
        show_header=True, 
        header_style="bold green"
    )
    
    # Basic columns
    vest_table.add_column("Vest Date", style="cyan", width=10)
    vest_table.add_column("Grant", style="yellow", width=8) 
    vest_table.add_column("Shares", style="purple", justify="right", width=8)
    vest_table.add_column("Initial Value", style="white", justify="right", width=12)
    
    # Add detailed columns if requested
    if detailed:
        vest_table.add_column("Initial Rate", style="cyan", justify="right", width=11)
        vest_table.add_column("Initial Price", style="cyan", justify="right", width=12)
    
    vest_table.add_column("Peak Value", style="red", justify="right", width=12)
    vest_table.add_column("Peak Date", style="yellow", width=10)
    
    if detailed:
        vest_table.add_column("Peak Rate", style="red", justify="right", width=10)
        vest_table.add_column("Peak Price", style="red", justify="right", width=11)
        
    vest_table.add_column("Closing Value", style="green", justify="right", width=12)
    
    if detailed:
        vest_table.add_column("Closing Rate", style="green", justify="right", width=12)
        vest_table.add_column("Closing Price", style="green", justify="right", width=13)
    
    vest_table.add_column("Shares Sold", style="magenta", justify="right", width=10)
    vest_table.add_column("Sale Proceeds", style="white", justify="right", width=12)
    
    # Add rows for each vest
    for vest in summary.vest_wise_details:
        # Format basic values
        initial_value = f"₹{vest.initial_value_inr:,.0f}" if vest.initial_value_inr > 0 else "₹0"
        peak_value = f"₹{vest.peak_value_inr:,.0f}" if vest.peak_value_inr > 0 else "₹0"
        closing_value = f"₹{vest.closing_value_inr:,.0f}" if vest.closing_value_inr > 0 else "₹0"
        shares_sold = f"{vest.shares_sold:.1f}" if vest.shares_sold > 0 else "-"
        proceeds = f"₹{vest.gross_proceeds_inr:,.0f}" if vest.gross_proceeds_inr > 0 else "-"
        peak_date = vest.peak_date.strftime("%b %d") if vest.peak_date else "-"
        
        # Format detailed values if requested
        if detailed:
            initial_rate = f"₹{vest.initial_exchange_rate:.4f}" if vest.initial_exchange_rate > 0 else "-"
            initial_price = f"${vest.initial_stock_price:.2f}" if vest.initial_stock_price > 0 else "-"
            peak_rate = f"₹{vest.peak_exchange_rate:.4f}" if vest.peak_exchange_rate > 0 else "-"
            peak_price = f"${vest.peak_stock_price:.2f}" if vest.peak_stock_price > 0 else "-"
            closing_rate = f"₹{vest.closing_exchange_rate:.4f}" if vest.closing_exchange_rate > 0 else "-"
            closing_price = f"${vest.closing_stock_price:.2f}" if vest.closing_stock_price > 0 else "-"
        
        # Color code fully sold vests
        vest_date_display = vest.vest_date.strftime("%Y-%m-%d")
        if vest.fully_sold:
            vest_date_display = f"[dim]{vest_date_display}[/dim]"
        
        # Build row data based on detailed flag
        row_data = [
            vest_date_display,
            vest.grant_number[-6:] if len(vest.grant_number) > 6 else vest.grant_number,  # Show last 6 chars
            f"{vest.closing_shares:.1f}",
            initial_value,
        ]
        
        if detailed:
            row_data.extend([initial_rate, initial_price])
            
        row_data.extend([peak_value, peak_date])
        
        if detailed:
            row_data.extend([peak_rate, peak_price])
            
        row_data.append(closing_value)
        
        if detailed:
            row_data.extend([closing_rate, closing_price])
            
        row_data.extend([shares_sold, proceeds])
        
        vest_table.add_row(*row_data)
    
    # Calculate and add total row for Sale Proceeds
    total_sale_proceeds = sum(vest.gross_proceeds_inr for vest in summary.vest_wise_details if vest.gross_proceeds_inr > 0)
    
    if total_sale_proceeds > 0:
        # Build total row data - match the number of columns based on detailed flag
        total_row_data = ["[bold]TOTAL[/bold]"]  # First column
        
        # Column structure analysis:
        # Basic mode: 9 columns total (Sale Proceeds is column 9)
        # Detailed mode: 15 columns total (Sale Proceeds is column 15)  
        
        if detailed:
            # Need 13 dashes for columns 2-14, then Sale Proceeds in column 15
            for _ in range(13):
                total_row_data.append("[bold]-[/bold]")
        else:
            # Need 7 dashes for columns 2-8, then Sale Proceeds in column 9  
            for _ in range(7):
                total_row_data.append("[bold]-[/bold]")
        
        # Add total sale proceeds (last column)
        total_row_data.append(f"[bold]₹{total_sale_proceeds:,.0f}[/bold]")
        
        vest_table.add_row(*total_row_data)
    
    console.print("\n")
    console.print(vest_table)
    
    # Add summary information
    total_vests = len(summary.vest_wise_details)
    active_vests = len([v for v in summary.vest_wise_details if not v.fully_sold])
    sold_vests = total_vests - active_vests
    
    console.print(f"\n📊 [bold cyan]Vest Summary:[/bold cyan]")
    console.print(f"   Total Vests: [white]{total_vests}[/white]")
    console.print(f"   Active (Holding): [green]{active_vests}[/green]")
    console.print(f"   Fully Sold: [red]{sold_vests}[/red]")


def _display_multi_year_summary_table(results, console, detailed: bool = False) -> None:
    """Display balance summary table for multiple years."""
    from rich.table import Table
    
    console.print(f"\n✅ [bold green]FA Multi-Year Analysis Complete[/bold green]")
    
    if not results.year_summaries:
        console.print("[red]No data available for any years[/red]")
        return
    
    # Create comprehensive balance summary table with all information
    table = Table(title="📊 Foreign Assets Balance Summary", show_header=True, header_style="bold magenta")
    table.add_column("Year", style="cyan", width=8)
    table.add_column("Balance Type", style="cyan", width=12)
    table.add_column("Amount (₹)", style="white", justify="right", width=14)
    table.add_column("Shares", style="purple", justify="right", width=8)
    table.add_column("Stock Price", style="magenta", justify="right", width=11)
    table.add_column("Forex Rate", style="yellow", justify="right", width=11)
    table.add_column("Date", style="white", width=10)
    table.add_column("Declaration", style="white", width=12)
    table.add_column("Continuity", style="white", width=10)
    
    # Sort years and validate continuity
    years = sorted(results.year_summaries.keys(), key=lambda x: int(x))
    continuity_issues = []
    
    for i, year in enumerate(years):
        summary = results.year_summaries[year]
        
        # Check balance continuity with previous year
        continuity_status = "✅"
        if i > 0:
            prev_year = years[i-1]
            prev_summary = results.year_summaries[prev_year]
            
            # Compare closing balance of previous year with opening balance of current year
            diff = abs(prev_summary.closing_balance_inr - summary.opening_balance_inr)
            avg_balance = (prev_summary.closing_balance_inr + summary.opening_balance_inr) / 2
            
            # Reasonable thresholds for continuity warnings
            ABSOLUTE_THRESHOLD = 10000.0  # ₹10,000 absolute difference
            PERCENTAGE_THRESHOLD = 0.05   # 5% relative difference
            
            # Calculate percentage difference (avoid division by zero)
            percentage_diff = (diff / avg_balance) if avg_balance > 0 else 0
            
            # Only show warning if difference is significant
            if diff > ABSOLUTE_THRESHOLD and percentage_diff > PERCENTAGE_THRESHOLD:
                continuity_status = "⚠️"
                continuity_issues.append(f"CL{prev_year} closing (₹{prev_summary.closing_balance_inr:,.2f}) ≠ CL{year} opening (₹{summary.opening_balance_inr:,.2f}) - Diff: ₹{diff:,.0f} ({percentage_diff:.1%})")
        
        # Format values
        opening = f"₹{summary.opening_balance_inr:,.2f}" if summary.opening_balance_inr > 0 else "₹0.00"
        peak = f"₹{summary.peak_balance_inr:,.2f}" if summary.peak_balance_inr > 0 else "₹0.00"
        closing = f"₹{summary.closing_balance_inr:,.2f}" if summary.closing_balance_inr > 0 else "₹0.00"
        peak_date = summary.peak_balance_date.strftime("%b %d") if summary.peak_balance_date else "-"
        
        # Declaration status for peak balance only
        declaration = "[red]Required[/red]" if summary.declaration_required else "[green]Not Req'd[/green]"
        
        # Opening Balance (from initial vesting date, not Jan 1st)
        opening_date = "Initial" if summary.opening_balance_inr > 0 else "-"
        opening_shares = f"{summary.opening_shares:.1f}" if summary.opening_shares > 0 else "0.0"
        opening_stock_price = f"${summary.opening_stock_price:.2f}" if summary.opening_stock_price > 0 else "-"
        opening_forex_rate = f"₹{summary.opening_exchange_rate:.4f}" if summary.opening_exchange_rate > 0 else "-"
        
        table.add_row(
            f"CL{year}",
            "[purple]Opening[/purple]",
            opening,
            opening_shares,
            opening_stock_price,
            opening_forex_rate,
            opening_date,
            "-",
            continuity_status if i > 0 else "-"
        )
        
        # Peak Balance
        peak_shares = f"{summary.peak_shares:.1f}" if summary.peak_shares > 0 else "0.0"
        peak_stock_price = f"${summary.peak_stock_price:.2f}" if summary.peak_stock_price > 0 else "-"
        peak_forex_rate = f"₹{summary.peak_exchange_rate:.4f}" if summary.peak_exchange_rate > 0 else "-"
        
        table.add_row(
            "",
            "[red]Peak[/red]",
            peak,
            peak_shares,
            peak_stock_price,
            peak_forex_rate,
            peak_date,
            declaration,
            "-"
        )
        
        # Closing Balance
        closing_date = "Dec 31" if summary.closing_balance_inr > 0 else "-"
        closing_shares = f"{summary.closing_shares:.1f}" if summary.closing_shares > 0 else "0.0"
        closing_stock_price = f"${summary.year_end_stock_price:.2f}" if summary.year_end_stock_price > 0 else "-"
        closing_forex_rate = f"₹{summary.year_end_exchange_rate:.4f}" if summary.year_end_exchange_rate > 0 else "-"
        
        table.add_row(
            "",
            "[green]Closing[/green]",
            closing,
            closing_shares,
            closing_stock_price,
            closing_forex_rate,
            closing_date,
            "-",
            "-"
        )
        
        # Add separator row between years (except for last year)
        if i < len(years) - 1:
            table.add_row("", "", "", "", "", "", "", "", "")
    
    console.print(table)
    
    # Display vest-wise details for all years
    for year, summary in results.year_summaries.items():
        if summary.vest_wise_details:
            _display_vest_wise_details_table(summary, year, console, detailed)
    
    # Show continuity warnings if any
    if continuity_issues:
        console.print(f"\n⚠️  [bold yellow]Significant Balance Continuity Issues Found:[/bold yellow]")
        for issue in continuity_issues:
            console.print(f"   [yellow]• {issue}[/yellow]")
        console.print(f"\n   [dim]Note: Only showing differences > ₹{ABSOLUTE_THRESHOLD:,.0f} AND > {PERCENTAGE_THRESHOLD:.0%}. Small differences due to exchange rate variations are normal.[/dim]")
    else:
        console.print(f"\n✅ [bold green]Balance Continuity Validated:[/bold green] All year transitions within thresholds (₹{ABSOLUTE_THRESHOLD:,.0f} AND {PERCENTAGE_THRESHOLD:.0%})")
    
    # Overall compliance summary
    declaration_years = [year for year, summary in results.year_summaries.items() if summary.declaration_required]
    
    console.print(f"\n📋 [bold purple]Overall Compliance Summary:[/bold purple]")
    console.print(f"   Years Analyzed: [cyan]{len(results.year_summaries)}[/cyan]")
    console.print(f"   Years Requiring Declaration: [red]{len(declaration_years)}[/red]")
    if declaration_years:
        years_str = ", ".join([f"CL{year}" for year in sorted(declaration_years)])
        console.print(f"   Declaration Years: [red]{years_str}[/red]")
    
    # Check for incomplete data warnings
    from datetime import date
    current_year = date.today().year
    future_years = [year for year in results.year_summaries.keys() if int(year) > current_year]
    current_year_partial = [year for year in results.year_summaries.keys() if int(year) == current_year]
    
    if future_years or current_year_partial:
        console.print(f"\n⚠️  [bold yellow]Data Completeness Notice:[/bold yellow]")
        for year in current_year_partial + future_years:
            if int(year) > current_year:
                console.print(f"   [yellow]• CL{year}: Using projected data (future year)[/yellow]")
            else:
                console.print(f"   [yellow]• CL{year}: Using partial data with fallbacks for remaining months[/yellow]")
        console.print(f"   [dim]Future calculations use latest available exchange rates and stock prices as fallbacks.[/dim]")
    
    logger.info(f"Multi-year FA calculation completed: {len(results.year_summaries)} years analyzed")



@cli.command()
def help_guide() -> None:
    """📚 Show comprehensive help guide with examples and workflows."""
    console.print(Panel.fit(
        Text("Comprehensive Help Guide", style="bold purple"),
        title="[bold green]EquityWise[/bold green]",
        border_style="purple"
    ))
    
    # Table of Contents
    console.print("\n📋 [bold cyan]Table of Contents:[/bold cyan]")
    console.print("   1. Data File Setup")
    console.print("   2. Basic Commands")
    console.print("   3. Complete Workflows")
    console.print("   4. Advanced Options")
    console.print("   5. Troubleshooting")
    console.print("   6. Output Formats")
    console.print("   7. Tax Compliance Guide")
    
    # Section 1: Data File Setup
    console.print("\n" + "="*60)
    console.print("1️⃣  [bold yellow]DATA FILE SETUP[/bold yellow]")
    console.print("="*60)
    
    console.print("\n📁 [cyan]Required Files and Locations:[/cyan]")
    console.print(f"   • BenefitHistory.xlsx: {settings.benefit_history_path}")
    console.print(f"   • G&L Statements: {', '.join(str(p) for p in settings.gl_statements_paths)}")
    console.print(f"   • SBI TTBR Rates: {settings.sbi_ttbr_rates_path}")
    console.print(f"   • Adobe Stock Data: {settings.adobe_stock_data_path}")
    
    console.print("\n📥 [cyan]How to Download Each File:[/cyan]")
    console.print("   [yellow]BenefitHistory.xlsx[/yellow]:")
    console.print("     → E*Trade → Portfolio → Stock Plan → Benefit History")
    console.print("     → Export → Excel Format")
    
    console.print("\n   [yellow]Gain & Loss Statements[/yellow]:")
    console.print("     → E*Trade → Accounts → Documents → Tax Documents")
    console.print("     → Download for each year with RSU activity")
    
    console.print("\n   [yellow]SBI TTBR Exchange Rates[/yellow]:")
    console.print("     → SBI website → Interest Rates → Forex Card Rates")
    console.print("     → Download historical USD rates as CSV")
    
    console.print("\n   [yellow]Adobe Stock Data[/yellow]:")
    console.print("     → Yahoo Finance → ADBE ticker")
    console.print("     → Download historical data covering your RSU period")
    
    # Section 2: Basic Commands
    console.print("\n" + "="*60)
    console.print("2️⃣  [bold yellow]BASIC COMMANDS[/bold yellow]")
    console.print("="*60)
    
    console.print("\n🔍 [cyan]Data Validation:[/cyan]")
    console.print("   equitywise validate-data")
    console.print("   [dim]→ Check if all required files are present and accessible[/dim]")
    
    console.print("\n🎯 [cyan]Interactive Mode:[/cyan]")
    console.print("   equitywise interactive")
    console.print("   [dim]→ Guided step-by-step calculation process[/dim]")

    console.print("\n📦 [cyan]Combined Annual Reports:[/cyan]")
    console.print("   equitywise generate-reports --financial-year FY24-25")
    console.print("   [dim]→ Generate detailed RSU FY24-25 and FA calendar-year 2024 reports[/dim]")
    
    console.print("\n💰 [cyan]RSU Calculations:[/cyan]")
    console.print("   equitywise calculate-rsu")
    console.print("   equitywise calculate-rsu --financial-year FY24-25")
    console.print("   equitywise calculate-rsu --detailed")
    console.print("   [dim]→ Calculate vesting income and capital gains[/dim]")
    
    console.print("\n🌍 [cyan]Foreign Assets Calculations:[/cyan]")
    console.print("   equitywise calculate-fa")
    console.print("   equitywise calculate-fa --calendar-year 2024")
    console.print("   equitywise calculate-fa --detailed")
    console.print("   [dim]→ Calculate FA declaration requirements[/dim]")
    
    # Section 3: Complete Workflows
    console.print("\n" + "="*60)
    console.print("3️⃣  [bold yellow]COMPLETE WORKFLOWS[/bold yellow]")
    console.print("="*60)
    
    console.print("\n📊 [cyan]Annual Tax Preparation:[/cyan]")
    console.print("   1. equitywise validate-data")
    console.print("   2. equitywise generate-reports --financial-year FY24-25 --output-format both --validate")
    console.print("   [dim]→ Complete preparation for FY24-25 tax filing[/dim]")
    
    console.print("\n🔄 [cyan]Multi-Year Analysis:[/cyan]")
    console.print("   1. equitywise calculate-rsu --detailed")
    console.print("   2. equitywise calculate-fa --detailed")
    console.print("   [dim]→ Analyze all available years for compliance[/dim]")
    
    console.print("\n🔧 [cyan]Troubleshooting Workflow:[/cyan]")
    console.print("   1. equitywise validate-data")
    console.print("   2. equitywise --log-level DEBUG calculate-rsu --validate-first")
    console.print("   3. Check log files and error messages")
    console.print("   4. equitywise interactive  # If issues persist")
    console.print("   [dim]→ Systematic issue diagnosis and resolution[/dim]")
    
    # Section 4: Advanced Options
    console.print("\n" + "="*60)
    console.print("4️⃣  [bold yellow]ADVANCED OPTIONS[/bold yellow]")
    console.print("="*60)
    
    console.print("\n⚙️  [cyan]Command Options:[/cyan]")
    console.print("   --detailed              Show individual transactions")
    console.print("   --output-format excel   Generate Excel reports")
    console.print("   --output-format csv     Generate CSV files")
    console.print("   --output-format both    Generate both formats")
    console.print("   --validate-first        Check files before calculations")
    console.print("   --log-level DEBUG       Verbose error information")
    
    console.print("\n📈 [cyan]Financial Year Formats:[/cyan]")
    console.print("   FY24-25    April 2024 to March 2025")
    console.print("   FY23-24    April 2023 to March 2024")
    console.print("   [dim]→ Indian Financial Year format[/dim]")
    
    console.print("\n📅 [cyan]Calendar Year Formats:[/cyan]")
    console.print("   2024       January 2024 to December 2024")
    console.print("   2023       January 2023 to December 2023")
    console.print("   [dim]→ For Foreign Assets declarations[/dim]")
    
    # Section 5: Output Formats
    console.print("\n" + "="*60)
    console.print("5️⃣  [bold yellow]OUTPUT FORMATS[/bold yellow]")
    console.print("="*60)
    
    console.print("\n📄 [cyan]Excel Reports (.xlsx):[/cyan]")
    console.print("   • Multi-sheet workbooks with formatting")
    console.print("   • Summary and detailed transaction sheets")
    console.print("   • Bank reconciliation analysis")
    console.print("   • Ready for tax professional review")
    
    console.print("\n📊 [cyan]CSV Reports (.csv):[/cyan]")
    console.print("   • Lightweight data files")
    console.print("   • Easy to import into other tools")
    console.print("   • Separate files for each data type")
    console.print("   • Machine-readable format")
    
    console.print("\n🖥️  [cyan]Console Output:[/cyan]")
    console.print("   • Rich formatted tables")
    console.print("   • Color-coded financial data")
    console.print("   • Progress indicators")
    console.print("   • Real-time status updates")
    
    # Section 6: Tax Compliance
    console.print("\n" + "="*60)
    console.print("6️⃣  [bold yellow]TAX COMPLIANCE GUIDE[/bold yellow]")
    console.print("="*60)
    
    console.print("\n🇮🇳 [cyan]Indian Tax Requirements:[/cyan]")
    console.print("   [yellow]RSU Vesting Income:[/yellow]")
    console.print("     • Taxed as salary income at FMV on vesting date")
    console.print("     • Reported in Financial Year of vesting")
    console.print("     • Use tool's 'Vesting Income' calculations")
    
    console.print("\n   [yellow]Capital Gains on Sales:[/yellow]")
    console.print("     • Short-term (<24 months): Regular income tax rates")
    console.print("     • Long-term (≥24 months): 10% + cess (with exemption)")
    console.print("     • Cost basis = FMV at vesting date")
    
    console.print("\n   [yellow]Foreign Assets Declaration:[/yellow]")
    console.print("     • Required if peak balance > ₹2 lakhs in any CY")
    console.print("     • Only vested shares count (unvested excluded)")
    console.print("     • Use tool's FA calculation for compliance")
    
    # Section 7: Support
    console.print("\n" + "="*60)
    console.print("7️⃣  [bold yellow]GETTING HELP[/bold yellow]")
    console.print("="*60)
    
    console.print("\n💬 [cyan]Command-specific Help:[/cyan]")
    console.print("   equitywise COMMAND --help")
    console.print("   [dim]→ Detailed help for any command[/dim]")
    
    console.print("\n🔍 [cyan]Troubleshooting Commands:[/cyan]")
    console.print("   equitywise validate-data     # Check file setup")
    console.print("   equitywise interactive       # Guided assistance")
    console.print("   --log-level DEBUG             # Verbose diagnostics")
    
    console.print("\n📝 [cyan]Log Files:[/cyan]")
    console.print("   equitywise --log-file debug.log COMMAND")
    console.print("   [dim]→ Save detailed logs for analysis[/dim]")
    
    console.print("\n✨ [bold green]Happy calculating! Use 'equitywise interactive' to get started.[/bold green]")


@cli.command()
def validate_data() -> None:
    """Validate all required data files are present and accessible."""
    console.print(Panel.fit(
        Text("Data Validation", style="bold purple"),
        title="[bold green]EquityWise[/bold green]",
        border_style="purple"
    ))
    
    logger.info("Starting data validation")
    
    # Check all required files with progress indicator
    files_to_check = [
        ("BenefitHistory", settings.benefit_history_path),
        ("SBI TTBR Rates", settings.sbi_ttbr_rates_path),
        ("Adobe Stock Data", settings.adobe_stock_data_path),
    ]
    
    # Add G&L statements
    for i, path in enumerate(settings.gl_statements_paths, 1):
        files_to_check.append((f"G&L Statement {i}", path))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("[purple]Validating data files...", total=len(files_to_check))
        all_valid = True
        
        for i, (name, path) in enumerate(files_to_check):
            progress.update(task, description=f"[purple]Checking {name}...")
            time.sleep(0.1)  # Small delay to show progress
            
            if path.exists():
                console.print(f"[green]✓[/green] {name}: {path}")
            else:
                console.print(f"[red]✗[/red] {name}: {path} [red](not found)[/red]")
                all_valid = False
            
            progress.update(task, advance=1)
        
        progress.update(task, description="[purple]Data validation complete")
    
    if all_valid:
        console.print("\n[bold green]All data files are accessible![/bold green]")
        logger.info("All data files validated successfully")
    else:
        console.print("\n[bold red]Some data files are missing. Please check the paths.[/bold red]")
        logger.error("Data validation failed - missing files")


@cli.command()
def interactive() -> None:
    """Launch interactive mode for guided calculations.
    
    This command provides a step-by-step guided interface for users who prefer
    an interactive experience over command-line arguments. It will:
    
    - Guide you through data validation
    - Help select calculation types (RSU, FA, or both)
    - Assist with parameter selection (years, output formats)
    - Provide real-time feedback and suggestions
    """
    console.print(Panel.fit(
        Text("🎯 Interactive Mode", style="bold purple"),
        title="[bold green]EquityWise[/bold green]",
        border_style="purple"
    ))
    
    logger.info("Starting interactive mode")
    
    try:
        _run_interactive_mode()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Interactive mode cancelled. Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Interactive mode error: {e}[/red]")
        logger.error(f"Interactive mode error: {e}")


def _validate_financial_year_format(fy: str) -> bool:
    """Validate financial year format (e.g., FY24-25, FY23-24)."""
    import re
    pattern = r'^FY\d{2}-\d{2}$'
    if not re.match(pattern, fy):
        return False
    
    # Extract years and validate sequence
    parts = fy[2:].split('-')
    try:
        year1, year2 = int(parts[0]), int(parts[1])
        # Should be consecutive years with year2 = year1 + 1
        return year2 == year1 + 1
    except (ValueError, IndexError):
        return False


def _financial_year_to_fa_calendar_year(financial_year: str) -> int:
    """Map an Indian FY to the Schedule FA calendar year within that FY.

    For example, FY25-26 covers April 2025 through March 2026, while its
    Schedule FA reporting period is the calendar year ending December 2025.
    """
    normalized_fy = financial_year.upper()
    if not _validate_financial_year_format(normalized_fy):
        raise ValueError(
            "expected FY<YY>-<YY> with consecutive years (for example FY25-26)"
        )

    calendar_year = 2000 + int(normalized_fy[2:4])
    if not 2018 <= calendar_year <= 2030:
        raise ValueError("supported financial years are FY18-19 through FY30-31")
    return calendar_year


def _validate_required_files() -> bool:
    """Validate that all required data files exist and are accessible."""
    files_to_check = [
        ("BenefitHistory", settings.benefit_history_path),
        ("SBI TTBR Rates", settings.sbi_ttbr_rates_path),
        ("Adobe Stock Data", settings.adobe_stock_data_path),
    ]
    
    # Validate the same auto-discovered inputs used by the calculators.
    rsu_files = settings.get_rsu_files(use_auto_discovery=True)
    gl_files = settings.get_gl_statement_files(use_auto_discovery=True)

    for i, path in enumerate(rsu_files, 1):
        files_to_check.append((f"RSU Statement {i}", path))

    for i, path in enumerate(gl_files, 1):
        files_to_check.append((f"G&L Statement {i}", path))

    missing_source_groups = []
    if not rsu_files:
        missing_source_groups.append(("RSU Statement", settings.rsu_documents_dir))
    if not gl_files:
        missing_source_groups.append(("G&L Statement", settings.gl_statements_dir))
    
    missing_files = list(missing_source_groups)
    all_valid = not missing_source_groups
    
    for name, path in files_to_check:
        if not path.exists():
            console.print(f"[red]✗[/red] {name}: {path} [red](not found)[/red]")
            missing_files.append((name, path))
            all_valid = False
        else:
            console.print(f"[green]✓[/green] {name}: {path}")
    
    # Provide recovery suggestions if files are missing
    if missing_files:
        _show_file_recovery_suggestions(missing_files)
    
    return all_valid


def _show_file_recovery_suggestions(missing_files: list) -> None:
    """Show user-friendly recovery suggestions for missing files."""
    console.print("\n💡 [bold yellow]Recovery Suggestions:[/bold yellow]")
    
    suggestions = {
        "BenefitHistory": [
            "Download BenefitHistory.xlsx from E*Trade portal",
            "Go to E*Trade → Portfolio → Stock Plan → Benefit History",
            "Export to Excel and save to the expected location"
        ],
        "SBI TTBR": [
            "Download TTBR rates from SBI website",
            "Visit https://sbi.co.in/web/interest-rates/interest-rates/forex-card-rates",
            "Download historical rates as CSV file"
        ],
        "Adobe Stock Data": [
            "Download ADBE stock data from Yahoo Finance or similar",
            "Use ticker symbol 'ADBE' for Adobe stock",
            "Ensure data covers the full date range of your RSU activities"
        ],
        "G&L Statement": [
            "Download Gain & Loss statements from E*Trade",
            "Go to E*Trade → Accounts → Documents → Tax Documents",
            "Download for each year you have RSU activities"
        ],
        "RSU Statement": [
            "Download the Stock Perquisites Statement from Excelity",
            "Choose either PDF or Excel format",
            "Save it in the RSU documents directory"
        ]
    }
    
    for name, path in missing_files:
        file_type = next((key for key in suggestions.keys() if key in name), "G&L Statement")
        console.print(f"\n[cyan]📁 {name}:[/cyan]")
        for suggestion in suggestions[file_type]:
            console.print(f"   • {suggestion}")
        console.print(f"   • [dim]Expected location: {path}[/dim]")


def _handle_calculation_error(error: Exception, calculation_type: str, context: str = "") -> None:
    """Handle calculation errors with user-friendly messages and suggestions."""
    error_msg = str(error)
    error_type = type(error).__name__
    
    console.print(f"\n[red]❌ {calculation_type} calculation failed: {error_msg}[/red]")
    
    # Provide specific suggestions based on error type
    if "ValidationError" in error_type:
        console.print("\n💡 [bold yellow]Data Validation Issue:[/bold yellow]")
        console.print("   • Check that all data files contain the expected columns")
        console.print("   • Verify that dates are in the correct format")
        console.print("   • Ensure numeric values don't contain extra characters")
        console.print("   • Run 'equitywise validate-data' for detailed file checking")
        
    elif "FileNotFoundError" in error_type:
        console.print("\n💡 [bold yellow]File Not Found:[/bold yellow]")
        console.print("   • Verify all data files are in the expected locations")
        console.print("   • Check file names match exactly (case-sensitive)")
        console.print("   • Run 'equitywise validate-data' to see expected paths")
        
    elif "PermissionError" in error_type:
        console.print("\n💡 [bold yellow]Permission Issue:[/bold yellow]")
        console.print("   • Ensure you have read access to all data files")
        console.print("   • Close any Excel files that might be open")
        console.print("   • Check file is not locked by another application")
        
    elif "KeyError" in error_type or "AttributeError" in error_type:
        console.print("\n💡 [bold yellow]Data Structure Issue:[/bold yellow]")
        console.print("   • Data file format may have changed")
        console.print("   • Check if E*Trade has updated their export format")
        console.print("   • Verify column names match expected values")
        console.print("   • Consider re-downloading fresh data files")
        
    elif "ValueError" in error_type:
        console.print("\n💡 [bold yellow]Data Format Issue:[/bold yellow]")
        console.print("   • Check for invalid dates or numbers in data files")
        console.print("   • Ensure currency values don't contain extra symbols")
        console.print("   • Verify date formats are consistent")
        
    else:
        console.print("\n💡 [bold yellow]General Troubleshooting:[/bold yellow]")
        console.print("   • Try running with --validate-first flag")
        console.print("   • Check log files for detailed error information")
        console.print("   • Ensure all data files are complete and not corrupted")
        console.print("   • Try running calculation for a single year first")
    
    # Always provide general help
    console.print("\n🔧 [bold cyan]Additional Help:[/bold cyan]")
    console.print("   • Use --detailed flag for more diagnostic information")
    console.print("   • Check the output directory for any partial results")
    console.print("   • Consider running 'equitywise interactive' for guided troubleshooting")
    
    if context:
        console.print(f"   • Context: {context}")


def _handle_report_generation_error(error: Exception, report_type: str, output_format: str) -> None:
    """Handle report generation errors with specific suggestions."""
    error_msg = str(error)
    error_type = type(error).__name__
    
    console.print(f"\n[red]❌ {report_type} {output_format} report generation failed: {error_msg}[/red]")
    
    console.print("\n💡 [bold yellow]Report Generation Troubleshooting:[/bold yellow]")
    
    if "PermissionError" in error_type:
        console.print("   • Close any existing Excel files in the output directory")
        console.print("   • Ensure output directory is writable")
        console.print("   • Try changing output format to CSV if Excel fails")
        
    elif "FileNotFoundError" in error_type:
        console.print("   • Output directory may not exist")
        console.print("   • Check if you have write permissions to output location")
        
    elif output_format == "excel" and ("openpyxl" in error_msg or "xlsxwriter" in error_msg):
        console.print("   • Excel library issue - try CSV format instead")
        console.print("   • Run: equitywise calculate-rsu --output-format csv")
        
    else:
        console.print("   • Try running calculation without reports first")
        console.print("   • Check if calculation data is valid")
        console.print("   • Try a different output format")
        console.print("   • Ensure sufficient disk space in output directory")
    
    console.print("\n🔄 [bold cyan]Recovery Options:[/bold cyan]")
    console.print("   • Re-run with --output-format csv for lightweight export")
    console.print("   • Use --detailed flag to see exactly what data failed")
    console.print("   • Check output directory for any partial files")


def _run_interactive_mode() -> None:
    """Run the interactive mode with guided prompts."""
    console.print("\n[bold cyan]Welcome to EquityWise - Smart Equity Tax Calculations![/bold cyan]")
    console.print("This interactive mode will guide you through the calculation process step by step.\n")
    
    # Step 1: Data validation
    console.print("🔍 [bold purple]Step 1: Data Validation[/bold purple]")
    console.print("Let's first check if all required data files are available...")
    
    if not _validate_required_files():
        console.print("\n[red]❌ Some required files are missing![/red]")
        console.print("Please ensure all data files are in the correct locations before proceeding.")
        console.print("Run 'equitywise validate-data' for detailed file location information.")
        return
    
    console.print("\n[green]✅ All data files are accessible![/green]")
    
    # Step 2: Calculation type selection
    console.print("\n📊 [bold purple]Step 2: Calculation Type Selection[/bold purple]")
    console.print("What would you like to calculate?")
    console.print("  [cyan]1.[/cyan] RSU calculations (Financial Year basis)")
    console.print("  [cyan]2.[/cyan] Foreign Assets calculations (Calendar Year basis)")
    console.print("  [cyan]3.[/cyan] Both RSU and Foreign Assets")
    
    while True:
        try:
            choice = console.input("\nEnter your choice (1/2/3): ").strip()
            if choice in ['1', '2', '3']:
                break
            console.print("[yellow]Please enter 1, 2, or 3[/yellow]")
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt()
    
    # Step 3: Parameter collection based on choice
    if choice in ['1', '3']:  # RSU calculations
        rsu_params = _collect_rsu_parameters()
    
    if choice in ['2', '3']:  # FA calculations  
        fa_params = _collect_fa_parameters()
    
    # Step 4: Output format selection
    console.print("\n📄 [bold purple]Step 4: Output Format Selection[/bold purple]")
    console.print("What output format would you prefer?")
    console.print("  [cyan]1.[/cyan] Excel (.xlsx) - Comprehensive reports with multiple sheets")
    console.print("  [cyan]2.[/cyan] CSV - Lightweight data files for analysis")
    console.print("  [cyan]3.[/cyan] Both Excel and CSV")
    
    while True:
        try:
            output_choice = console.input("\nEnter your choice (1/2/3): ").strip()
            if output_choice in ['1', '2', '3']:
                output_format = {'1': 'excel', '2': 'csv', '3': 'both'}[output_choice]
                break
            console.print("[yellow]Please enter 1, 2, or 3[/yellow]")
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt()
    
    # Step 5: Execution confirmation and run
    console.print("\n🚀 [bold purple]Step 5: Execution[/bold purple]")
    console.print("Ready to run calculations with the following settings:")
    
    if choice in ['1', '3']:
        fy_text = rsu_params['financial_year'] if rsu_params['financial_year'] else 'All available years'
        detail_text = 'Yes' if rsu_params['detailed'] else 'No'
        console.print(f"  [cyan]RSU Calculation:[/cyan] {fy_text} (Detailed: {detail_text})")
    
    if choice in ['2', '3']:
        cy_text = str(fa_params['calendar_year']) if fa_params['calendar_year'] else 'All available years'
        detail_text = 'Yes' if fa_params['detailed'] else 'No'
        console.print(f"  [cyan]FA Calculation:[/cyan] {cy_text} (Detailed: {detail_text})")
    
    console.print(f"  [cyan]Output Format:[/cyan] {output_format.title()}")
    
    try:
        confirm = console.input("\nProceed with calculations? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            console.print("[yellow]Calculation cancelled.[/yellow]")
            return
    except (EOFError, KeyboardInterrupt):
        raise KeyboardInterrupt()
    
    # Execute calculations
    console.print("\n" + "="*60)
    
    if choice in ['1', '3']:  # RSU calculations
        console.print("\n[bold green]Running RSU Calculations...[/bold green]")
        from click.testing import CliRunner
        runner = CliRunner()
        
        cmd_args = ['calculate-rsu', '--output-format', output_format]
        if rsu_params['financial_year']:
            cmd_args.extend(['--financial-year', rsu_params['financial_year']])
        if rsu_params['detailed']:
            cmd_args.append('--detailed')
        
        # Run the actual RSU calculation
        result = runner.invoke(cli, cmd_args, catch_exceptions=False)
        
    if choice in ['2', '3']:  # FA calculations
        console.print("\n[bold green]Running Foreign Assets Calculations...[/bold green]")
        from click.testing import CliRunner
        runner = CliRunner()
        
        cmd_args = ['calculate-fa', '--output-format', output_format]
        if fa_params['calendar_year']:
            cmd_args.extend(['--calendar-year', str(fa_params['calendar_year'])])
        if fa_params['detailed']:
            cmd_args.append('--detailed')
        
        # Run the actual FA calculation
        result = runner.invoke(cli, cmd_args, catch_exceptions=False)
    
    console.print("\n" + "="*60)
    console.print("[bold green]🎉 Interactive calculations completed![/bold green]")
    console.print("Check the output directory for generated reports.")


def _collect_rsu_parameters() -> dict:
    """Collect RSU calculation parameters interactively."""
    console.print("\n💰 [bold cyan]RSU Calculation Parameters[/bold cyan]")
    
    # Financial year selection
    console.print("Which financial year would you like to calculate?")
    console.print("  [cyan]1.[/cyan] All available years")
    console.print("  [cyan]2.[/cyan] Specific financial year (e.g., FY24-25)")
    
    while True:
        try:
            fy_choice = console.input("\nEnter your choice (1/2): ").strip()
            if fy_choice in ['1', '2']:
                break
            console.print("[yellow]Please enter 1 or 2[/yellow]")
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt()
    
    financial_year = None
    if fy_choice == '2':
        while True:
            try:
                fy = console.input("Enter financial year (format: FY24-25): ").strip()
                if _validate_financial_year_format(fy):
                    financial_year = fy
                    break
                console.print("[yellow]Invalid format. Please use FY<YY>-<YY> format (e.g., FY24-25)[/yellow]")
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt()
    
    # Detailed output selection
    while True:
        try:
            detailed_choice = console.input("Show detailed transaction breakdown? (y/N): ").strip().lower()
            detailed = detailed_choice in ['y', 'yes']
            break
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt()
    
    return {
        'financial_year': financial_year,
        'detailed': detailed
    }


def _collect_fa_parameters() -> dict:
    """Collect Foreign Assets calculation parameters interactively."""
    console.print("\n🌍 [bold cyan]Foreign Assets Calculation Parameters[/bold cyan]")
    
    # Calendar year selection
    console.print("Which calendar year would you like to calculate?")
    console.print("  [cyan]1.[/cyan] All available years")
    console.print("  [cyan]2.[/cyan] Specific calendar year (e.g., 2024)")
    
    while True:
        try:
            cy_choice = console.input("\nEnter your choice (1/2): ").strip()
            if cy_choice in ['1', '2']:
                break
            console.print("[yellow]Please enter 1 or 2[/yellow]")
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt()
    
    calendar_year = None
    if cy_choice == '2':
        while True:
            try:
                cy = console.input("Enter calendar year (2018-2030): ").strip()
                cy_int = int(cy)
                if 2018 <= cy_int <= 2030:
                    calendar_year = cy_int
                    break
                console.print("[yellow]Please enter a year between 2018 and 2030[/yellow]")
            except (ValueError, EOFError, KeyboardInterrupt):
                if cy.strip() == '':
                    raise KeyboardInterrupt()
                console.print("[yellow]Please enter a valid year[/yellow]")
    
    # Detailed output selection
    while True:
        try:
            detailed_choice = console.input("Show detailed vest-wise breakdown? (y/N): ").strip().lower()
            detailed = detailed_choice in ['y', 'yes']
            break
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt()
    
    return {
        'calendar_year': calendar_year,
        'detailed': detailed
    }


if __name__ == "__main__":
    cli()
