#!/usr/bin/env python3
"""
Compress downloaded PDFs by month for GitHub upload and Windows compatibility
Creates ZIP files organized by year and month, with Windows extraction tools
"""

import os
import zipfile
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import logging

class DownloadCompressor:
    """Compresses downloaded PDFs into monthly ZIP archives"""
    
    def __init__(self, downloads_dir: str = './downloads', archives_dir: str = './archives'):
        self.downloads_dir = Path(downloads_dir)
        self.archives_dir = Path(archives_dir)
        self.archives_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('compression.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'total_size_original': 0,
            'total_size_compressed': 0,
            'archives_created': 0,
            'compression_ratio': 0.0
        }
    
    def get_file_hash(self, filepath: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def compress_month(self, year: int, month: int) -> Tuple[bool, Dict]:
        """Compress all PDFs for a specific year/month into a ZIP file"""
        month_dir = self.downloads_dir / str(year) / f"{month:02d}"
        
        if not month_dir.exists():
            self.logger.warning(f"Month directory does not exist: {month_dir}")
            return False, {}
        
        # Create year directory in archives
        year_archive_dir = self.archives_dir / str(year)
        year_archive_dir.mkdir(exist_ok=True)
        
        # ZIP filename
        zip_filename = f"{year}-{month:02d}.zip"
        zip_path = year_archive_dir / zip_filename
        
        # Skip if already exists
        if zip_path.exists():
            self.logger.info(f"Archive already exists: {zip_path}")
            return True, {'skipped': True, 'path': str(zip_path)}
        
        # Collect all PDF files for this month
        pdf_files = []
        original_size = 0
        
        for day_dir in sorted(month_dir.iterdir()):
            if day_dir.is_dir():
                for pdf_file in day_dir.glob("*.PDF"):
                    pdf_files.append(pdf_file)
                    original_size += pdf_file.stat().st_size
        
        if not pdf_files:
            self.logger.warning(f"No PDF files found for {year}-{month:02d}")
            return False, {}
        
        # Create ZIP archive with maximum compression
        self.logger.info(f"Compressing {len(pdf_files)} files for {year}-{month:02d}...")
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                for pdf_file in pdf_files:
                    # Preserve directory structure within ZIP
                    # Structure: year/month/day/filename.PDF
                    relative_path = pdf_file.relative_to(self.downloads_dir)
                    zipf.write(pdf_file, relative_path)
            
            compressed_size = zip_path.stat().st_size
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            # Update statistics
            self.stats['total_files'] += len(pdf_files)
            self.stats['total_size_original'] += original_size
            self.stats['total_size_compressed'] += compressed_size
            self.stats['archives_created'] += 1
            
            self.logger.info(f"Created {zip_filename}: {len(pdf_files)} files, "
                           f"{original_size / (1024*1024):.1f}MB → {compressed_size / (1024*1024):.1f}MB "
                           f"({compression_ratio:.1f}% compression)")
            
            # Create manifest entry
            manifest_entry = {
                'archive': zip_filename,
                'year': year,
                'month': month,
                'file_count': len(pdf_files),
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'created_date': datetime.now().isoformat(),
                'sha256': self.get_file_hash(zip_path)
            }
            
            return True, manifest_entry
            
        except Exception as e:
            self.logger.error(f"Failed to create archive {zip_filename}: {e}")
            if zip_path.exists():
                zip_path.unlink()  # Clean up partial file
            return False, {}
    
    def compress_year(self, year: int) -> List[Dict]:
        """Compress all months for a specific year"""
        year_dir = self.downloads_dir / str(year)
        
        if not year_dir.exists():
            self.logger.warning(f"Year directory does not exist: {year_dir}")
            return []
        
        self.logger.info(f"Processing year {year}...")
        
        year_manifest = []
        
        # Process each month
        for month in range(1, 13):
            success, manifest_entry = self.compress_month(year, month)
            if success and manifest_entry:
                year_manifest.append(manifest_entry)
        
        # Save year manifest
        if year_manifest:
            manifest_path = self.archives_dir / f"{year}-manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(year_manifest, f, indent=2)
            self.logger.info(f"Saved manifest: {manifest_path}")
        
        return year_manifest
    
    def compress_all(self) -> Dict:
        """Compress all available years"""
        self.logger.info("Starting compression of all downloads...")
        
        # Find all year directories
        years = []
        for item in self.downloads_dir.iterdir():
            if item.is_dir() and item.name.isdigit():
                years.append(int(item.name))
        
        years.sort()
        self.logger.info(f"Found years to process: {years}")
        
        all_manifests = {}
        
        # Process each year
        for year in years:
            year_manifest = self.compress_year(year)
            if year_manifest:
                all_manifests[year] = year_manifest
        
        # Calculate final statistics
        if self.stats['total_size_original'] > 0:
            self.stats['compression_ratio'] = (1 - self.stats['total_size_compressed'] / self.stats['total_size_original']) * 100
        
        # Save master manifest
        master_manifest = {
            'created_date': datetime.now().isoformat(),
            'statistics': self.stats,
            'years': all_manifests
        }
        
        master_manifest_path = self.archives_dir / 'master-manifest.json'
        with open(master_manifest_path, 'w') as f:
            json.dump(master_manifest, f, indent=2)
        
        self.logger.info("Compression completed!")
        self.logger.info(f"Statistics:")
        self.logger.info(f"  Total files: {self.stats['total_files']:,}")
        self.logger.info(f"  Original size: {self.stats['total_size_original'] / (1024**3):.2f} GB")
        self.logger.info(f"  Compressed size: {self.stats['total_size_compressed'] / (1024**3):.2f} GB")
        self.logger.info(f"  Compression ratio: {self.stats['compression_ratio']:.1f}%")
        self.logger.info(f"  Archives created: {self.stats['archives_created']}")
        
        return master_manifest
    
    def create_windows_tools(self):
        """Create Windows-compatible extraction tools"""
        self.logger.info("Creating Windows extraction tools...")
        
        # Create batch script for extraction
        batch_script = '''@echo off
echo ========================================
echo Brazilian Chamber of Deputies PDF Extractor
echo ========================================
echo.
echo This script will extract all ZIP archives to recreate the original folder structure.
echo.
pause

echo Starting extraction...
echo.

for /r %%i in (*.zip) do (
    echo Extracting %%~nxi...
    powershell -command "try { Expand-Archive -Path '%%i' -DestinationPath './extracted' -Force; Write-Host 'Success: %%~nxi' -ForegroundColor Green } catch { Write-Host 'Error extracting %%~nxi: $_' -ForegroundColor Red }"
)

echo.
echo ========================================
echo Extraction completed!
echo Files have been extracted to the 'extracted' folder.
echo ========================================
pause
'''
        
        batch_path = self.archives_dir / 'extract_all.bat'
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_script)
        
        # Create PowerShell script with progress
        powershell_script = '''# Brazilian Chamber of Deputies PDF Extractor (PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Brazilian Chamber of Deputies PDF Extractor" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$zipFiles = Get-ChildItem -Recurse -Filter "*.zip"
$totalFiles = $zipFiles.Count

if ($totalFiles -eq 0) {
    Write-Host "No ZIP files found!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "Found $totalFiles ZIP archives to extract." -ForegroundColor Green
Write-Host ""

$extractPath = "./extracted"
if (!(Test-Path $extractPath)) {
    New-Item -ItemType Directory -Path $extractPath | Out-Null
}

$current = 0
foreach ($zipFile in $zipFiles) {
    $current++
    $percent = [math]::Round(($current / $totalFiles) * 100, 1)
    
    Write-Progress -Activity "Extracting Archives" -Status "Processing $($zipFile.Name)" -PercentComplete $percent
    Write-Host "[$current/$totalFiles] Extracting $($zipFile.Name)..." -ForegroundColor Yellow
    
    try {
        Expand-Archive -Path $zipFile.FullName -DestinationPath $extractPath -Force
        Write-Host "  ✓ Success" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
    }
}

Write-Progress -Activity "Extracting Archives" -Completed
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Extraction completed!" -ForegroundColor Cyan
Write-Host "Files have been extracted to the 'extracted' folder." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Read-Host "Press Enter to exit"
'''
        
        ps_path = self.archives_dir / 'extract_all.ps1'
        with open(ps_path, 'w', encoding='utf-8') as f:
            f.write(powershell_script)
        
        # Create README for Windows users
        readme_content = '''# Brazilian Chamber of Deputies PDF Archives

This folder contains compressed PDF archives of Brazilian Chamber of Deputies documents organized by year and month.

## File Structure
- Each ZIP file is named: YYYY-MM.zip (e.g., 1992-01.zip for January 1992)
- Archives are organized in year folders: /1992/, /1993/, etc.
- Each archive preserves the original folder structure: year/month/day/

## Extraction Options

### Option 1: Automatic Extraction (Recommended)
Double-click `extract_all.bat` to automatically extract all archives.

### Option 2: PowerShell with Progress Bar
Right-click `extract_all.ps1` → "Run with PowerShell"

### Option 3: Manual Extraction
Right-click any ZIP file → "Extract All..." → Choose destination

## System Requirements
- Windows 7 or later (built-in ZIP support)
- PowerShell 5.0+ (for advanced extraction script)
- Sufficient disk space (see master-manifest.json for size requirements)

## File Verification
Each archive includes SHA-256 checksums in the manifest files for integrity verification.

## Archive Contents
- 1992-01.zip through 1992-12.zip: January through December 1992
- 1993-01.zip through 1993-12.zip: January through December 1993
- ... and so on for each year

## Support
For issues or questions, refer to the compression.log file or the GitHub repository.

Generated on: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        readme_path = self.archives_dir / 'README.txt'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        self.logger.info("Windows tools created:")
        self.logger.info(f"  - {batch_path}")
        self.logger.info(f"  - {ps_path}")
        self.logger.info(f"  - {readme_path}")


def main():
    """Main entry point"""
    import sys
    
    downloads_dir = './downloads'
    archives_dir = './archives'
    
    # Allow custom directories from command line
    if len(sys.argv) > 1:
        downloads_dir = sys.argv[1]
    if len(sys.argv) > 2:
        archives_dir = sys.argv[2]
    
    print(f"Compressing downloads from: {downloads_dir}")
    print(f"Creating archives in: {archives_dir}")
    print()
    
    compressor = DownloadCompressor(downloads_dir, archives_dir)
    
    # Compress all downloads
    manifest = compressor.compress_all()
    
    # Create Windows extraction tools
    compressor.create_windows_tools()
    
    print("\nCompression completed successfully!")
    print(f"Archives created in: {archives_dir}")
    print("Windows extraction tools have been created.")


if __name__ == "__main__":
    main()
