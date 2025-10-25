import requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
import time
import logging
from typing import Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import settings

logger = logging.getLogger(__name__)

MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3,
    "april": 4, "mai": 5, "juni": 6, "juli": 7,
    "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}

def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=settings.max_retries,
        backoff_factor=settings.backoff_multiplier,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set proper headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    return session

def fetch_calendar_data() -> Dict[date, str]:
    """
    Scrape Opfinger Hütte calendar and return a dict of
    {date: status} for weekend slots (Friday-Saturday and Saturday-Sunday).
    Fetches multiple months to get comprehensive data.
    """
    try:
        results = {}
        today = date.today()
        
        # Fetch current month and next N months based on configuration
        for month_offset in range(settings.months_ahead):
            target_date = today + timedelta(days=30 * month_offset)
            month = target_date.month
            year = target_date.year
            
            logger.debug(f"Fetching calendar for {month}/{year}")
            
            # Build URL with month and year parameters
            url = f"{settings.base_url}&monat={month}&jahr={year}&eintrag=Kalender+anzeigen"
            
            html = _fetch_html_with_retries(url)
            if not html:
                logger.warning(f"Failed to fetch calendar for {month}/{year}")
                continue
                
            month_results = _parse_calendar_html(html, month, year)
            results.update(month_results)
            
            # Small delay between requests to be respectful
            if month_offset < 2:  # Don't delay after the last request
                time.sleep(1)
            
        logger.info(f"Found {len(results)} weekend entries across all months.")

        # Normalize the results to only free and booked to our use-case
        # Free only if place is free from mid day till next mid-day on friday and saturday
        dates = list(results.keys())
        for i in range(len(dates) - 1):
            current_date = dates[i]
            next_date = dates[i + 1]
            
            if next_date - current_date == timedelta(days=1) and \
                (results[current_date] in ['partial_rg', 'free']) and \
                (results[next_date] in ['free', 'partial_gr']):
                results[current_date] = 'free'
            else:
                results[current_date] = 'booked'

        if results[next_date] != 'free':
            results[next_date] = 'booked' 

        return results
        
    except Exception as e:
        logger.error(f"Unexpected error in fetch_calendar_data: {e}")
        return {}

def _parse_calendar_html(html: str, month: int, year: int) -> Dict[date, str]:
    """Parse calendar HTML and extract weekend availability."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        results = {}
        
        # Find all calendar tables
        calendar_tables = soup.find_all("table", style=lambda x: x and "border-collapse: collapse" in x)
        
        table = calendar_tables[0]
        try:
            # Extract month and year from the header before this table
            month_year_header = table.find_previous("b")
            if not month_year_header:
                logger.warning(f"Month header not found for {month}/{year}")
                return results
                
            month_year_text = month_year_header.get_text(strip=True)
            logger.debug(f"Processing calendar for: {month_year_text}")
            
            # Parse month and year from header
            header_month_label, header_year = _parse_month_year(month_year_text)
            
            # Use header values if available, otherwise use parameters
            if header_month_label and header_year:
                month_label = header_month_label
                year_label = header_year
            else:
                # Fallback to parameter values
                month_label = list(MONTHS.keys())[month - 1] if month in range(1, 13) else None
                year_label = year
            
            if not month_label or not year_label:
                logger.warning(f"Could not determine month/year for table")
                return results
            
            # Process calendar cells
            month_results = _process_calendar_table(table, month_label, year_label)
            results.update(month_results)
            
        except Exception as e:
            logger.warning(f"Error processing calendar table: {e}")
                
        return results
        
    except Exception as e:
        logger.error(f"Error parsing calendar HTML: {e}")
        return {}

def _parse_month_year(month_year_text: str) -> tuple[str, int]:
    """Parse month and year from header text like 'November 2025'."""
    try:
        parts = month_year_text.split()
        if len(parts) >= 2:
            month_label = parts[0].lower()
            year_label = int(parts[1])
            
            if month_label in MONTHS:
                return month_label, year_label
        return None, None
    except (ValueError, IndexError):
        return None, None

def _process_calendar_table(table, month_label: str, year_label: int) -> Dict[date, str]:
    """Process a single calendar table and extract weekend availability."""
    results = {}
    today = date.today()
    
    try:
        # Find all table cells that contain day numbers
        # cells = table.find_all("td")
        rows = table.find_all("tr", recursive=False)
        cells = []
        for row in rows:
            cells.extend(row.find_all("td", recursive=False))
        
        for cell in cells:
            try:
                # Look for day numbers in the cell
                day_links = cell.find_all("a")
                if not day_links:
                    continue
                
                # Extract day number from the first link
                day_text = day_links[0].get_text(strip=True)
                if not day_text.isdigit():
                    continue
                    
                day_num = int(day_text)
                
                # Determine status based on background color
                status = _determine_status_from_cell(cell)
                if not status:
                    continue
                
                # Create date and check if it's a weekend
                try:
                    full_date = date(year_label, MONTHS[month_label], day_num)
                except ValueError:
                    logger.warning(f"Invalid date: {year_label}-{MONTHS[month_label]}-{day_num}")
                    continue

                if full_date > today: 
                    # Check if this is a Friday or Saturday (weekend slots)
                    if full_date.weekday() in (4, 5):  # Friday=4, Saturday=5
                        results[full_date] = status
                        logger.debug(f"Found {full_date} ({full_date.strftime('%A')}): {status}")
                        
            except Exception as e:
                logger.warning(f"Error processing calendar cell: {e}")
                continue
                
    except Exception as e:
        logger.warning(f"Error processing calendar table: {e}")
        
    return results

def _determine_status_from_cell(cell) -> Optional[str]:
    """Determine availability status from a calendar cell.
    Distinguishes between red→green (partial_rg) and green→red (partial_gr).
    """
    try:
        links = cell.find_all("a")
        if not links:
            return None

        colors_in_order = []
        for link in links:
            style = link.get("style", "").lower()
            if "background: red" in style or "background-color: red" in style:
                colors_in_order.append("red")
            elif "background: green" in style or "background-color: green" in style:
                colors_in_order.append("green")

        if not colors_in_order:
            logger.debug("No color indicators found in cell")
            return None

        # Deduplicate adjacent duplicates (e.g. red, red, green -> red, green)
        simplified = []
        for c in colors_in_order:
            if not simplified or simplified[-1] != c:
                simplified.append(c)

        # Determine final status
        if len(set(simplified)) == 1:
            # Only one color present
            color = simplified[0]
            if color == "red":
                return "booked"
            elif color == "green":
                return "free"
        elif len(simplified) >= 2:
            # Mixed sequence, check order
            first, second = simplified[0], simplified[1]
            if first == "red" and second == "green":
                return "partial_rg"  # red then green
            elif first == "green" and second == "red":
                return "partial_gr"  # green then red
        else:
            return None

    except Exception as e:
        logger.warning(f"Error determining status from cell: {e}")
        return None


def _fetch_html_with_retries(url: str) -> Optional[str]:
    """
    Fetch HTML content with retries and exponential backoff.
    Returns HTML string or None if all retries fail.
    """
    session = create_session()
    
    try:
        response = session.get(url, timeout=settings.request_timeout)
        response.raise_for_status()
        logger.info(f"Fetched calendar successfully from {url}")
        return response.text
    except requests.RequestException as e:
        logger.error(f"Failed to fetch calendar: {e}")
        return None
    finally:
        session.close()
