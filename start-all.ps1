# QuteMail - Start All Services

Write-Host "================================" -ForegroundColor Cyan
Write-Host "🔐 Starting QuteMail Services" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check if km-service exists
if (-not (Test-Path "km-service")) {
    Write-Host "❌ km-service directory not found!" -ForegroundColor Red
    exit 1
}

# Start KM Service
Write-Host "`n📡 Starting KM Service (Port 5001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd km-service; python app.py" -WindowStyle Normal

Start-Sleep -Seconds 3

# Test KM Service
Write-Host "`n🧪 Testing KM Service..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5001/api/v1/status" -Method Get -TimeoutSec 5
    Write-Host "✅ KM Service is running!" -ForegroundColor Green
    Write-Host "   Service: $($response.service)" -ForegroundColor Gray
    Write-Host "   Version: $($response.version)" -ForegroundColor Gray
} catch {
    Write-Host "⚠️  KM Service health check failed. Continuing anyway..." -ForegroundColor Yellow
}

# Start Django Backend
Write-Host "`n🐍 Starting Django Backend (Port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python manage.py runserver" -WindowStyle Normal

Start-Sleep -Seconds 3

# Start React Frontend
Write-Host "`n⚛️  Starting React Frontend (Port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd client; npm run dev" -WindowStyle Normal

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "✅ All services started!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services running:" -ForegroundColor White
Write-Host "  🔐 KM Service:  http://localhost:5001" -ForegroundColor Gray
Write-Host "  🐍 Backend:     http://localhost:8000" -ForegroundColor Gray
Write-Host "  ⚛️  Frontend:    http://localhost:5173" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to close all services..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host "`nStopping all services..." -ForegroundColor Red
Get-Process | Where-Object {$_.ProcessName -eq "python" -or $_.ProcessName -eq "node"} | Stop-Process -Force
Write-Host "✅ All services stopped." -ForegroundColor Green
