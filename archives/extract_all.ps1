# Brazilian Chamber of Deputies PDF Extractor (PowerShell)
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
