#!/usr/bin/env python3
"""
Brazilian Chamber of Deputies PDF Scraper
Downloads PDF documents from https://imagem.camara.leg.br/pesquisa_diario_basica.asp
"""

import os
import re
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bs4 import BeautifulSoup
from tqdm import tqdm


@dataclass
class Config:
    """Configuration for the scraper"""
    years_back: int = 2
    max_threads: int = 40
    base_url: str = 'https://imagem.camara.leg.br/'
    download_dir: str = './downloads'
    retry_attempts: int = 3
    retry_delay: float = 1.0
    request_timeout: int = 15
    rate_limit_delay: float = 0.02
    user_agent: str = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'


class ProgressTracker:
    """Tracks download progress and saves state"""
    
    def __init__(self, progress_file: str = 'download_progress.json'):
        self.progress_file = progress_file
        self.data = self.load_progress()
        
    def load_progress(self) -> Dict:
        """Load existing progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {'completed_dates': [], 'failed_downloads': [], 'stats': {}}
    
    def save_progress(self):
        """Save current progress to file"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            logging.error(f"Failed to save progress: {e}")
    
    def is_date_completed(self, date_key: str) -> bool:
        """Check if a date has been completed"""
        return date_key in self.data.get('completed_dates', [])
    
    def mark_date_completed(self, date_key: str):
        """Mark a date as completed"""
        if 'completed_dates' not in self.data:
            self.data['completed_dates'] = []
        if date_key not in self.data['completed_dates']:
            self.data['completed_dates'].append(date_key)
    
    def add_failed_download(self, url: str, error: str):
        """Add a failed download"""
        if 'failed_downloads' not in self.data:
            self.data['failed_downloads'] = []
        self.data['failed_downloads'].append({
            'url': url,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
    
    def update_stats(self, key: str, value: int):
        """Update statistics"""
        if 'stats' not in self.data:
            self.data['stats'] = {}
        self.data['stats'][key] = self.data['stats'].get(key, 0) + value


class CamaraDownloader:
    """Main downloader class for Brazilian Chamber of Deputies PDFs"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.user_agent})
        
        # Configure connection pool with custom adapter
        adapter = HTTPAdapter(
            pool_connections=60,        # Number of connection pools (higher than threads)
            pool_maxsize=75,           # Max connections per pool  
            max_retries=3,             # Built-in retry logic
            pool_block=False           # Don't block when pool is full
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.progress = ProgressTracker()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('camara_downloader.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create download directory
        Path(self.config.download_dir).mkdir(parents=True, exist_ok=True)
    
    def log_failed_download_details(self, pdf_url: str, date_str: str, error: str):
        """Enhanced logging for failed downloads with detailed date extraction"""
        try:
            # Extract date parts from date_str (format: DD/MM/YYYY)
            day, month, year = date_str.split('/')
            month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                          'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            month_name = month_names[int(month) - 1]
            
            self.logger.error("=" * 80)
            self.logger.error(f"FAILED DOWNLOAD - MANUAL INTERVENTION REQUIRED")
            self.logger.error(f"Date: {day}/{month}/{year} ({day} {month_name} {year})")
            self.logger.error(f"Year: {year}")
            self.logger.error(f"Month: {month_name} ({month})")
            self.logger.error(f"Day: {day}")
            self.logger.error(f"PDF URL: {pdf_url}")
            self.logger.error(f"Error: {error}")
            self.logger.error("=" * 80)
        except Exception as e:
            self.logger.error(f"Failed to parse date {date_str} for failed download: {e}")
            self.logger.error(f"Raw date string: {date_str}")
            self.logger.error(f"Failed URL: {pdf_url}")
    
    def get_available_years(self) -> List[int]:
        """Extract available years from the main page"""
        try:
            url = urljoin(self.config.base_url, 'pesquisa_diario_basica.asp')
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find year options in the page
            year_pattern = re.compile(r'\b(19|20)\d{2}\b')
            years = set()
            
            # Look for year patterns in the HTML content
            for match in year_pattern.finditer(response.text):
                year = int(match.group())
                if 1881 <= year <= datetime.now().year:
                    years.add(year)
            
            # Filter years based on configuration
            current_year = datetime.now().year
            start_year = current_year - self.config.years_back
            filtered_years = [y for y in sorted(years) if y >= start_year]
            
            self.logger.info(f"Found {len(filtered_years)} years to process: {filtered_years}")
            return filtered_years
            
        except Exception as e:
            self.logger.error(f"Failed to get available years: {e}")
            return []
    
    def get_year_calendar(self, year: int) -> List[Tuple[str, str]]:
        """Get all available date links for a specific year"""
        try:
            url = urljoin(self.config.base_url, f'pesquisa_diario_basica.asp?ano={year}')
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            date_links = []
            
            # Find all links with the date pattern
            for link in soup.find_all('a', class_='WeekDay'):
                href = link.get('href', '')
                if 'dc_20b.asp' in href and 'Datain=' in href:
                    # Extract date from href
                    date_match = re.search(r'Datain=(\d+/\d+/\d+)', href)
                    if date_match:
                        date_str = date_match.group(1)
                        full_url = urljoin(self.config.base_url, href)
                        date_links.append((date_str, full_url))
            
            self.logger.info(f"Found {len(date_links)} dates for year {year}")
            return date_links
            
        except Exception as e:
            self.logger.error(f"Failed to get calendar for year {year}: {e}")
            return []
    
    def resolve_pdf_url(self, date_url: str) -> Optional[str]:
        """Follow a date link to get the actual PDF URL"""
        try:
            response = self.session.get(date_url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for PDF links in the response
            pdf_patterns = [
                r'https://imagem\.camara\.gov\.br/Imagem/d/pdf/[^"]+\.PDF',
                r'/Imagem/d/pdf/[^"]+\.PDF'
            ]
            
            for pattern in pdf_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    pdf_url = matches[0]
                    if not pdf_url.startswith('http'):
                        pdf_url = 'https://imagem.camara.gov.br' + pdf_url
                    return pdf_url
            
            # Alternative: look for specific link elements
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if '.PDF' in href.upper():
                    if not href.startswith('http'):
                        href = 'https://imagem.camara.gov.br' + href
                    return href
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to resolve PDF URL from {date_url}: {e}")
            return None
    
    def download_pdf(self, pdf_url: str, date_str: str, year: int) -> bool:
        """Download a single PDF file"""
        try:
            # Create directory structure
            date_parts = date_str.split('/')
            if len(date_parts) == 3:
                day, month, year_str = date_parts
                month_names = [
                    '01_Janeiro', '02_Fevereiro', '03_Março', '04_Abril',
                    '05_Maio', '06_Junho', '07_Julho', '08_Agosto',
                    '09_Setembro', '10_Outubro', '11_Novembro', '12_Dezembro'
                ]
                month_dir = month_names[int(month) - 1]
                
                save_dir = Path(self.config.download_dir) / str(year) / month_dir
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # Extract filename from URL
                filename = os.path.basename(urlparse(pdf_url).path)
                if not filename.endswith('.PDF'):
                    filename += '.PDF'
                
                save_path = save_dir / filename
                
                # Skip if file already exists
                if save_path.exists():
                    self.logger.debug(f"File already exists: {save_path}")
                    return True
                
                # Download with retry logic
                for attempt in range(self.config.retry_attempts):
                    try:
                        response = self.session.get(pdf_url, timeout=self.config.request_timeout, stream=True)
                        response.raise_for_status()
                        
                        with open(save_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=65536):
                                if chunk:
                                    f.write(chunk)
                        
                        self.logger.info(f"Downloaded: {filename}")
                        self.progress.update_stats('downloads_completed', 1)
                        return True
                        
                    except Exception as e:
                        self.logger.warning(f"Download attempt {attempt + 1} failed for {pdf_url}: {e}")
                        if attempt < self.config.retry_attempts - 1:
                            time.sleep(self.config.retry_delay * (2 ** attempt))
                        else:
                            self.log_failed_download_details(pdf_url, date_str, str(e))
                            self.progress.add_failed_download(pdf_url, str(e))
                            self.progress.update_stats('downloads_failed', 1)
                            return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to download PDF {pdf_url}: {e}")
            self.progress.add_failed_download(pdf_url, str(e))
            self.progress.update_stats('downloads_failed', 1)
            return False
    
    def process_date_batch(self, date_batch: List[Tuple[str, str]], year: int) -> int:
        """Process a batch of dates concurrently"""
        successful_downloads = 0
        
        with ThreadPoolExecutor(max_workers=self.config.max_threads) as executor:
            # Submit all date processing tasks
            future_to_date = {}
            for date_str, date_url in date_batch:
                date_key = f"{year}_{date_str}"
                
                if self.progress.is_date_completed(date_key):
                    self.logger.debug(f"Skipping completed date: {date_str}")
                    continue
                
                future = executor.submit(self._process_single_date, date_str, date_url, year)
                future_to_date[future] = (date_str, date_key)
            
            # Process completed futures
            for future in as_completed(future_to_date):
                date_str, date_key = future_to_date[future]
                try:
                    success = future.result()
                    if success:
                        successful_downloads += 1
                        self.progress.mark_date_completed(date_key)
                    
                    # Add small delay between requests
                    time.sleep(self.config.rate_limit_delay)
                    
                except Exception as e:
                    self.logger.error(f"Error processing date {date_str}: {e}")
        
        return successful_downloads
    
    def _process_single_date(self, date_str: str, date_url: str, year: int) -> bool:
        """Process a single date (resolve PDF URL and download)"""
        try:
            pdf_url = self.resolve_pdf_url(date_url)
            if pdf_url:
                return self.download_pdf(pdf_url, date_str, year)
            else:
                self.logger.warning(f"No PDF found for date {date_str}")
                return False
        except Exception as e:
            self.logger.error(f"Error processing date {date_str}: {e}")
            return False
    
    def run(self):
        """Main execution method"""
        self.logger.info("Starting Brazilian Chamber of Deputies PDF scraper")
        
        # Get available years
        years = self.get_available_years()
        if not years:
            self.logger.error("No years found to process")
            return
        
        total_downloads = 0
        
        # Process years from oldest to newest
        for year in sorted(years):
            self.logger.info(f"Processing year {year}")
            
            # Get all dates for this year
            date_links = self.get_year_calendar(year)
            if not date_links:
                self.logger.warning(f"No dates found for year {year}")
                continue
            
            # Process dates in batches
            batch_size = 100  # Process 100 dates at a time (doubled for speed)
            for i in range(0, len(date_links), batch_size):
                batch = date_links[i:i + batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1} for year {year} ({len(batch)} dates)")
                
                batch_downloads = self.process_date_batch(batch, year)
                total_downloads += batch_downloads
                
                # Save progress after each batch
                self.progress.save_progress()
                
                self.logger.info(f"Batch completed. Downloaded {batch_downloads} files")
        
        # Final statistics
        self.logger.info(f"Scraping completed! Total downloads: {total_downloads}")
        self.logger.info(f"Failed downloads: {self.progress.data.get('stats', {}).get('downloads_failed', 0)}")
        self.progress.save_progress()


def main():
    """Main entry point"""
    config = Config()
    
    # Allow configuration override from command line or environment
    import sys
    if len(sys.argv) > 1:
        try:
            config.years_back = int(sys.argv[1])
        except ValueError:
            print("Invalid years_back argument. Using default: 2")
    
    if len(sys.argv) > 2:
        try:
            config.max_threads = int(sys.argv[2])
        except ValueError:
            print("Invalid max_threads argument. Using default: 15")
    
    print(f"Configuration:")
    print(f"  Years back: {config.years_back}")
    print(f"  Max threads: {config.max_threads}")
    print(f"  Download directory: {config.download_dir}")
    print()
    
    downloader = CamaraDownloader(config)
    downloader.run()


if __name__ == "__main__":
    main()
