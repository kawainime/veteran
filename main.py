#!/usr/bin/env python3
"""
Veterans Verification CLI (Standalone Version)
Repaired for Ubuntu 24.04 - Removes 'src' dependency.
"""

import sys
import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Generator, Union
from dataclasses import dataclass, asdict

# Try to import external libraries
try:
    import click
    import cloudscraper
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    print("CRITICAL ERROR: Missing dependencies.")
    print("Please run: pip install click cloudscraper rich requests")
    sys.exit(1)

# ==========================================
# 1. UTILS & CONFIG (Replaces src.utils/config)
# ==========================================

class ConsoleUI:
    """Handles console output."""
    def __init__(self, verbose=False):
        self.console = Console()
        self.verbose = verbose

    def print_banner(self):
        self.console.print(Panel(
            "[bold cyan]Veterans Verification CLI (Standalone)[/bold cyan]\n"
            "[dim]Repaired Version - Scraper & Token Checker Active[/dim]",
            title="System Ready",
            border_style="green"
        ))

    def print_error(self, msg, title="Error"):
        self.console.print(Panel(f"[bold red]{msg}[/bold red]", title=title, border_style="red"))

    def print_success(self, msg):
        self.console.print(f"[bold green]✅ {msg}[/bold green]")

    def print_info(self, msg):
        self.console.print(f"[cyan]ℹ️ {msg}[/cyan]")

    def print_warning(self, msg):
        self.console.print(f"[yellow]⚠️ {msg}[/yellow]")

class ConfigManager:
    """Manages configuration loading."""
    @staticmethod
    def load(path: str) -> dict:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file {path} not found")
        with open(p, 'r') as f:
            return json.load(f)

class ProxyManager:
    """Simple proxy manager."""
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.current_idx = 0

    @classmethod
    def from_file(cls, path: Path):
        if not path.exists():
            return cls([])
        with open(path) as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return cls(proxies)

    def get_current(self) -> Optional[str]:
        if not self.proxies: return None
        return self.proxies[self.current_idx % len(self.proxies)]

    def get_next(self) -> Optional[str]:
        if not self.proxies: return None
        self.current_idx += 1
        return self.get_current()

    def __len__(self):
        return len(self.proxies)

# ==========================================
# 2. DATA MODELS (Replaces src.data_parser)
# ==========================================

@dataclass
class VeteranData:
    first_name: str
    last_name: str
    branch: str
    birth_date: str
    discharge_date: str
    organization: str = "NA"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class DataParser:
    @staticmethod
    def parse_line(line: str) -> Optional[VeteranData]:
        parts = line.strip().split('|')
        if len(parts) < 5:
            return None
        return VeteranData(
            first_name=parts[0],
            last_name=parts[1],
            branch=parts[2],
            birth_date=parts[3],
            discharge_date=parts[4]
        )

    @staticmethod
    def parse_file(path: Path) -> List[VeteranData]:
        records = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    rec = DataParser.parse_line(line)
                    if rec: records.append(rec)
        return records

# ==========================================
# 3. SCRAPER LOGIC (Ported from scraper.py)
# ==========================================

class VLMScraper:
    """Ported directly from scraper.py to remove dependency."""
    API_URL = "https://www.vlm.cem.va.gov/api/v1.1/gcio/profile/search/basic"
    BRANCH_MAP = {
        "US Army": "Army", "Army": "Army",
        "US Navy": "Navy", "Navy": "Navy",
        "US Air Force": "Air Force", "Air Force": "Air Force",
        "US Marine Corps": "Marine Corps", "Marine Corps": "Marine Corps"
    }

    def __init__(self, delay=1.0, verbose=False):
        self.delay = delay
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json;charset=utf-8",
            "Origin": "https://www.vlm.cem.va.gov"
        })

    def scrape_by_letters(self, letters, year="", limit=50):
        """Scrape generator."""
        console = Console()
        for letter in letters.replace(",","").upper():
            if self.verbose: console.log(f"Scraping letter: {letter}")
            
            payload = {
                "lastName": letter,
                "yearOfDeath": year,
                "limit": limit,
                "page": 1
            }
            
            try:
                resp = self.session.post(self.API_URL, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json().get('response', {}).get('data', [])
                    for profile in data:
                        # Parsing Logic
                        fname = profile.get('first_name', '').title()
                        lname = profile.get('last_name', '').title()
                        branch_raw = profile.get('service_branch_id', 'Army')
                        branch = self.BRANCH_MAP.get(branch_raw, 'Army')
                        death_date = profile.get('date_of_death', '')[:10]
                        
                        # Guess DOB (Death - 60 years roughly)
                        try:
                            dy = int(death_date[:4])
                            birth_date = f"{dy-60}-01-01"
                        except:
                            birth_date = "1950-01-01"

                        if fname and lname and death_date:
                            yield VeteranData(fname, lname, branch, birth_date, death_date)
                
                time.sleep(self.delay)
            except Exception as e:
                if self.verbose: console.log(f"Error scraping {letter}: {e}")

# ==========================================
# 4. VERIFICATION LOGIC (Simplified)
# ==========================================

class TokenChecker:
    """Replaces full Verifier since src is missing. Checks Token & ID creation."""
    
    def __init__(self, config, proxy_manager=None):
        self.token = config.get('accessToken')
        self.scraper = cloudscraper.create_scraper()
        self.proxy = proxy_manager.get_current() if proxy_manager else None

    def check_token_and_create_id(self):
        """Checks if token is valid by creating a Verification ID."""
        url = 'https://chatgpt.com/backend-api/veterans/create_verification'
        headers = {
            'authorization': f'Bearer {self.token}',
            'content-type': 'application/json',
            'origin': 'https://chatgpt.com',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        proxies = {'http': self.proxy, 'https': self.proxy} if self.proxy else None
        
        try:
            resp = self.scraper.post(
                url, 
                json={'program_id': '690415d58971e73ca187d8c9'}, # Veterans program ID
                headers=headers,
                proxies=proxies,
                timeout=15
            )
            
            if resp.status_code == 200:
                vid = resp.json().get('verification_id')
                return True, f"Token Valid! Verification ID created: {vid}"
            elif resp.status_code == 401:
                return False, "Token Expired (401)"
            elif resp.status_code == 403:
                return False, "Access Forbidden (403) - Try Proxy or Cloudflare issue"
            else:
                return False, f"Error {resp.status_code}: {resp.text[:50]}"
                
        except Exception as e:
            return False, f"Connection Error: {str(e)}"

# ==========================================
# 5. MAIN ENTRY POINT
# ==========================================

@click.command()
@click.option("--config", default="config.json", help="Config file")
@click.option("--data", default="data.txt", help="Data file")
@click.option("--proxy", help="Proxy URL")
@click.option("--live", is_flag=True, help="Live Scrape Mode")
@click.option("--letters", default="A", help="Letters to scrape (Live mode)")
@click.option("--year", default="2024", help="Year to scrape (Live mode)")
@click.option("--verbose", is_flag=True, help="Verbose output")
def main(config, data, proxy, live, letters, year, verbose):
    """
    All-in-One Veterans Tool (Ubuntu 24 Compatible).
    Can Scrape Data and Check Token Validity.
    """
    ui = ConsoleUI(verbose)
    ui.print_banner()

    # 1. Load Config
    try:
        conf = ConfigManager.load(config)
        token_short = conf.get('accessToken', '')[:10] + "..."
        ui.print_info(f"Loaded config. Token: {token_short}")
    except Exception as e:
        ui.print_error(f"Config Error: {e}")
        return

    # 2. Setup Proxy
    pm = ProxyManager([proxy]) if proxy else None
    if proxy: ui.print_info(f"Using Proxy: {proxy}")

    # 3. Check Token
    ui.console.rule("[bold]Checking Access Token[/bold]")
    checker = TokenChecker(conf, pm)
    valid, msg = checker.check_token_and_create_id()
    
    if valid:
        ui.print_success(msg)
    else:
        ui.print_error(msg)
        ui.print_warning("Please update accessToken in config.json")
        if not live: return # Stop if not just scraping

    # 4. Process Data (Scrape or Load)
    ui.console.rule("[bold]Processing Data[/bold]")
    
    records = []
    
    if live:
        ui.print_info(f"Starting Live Scraper (Year: {year}, Letters: {letters})")
        scraper = VLMScraper(verbose=verbose)
        
        # Output file
        out_file = Path(f"scraped_data_{int(time.time())}.txt")
        
        with open(out_file, 'w') as f:
            # Header
            f.write(f"# Scraped Data {datetime.now()}\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=ui.console
            ) as progress:
                task = progress.add_task("Scraping...", total=None)
                
                count = 0
                for rec in scraper.scrape_by_letters(letters, year):
                    records.append(rec)
                    line = f"{rec.first_name}|{rec.last_name}|{rec.branch}|{rec.birth_date}|{rec.discharge_date}"
                    f.write(line + "\n")
                    f.flush()
                    count += 1
                    progress.update(task, description=f"Found: {count} veterans ({rec.full_name})")
                    
        ui.print_success(f"Scraping Complete. Saved {len(records)} records to {out_file}")
        
    else:
        # Load from file
        try:
            records = DataParser.parse_file(Path(data))
            ui.print_info(f"Loaded {len(records)} records from {data}")
        except Exception as e:
            ui.print_error(f"Failed to load data: {e}")

    # 5. Verification Stub
    if records and valid:
        ui.console.rule("[bold red]VERIFICATION MODULE MISSING[/bold red]")
        ui.print_warning(
            "The full auto-verification logic (SheerID submission) was located in the 'src' folder\n"
            "which is missing from your installation.\n\n"
            "This script has successfully:\n"
            "1. Verified your ChatGPT Token works.\n"
            "2. Loaded/Scraped Veteran Data.\n\n"
            "To proceed with verification, you need to manually submit this data or\n"
            "redownload the full repository using 'git clone'."
        )
        
        # Show sample data to prove it works
        table = Table(title="Sample Data Ready for Use")
        table.add_column("First Name")
        table.add_column("Last Name")
        table.add_column("Discharge")
        
        for r in records[:5]:
            table.add_row(r.first_name, r.last_name, r.discharge_date)
        
        ui.console.print(table)

if __name__ == "__main__":
    main()
