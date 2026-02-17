# Start Backend Script
Write-Host "🚀 Uruchamianie Backend FastAPI..." -ForegroundColor Green
Write-Host ""

$projectPath = "E:\Polish Footballers Abroad Tracker\polish-players-tracker"
$pythonExe = "$projectPath\.venv\Scripts\python.exe"

# Zmień katalog
Set-Location $projectPath

# Sprawdź czy Python istnieje
if (-Not (Test-Path $pythonExe)) {
    Write-Host "❌ Błąd: Nie znaleziono Pythona w .venv" -ForegroundColor Red
    Write-Host "Uruchom najpierw: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Uruchom backend
Write-Host "📡 Backend będzie dostępny na: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "📚 Dokumentacja API: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Naciśnij Ctrl+C aby zatrzymać serwer" -ForegroundColor Yellow
Write-Host ""

& $pythonExe -m uvicorn app.backend.main:app --reload --port 8000 --no-access-log
