# start-wokwi.ps1
# Khoi dong Backend Flask + ngrok -> Wokwi
# Su dung: .\start-wokwi.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " He Thong Giam Sat Nhiet Do - Wokwi   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Khoi dong Flask Backend
Write-Host "[1/3] Khoi dong Flask Backend..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.\venv\Scripts\activate; python app.py" -PassThru -WindowStyle Normal
Write-Host "  -> Backend PID: $($backendJob.Id)" -ForegroundColor Green
Write-Host "  -> URL: http://127.0.0.1:5000" -ForegroundColor Green

Start-Sleep -Seconds 3

# 2. Khoi dong ngrok
Write-Host "[2/3] Khoi dong ngrok..." -ForegroundColor Yellow
$ngrokJob = Start-Process -FilePath "ngrok" -ArgumentList "http", "5000" -PassThru -WindowStyle Normal
Start-Sleep -Seconds 3

# Lay ngrok URL
try {
    $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels"
    $ngrokUrl = $tunnels.tunnels[0].public_url
    Write-Host "  -> ngrok URL: $ngrokUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "  CAP NHAT config_wokwi.h:" -ForegroundColor Magenta
    Write-Host "  const char* SERVER_URL = ""$ngrokUrl/api/sensor-data"";" -ForegroundColor White
} catch {
    Write-Host "  -> Khong lay duoc URL, kiem tra ngrok manually" -ForegroundColor Red
}

# 3. Huong dan Wokwi
Write-Host ""
Write-Host "[3/3] Huong dan Wokwi:" -ForegroundColor Yellow
Write-Host "  1. Mo https://wokwi.com -> New Project -> ESP32" -ForegroundColor White
Write-Host "  2. Copy 4 file tu firmware/wokwi/ vao project" -ForegroundColor White
Write-Host "  3. Cap nhat SERVER_URL trong sketch voi ngrok URL o tren" -ForegroundColor White
Write-Host "  4. Start Simulation -> kiem tra Serial Monitor" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Nhan Enter de dong tat ca...           " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Read-Host

# Cleanup
Write-Host "Dang dung..." -ForegroundColor Yellow
Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $ngrokJob.Id -Force -ErrorAction SilentlyContinue
Write-Host "Da dong." -ForegroundColor Green
