# Brazilian Chamber of Deputies PDF Archives

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

Generated on: 2025-08-16 07:00:58