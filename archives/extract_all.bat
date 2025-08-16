@echo off
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
