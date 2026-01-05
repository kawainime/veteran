#!/usr/bin/env python3
"""
Veterans Verification CLI - Main Entry Point

An improved CLI tool for ChatGPT Plus US Veterans verification via SheerID.

Usage:
    python main.py [OPTIONS]

Examples:
    python main.py                          # Run with defaults (data.txt)
    python main.py --live --year 2025       # Live scrape 2025 deaths
    python main.py --live --letters A,B,C   # Scrape specific letters
    python main.py --proxy http://...       # With proxy
    python main.py --single "John|Doe|..."  # Single record
    python main.py -v                       # Verbose mode
"""

import sys
import time
import random
from pathlib import Path
from datetime import date, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

import click

from src.config import ConfigManager, Config
from src.data_parser import DataParser, VeteranData
from src.utils import ProxyManager, DeduplicationTracker, format_duration
from src.verifier import VerificationOrchestrator, VerificationStatus
from src.ui import ConsoleUI, create_simple_progress_callback, create_request_log_callback


def generate_fake_discharge_date() -> str:
    """
    Generate a fake discharge date that is:
    - Within the current month
    - Before or equal to today
    - Random day between 1 and today's day
    
    This ensures the discharge is "within 12 months" as required by SheerID.
    """
    today = date.today()
    
    # Random day between 1 and today's day (not future)
    if today.day > 1:
        random_day = random.randint(1, today.day - 1)
    else:
        # If today is the 1st, use last month
        last_month = today - timedelta(days=1)
        random_day = random.randint(1, last_month.day)
        return last_month.replace(day=random_day).strftime("%Y-%m-%d")
    
    return today.replace(day=random_day).strftime("%Y-%m-%d")


def get_base_path() -> Path:
    """Get the base path for config and data files."""
    return Path(__file__).parent


@click.command()
@click.option(
    "--proxy",
    type=str,
    help="Proxy URL (e.g., http://user:pass@host:port)",
)
@click.option(
    "--proxy-file",
    type=click.Path(exists=True),
    help="Load proxies from file",
)
@click.option(
    "--no-dedup",
    is_flag=True,
    help="Disable deduplication check",
)
@click.option(
    "--single",
    type=str,
    help='Single record: "FirstName|LastName|Branch|DOB|DischargeDate"',
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate data without submitting",
)
@click.option(
    "--max-retries",
    type=int,
    default=3,
    help="Maximum retry attempts per request",
)
@click.option(
    "--delay",
    type=float,
    default=0.5,
    help="Delay between records in seconds",
)
@click.option(
    "--config",
    "config_file",
    type=str,
    default="config.json",
    help="Config file path",
)
@click.option(
    "--data",
    "data_file",
    type=str,
    default="data.txt",
    help="Data file path",
)
@click.option(
    "--stop-on-success",
    is_flag=True,
    default=True,
    help="Stop after first successful verification",
)
@click.option(
    "--continue-on-success",
    is_flag=True,
    help="Continue processing after success",
)
@click.option(
    "--retry-until-success",
    is_flag=True,
    help="Keep retrying all records until one succeeds",
)
@click.option(
    "--max-rounds",
    type=int,
    default=0,
    help="Maximum retry rounds (0=unlimited, only with --retry-until-success)",
)
@click.option(
    "--live",
    is_flag=True,
    help="Live scrape data from VA.gov instead of using data.txt",
)
@click.option(
    "--year",
    "scrape_year",
    type=str,
    default="2025",
    help="Year of death to scrape (for --live mode)",
)
@click.option(
    "--letters",
    "scrape_letters",
    type=str,
    default="A",
    help="Letters to scrape, comma-separated (e.g., A,B,C or A-Z)",
)
@click.option(
    "--branch",
    "scrape_branch",
    type=str,
    default="NA",
    help="Branch filter for scraping (Army, Navy, etc. or NA for all)",
)
@click.option(
    "--limit-per-letter",
    type=int,
    default=50,
    help="Max records per letter when scraping",
)
@click.option(
    "--source",
    "scrape_source",
    type=click.Choice(["vlm", "anc"], case_sensitive=False),
    default="anc",
    help="Data source for --live mode: vlm (VA Legacy Memorial) or anc (Arlington National Cemetery, default)",
)
@click.option(
    "--auto-reset",
    is_flag=True,
    help="Auto reset verification ID when locked (uses browser automation)",
)
@click.option(
    "--no-headless",
    is_flag=True,
    help="Show browser window during auto-reset (for debugging)",
)
@click.option(
    "--cookies",
    "cookies_file",
    type=str,
    help="Path to cookies.json file exported from browser (for auto-reset)",
)
@click.option(
    "--rotate-proxy",
    is_flag=True,
    help="Rotate proxy for each verification attempt",
)
@click.option(
    "--fake-dod",
    is_flag=True,
    help="Use fake discharge date (within current month, before today) to meet 12-month requirement",
)
def main(
    proxy: str,
    proxy_file: str,
    no_dedup: bool,
    single: str,
    verbose: bool,
    dry_run: bool,
    max_retries: int,
    delay: float,
    config_file: str,
    data_file: str,
    stop_on_success: bool,
    continue_on_success: bool,
    retry_until_success: bool,
    max_rounds: int,
    live: bool,
    scrape_year: str,
    scrape_letters: str,
    scrape_branch: str,
    limit_per_letter: int,
    scrape_source: str,
    auto_reset: bool,
    no_headless: bool,
    cookies_file: str,
    rotate_proxy: bool,
    fake_dod: bool,
):
    """
    Veterans Verification CLI - US Veterans verification for ChatGPT Plus.
    
    Automates the SheerID verification process using veteran data.
    """
    base_path = get_base_path()
    ui = ConsoleUI(verbose=verbose)
    
    # Print banner
    ui.print_banner()
    
    # Load configuration
    config_manager = ConfigManager(base_path)
    
    if not config_manager.config_exists(config_file):
        ui.print_error(
            f"Config file '{config_file}' not found!\n\n"
            "Create it by copying config.example.json:\n"
            f"  cp config.example.json {config_file}\n\n"
            "Then edit it with your credentials.",
            title="Configuration Missing"
        )
        sys.exit(1)
    
    try:
        config = config_manager.load(config_file)
    except Exception as e:
        ui.print_error(f"Failed to load config: {e}")
        sys.exit(1)
    
    # Validate configuration
    valid, errors = config.is_valid()
    if not valid:
        ui.print_error(
            "Configuration errors:\n" + "\n".join(f"  • {e}" for e in errors),
            title="Invalid Configuration"
        )
        ui.print_token_expired_help()
        sys.exit(1)
    
    # Override settings
    if max_retries:
        config.settings.max_retries = max_retries
    if delay:
        config.settings.delay_between_records = delay
    
    # Load proxies
    proxy_manager = None
    if proxy:
        proxy_manager = ProxyManager([proxy])
    elif proxy_file:
        proxy_manager = ProxyManager.from_file(Path(proxy_file))
    else:
        default_proxy_file = base_path / "proxy.txt"
        if default_proxy_file.exists():
            proxy_manager = ProxyManager.from_file(default_proxy_file)
    
    # Load veteran records
    records = []
    live_scraper = None
    
    if single:
        # Single record mode
        record = DataParser.parse_line(single)
        if not record:
            ui.print_error(
                "Invalid record format.\n"
                'Expected: "FirstName|LastName|Branch|DOB|DischargeDate"\n'
                'Example: "John|Smith|Army|1990-01-15|2024-06-01"'
            )
            sys.exit(1)
        records = [record]
    elif live:
        # Live scraping mode - will scrape on-the-fly
        # Parse letters
        if "-" in scrape_letters:
            # Range like A-Z
            parts = scrape_letters.split("-")
            if len(parts) == 2:
                start, end = parts[0].upper(), parts[1].upper()
                letters = "".join([chr(i) for i in range(ord(start), ord(end) + 1)])
            else:
                letters = scrape_letters.replace(",", "").upper()
        else:
            letters = scrape_letters.replace(",", "").upper()
        
        # Select scraper based on source
        if scrape_source.lower() == "anc":
            from src.anc_scraper import ANCExplorerScraper
            
            # ANC requires proxy
            scraper_proxy = proxy
            if not scraper_proxy and proxy_manager:
                scraper_proxy = proxy_manager.get_current()
            
            if not scraper_proxy:
                ui.print_error("ANC Explorer requires a proxy. Use --proxy or --proxy-file")
                sys.exit(1)
            
            ui.print_info(f"🔴 LIVE MODE: Arlington National Cemetery Explorer")
            ui.print_info(f"   Year: {scrape_year} | Letters: {letters} | Limit: {limit_per_letter}/letter")
            ui.print_info(f"   Source: [bold cyan]ANC[/bold cyan] (Real DOB & Branch data)")
            
            live_scraper = ANCExplorerScraper(
                proxy=scraper_proxy,
                delay=0.5,
                verbose=verbose,
                console=ui.console
            )
            live_scraper_type = "anc"
        else:
            from scraper import VLMScraper
            
            ui.print_info(f"🔴 LIVE MODE: Scraping VA.gov Veterans Legacy Memorial")
            ui.print_info(f"   Year: {scrape_year} | Letters: {letters} | Branch: {scrape_branch} | Limit: {limit_per_letter}/letter")
            
            live_scraper = VLMScraper(delay=0.5, verbose=verbose)
            live_scraper_type = "vlm"
        # Records will be loaded on-the-fly
    else:
        # Load from file
        data_path = base_path / data_file
        if not data_path.exists():
            ui.print_error(
                f"Data file '{data_file}' not found!\n\n"
                "Create it by copying data.example.txt:\n"
                f"  cp data.example.txt {data_file}\n\n"
                "Then add your veteran records.\n\n"
                "Or use --live mode to scrape directly from VA.gov",
                title="Data File Missing"
            )
            sys.exit(1)
        
        records = DataParser.parse_file(data_path)
        
        if not records:
            ui.print_error("No valid records found in data file!")
            sys.exit(1)
    
    # Initialize deduplication tracker
    dedup_tracker = None
    if not no_dedup:
        dedup_tracker = DeduplicationTracker(base_path / "used.txt")
    
    # Print configuration info
    record_count_display = len(records) if records else f"LIVE ({letters})"
    ui.print_config_info(
        proxy_count=len(proxy_manager) if proxy_manager else 0,
        record_count=len(records) if records else 0,
        using_cloudscraper=True,
        email_configured=config.email.is_valid(),
    )
    
    if live:
        ui.console.print(f"   [bold magenta]📡 Live Mode[/bold magenta]     Year={scrape_year} Letters={letters} Source={scrape_source.upper()}")
    
    if fake_dod:
        ui.console.print(f"   [bold yellow]📅 Fake DOD[/bold yellow]      Using current month discharge date (within 12 months)")
    
    # Dry run mode
    if dry_run:
        if live:
            ui.print_error("Dry run mode not supported with --live")
            sys.exit(1)
        ui.print_info("Dry run mode - validating records without submitting")
        for i, record in enumerate(records, 1):
            warnings = DataParser.validate_record(record)
            status = "✅" if not warnings else "⚠️"
            ui.console.print(f"[{i}] {status} {record.full_name} ({record.branch})")
            for w in warnings:
                ui.print_warning(f"    {w}")
        return
    
    # Run verification
    start_time = time.time()
    success_count = 0
    failed_count = 0
    skipped_count = 0
    round_count = 0
    
    current_proxy = proxy_manager.get_current() if proxy_manager else None
    
    # Retry until success loop
    keep_trying = True
    while keep_trying:
        round_count += 1
        if retry_until_success and round_count > 1:
            ui.print_info(f"\n🔄 Round {round_count} - Retrying...")
            if dedup_tracker:
                dedup_tracker = DeduplicationTracker(base_path / "used.txt")
        
        try:
            with VerificationOrchestrator(
                config=config,
                proxy=current_proxy,
                on_progress=create_simple_progress_callback(ui) if verbose else lambda x: None,
                on_request_log=create_request_log_callback(ui, verbose),
            ) as orchestrator:
                
                # Determine record source
                if live:
                    # Live scraping mode - stream records
                    if live_scraper_type == "anc":
                        record_generator = live_scraper.scrape_by_letters(
                            letters=letters,
                            year=scrape_year,
                            max_per_letter=limit_per_letter,
                        )
                    else:
                        record_generator = live_scraper.scrape_all(
                            letters=letters,
                            year_of_death=scrape_year,
                            branch=scrape_branch,
                            max_per_letter=limit_per_letter,
                        )
                    total_records = "LIVE"
                    record_iter = enumerate(record_generator, 1)
                else:
                    total_records = len(records)
                    record_iter = enumerate(records, 1)
                
                for i, scraped_record in record_iter:
                    # Convert scraped record to VeteranData if from live scraper
                    if live:
                        line = scraped_record.to_verification_format()
                        record = DataParser.parse_line(line)
                        if not record:
                            continue
                    else:
                        record = scraped_record
                    
                    # Apply fake discharge date if enabled
                    if fake_dod:
                        fake_discharge = generate_fake_discharge_date()
                        record = VeteranData(
                            first_name=record.first_name,
                            last_name=record.last_name,
                            branch=record.branch,
                            birth_date=record.birth_date,
                            discharge_date=fake_discharge,
                            organization=record.organization,
                        )
                        if verbose:
                            ui.console.print(f"   [dim]📅 Fake DOD: {fake_discharge}[/dim]")
                    
                    # Check deduplication
                    if dedup_tracker and dedup_tracker.is_used(
                        record.first_name, record.last_name, record.birth_date
                    ):
                        if not retry_until_success:
                            ui.print_record_start(i, total_records, record)
                            ui.console.print("   [yellow]⏭️ SKIPPED[/yellow] Already processed")
                            skipped_count += 1
                        continue
                    
                    # Validate record
                    warnings = DataParser.validate_record(record)
                    for w in warnings:
                        if verbose:
                            ui.print_warning(w)
                    
                    # Rotate proxy if enabled
                    if rotate_proxy and proxy_manager:
                        current_proxy = proxy_manager.get_next()
                        orchestrator.set_proxy(current_proxy)
                        if verbose:
                            proxy_short = current_proxy[:40] + "..." if len(current_proxy) > 40 else current_proxy
                            ui.console.print(f"   [dim]🔄 Proxy: {proxy_short}[/dim]")
                    
                    # Print record start
                    ui.print_record_start(i, total_records, record)
                    
                    # Run verification
                    result = orchestrator.verify(record)
                    
                    # Mark as used
                    if dedup_tracker and result.status != VerificationStatus.ERROR:
                        dedup_tracker.mark_used(
                            record.first_name, record.last_name, record.birth_date
                        )
                    
                    # Print result
                    ui.print_result(result)
                    
                    # Update counters
                    if result.status == VerificationStatus.SUCCESS:
                        success_count += 1
                        ui.print_success_banner(result)
                        keep_trying = False  # Stop retry loop on success
                        
                        if not continue_on_success and stop_on_success:
                            ui.print_info("Stopping after successful verification")
                            break
                    
                    elif result.status == VerificationStatus.TOKEN_EXPIRED:
                        failed_count += 1
                        ui.print_token_expired_help()
                        keep_trying = False  # Can't continue without valid token
                        break
                    
                    elif result.status == VerificationStatus.ERROR:
                        failed_count += 1
                        # Check if it's a verification ID error that can be auto-reset
                        error_code = result.details.get("error") if result.details else None
                        can_auto_reset = error_code in ("verification_id_reused", "verification_in_error_state")
                        
                        if can_auto_reset and auto_reset:
                            ui.print_warning("🔄 Verification ID locked - attempting auto-reset...")
                            from src.browser_reset import reset_via_api, reset_verification, HAS_PLAYWRIGHT
                            
                            # Try API reset first (faster)
                            reset_success, new_vid, reset_msg = reset_via_api(
                                config.access_token,
                                proxy=current_proxy
                            )
                            
                            if reset_success:
                                ui.print_success(f"✅ API Reset: {reset_msg}")
                                VerificationOrchestrator.reset_failed_ids()
                                continue  # Retry this record
                            
                            # If API reset failed, try browser
                            if HAS_PLAYWRIGHT:
                                ui.print_warning("API reset failed, trying browser automation...")
                                # Look for cookies file in base path if not specified
                                cookies_path = cookies_file
                                if not cookies_path:
                                    default_cookies = base_path / "cookies.json"
                                    if default_cookies.exists():
                                        cookies_path = str(default_cookies)
                                
                                reset_success, new_vid, reset_msg = reset_verification(
                                    config.access_token,
                                    headless=not no_headless,
                                    proxy=current_proxy,
                                    cookies_file=cookies_path
                                )
                                
                                if reset_success:
                                    ui.print_success(f"✅ Browser Reset: {reset_msg}")
                                    VerificationOrchestrator.reset_failed_ids()
                                    continue  # Retry this record
                                else:
                                    ui.print_error(f"Browser reset failed: {reset_msg}")
                            else:
                                ui.print_warning("Playwright not installed. Run: pip install playwright && playwright install chromium")
                        
                        if can_auto_reset:
                            ui.print_error(
                                "🔴 Verification ID tidak berubah!\n\n"
                                "ChatGPT API mengembalikan ID yang SAMA yang sudah dalam state error.\n\n"
                                "SOLUSI:\n"
                                "1. Buka browser: https://chatgpt.com/veterans-claim\n"
                                "2. Klik 'Verify Eligibility' untuk reset\n"
                                "3. Jalankan tool ini lagi\n"
                                "4. Atau gunakan --auto-reset untuk auto reset\n",
                                title="Verification ID Locked"
                            )
                            keep_trying = False
                            break
                    
                    elif result.status == VerificationStatus.FAILED:
                        failed_count += 1
                    
                    elif result.status == VerificationStatus.SKIPPED:
                        skipped_count += 1
                    
                    # Delay between records
                    if not live or i % 10 != 0:  # Less delay info for live mode
                        time.sleep(config.settings.delay_between_records)
                
                # End of records - check if we should retry
                if not retry_until_success or success_count > 0:
                    keep_trying = False
                elif retry_until_success and success_count == 0:
                    # Check max rounds limit
                    if max_rounds > 0 and round_count >= max_rounds:
                        ui.print_warning(f"Reached maximum rounds ({max_rounds}). Stopping.")
                        keep_trying = False
                    else:
                        rounds_info = f" (max: {max_rounds})" if max_rounds > 0 else " (unlimited)"
                        ui.print_warning(f"Round {round_count} complete - No success yet{rounds_info}. Retrying in 5 seconds...")
                        time.sleep(5)
        
        except KeyboardInterrupt:
            ui.print_warning("\nInterrupted by user")
            keep_trying = False
        
        except Exception as e:
            ui.print_error(f"Unexpected error: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            if not retry_until_success:
                keep_trying = False
            else:
                ui.print_warning("Error occurred. Retrying in 10 seconds...")
                time.sleep(10)
    
    # Print summary
    total_time = time.time() - start_time
    ui.print_summary(
        success=success_count,
        failed=failed_count,
        skipped=skipped_count,
        total_time=total_time,
    )


if __name__ == "__main__":
    main()
