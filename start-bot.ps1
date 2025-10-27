# ExpoBeton Rasa Bot Startup Script
# Run this script to start both the action server and the bot

Write-Host "Starting ExpoBeton Rasa Bot..." -ForegroundColor Cyan

# Check if license is set
if (-not $env:RASA_PRO_LICENSE) {
    Write-Host "`nERROR: RASA_PRO_LICENSE environment variable not set!" -ForegroundColor Red
    Write-Host "`nPlease run one of the following:" -ForegroundColor Yellow
    Write-Host "1. Set it in Windows Environment Variables (persists across restarts)" -ForegroundColor Yellow
    Write-Host "   - Press Win + R, type 'sysdm.cpl', press Enter" -ForegroundColor White
    Write-Host "   - Go to 'Advanced' tab -> 'Environment Variables'" -ForegroundColor White
    Write-Host "   - Add 'RASA_PRO_LICENSE' with your license key" -ForegroundColor White
    Write-Host "`n2. Or set it temporarily in this session:" -ForegroundColor Yellow
    Write-Host "   `$env:RASA_PRO_LICENSE = 'YOUR_LICENSE_KEY_HERE'" -ForegroundColor White
    Write-Host "`n3. Or request a new free trial license:" -ForegroundColor Yellow
    Write-Host "   uv run rasa init license --trial" -ForegroundColor White
    exit 1
}

Write-Host "`n✓ License found!" -ForegroundColor Green

# Start action server in background
Write-Host "`nStarting action server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\python.exe -m rasa_sdk --actions actions"

# Wait a bit for action server to start
Start-Sleep -Seconds 5

# Start the bot
Write-Host "Starting bot..." -ForegroundColor Cyan
uv run rasa shell --model models\expobeton-fallback.tar.gz --port 5023
