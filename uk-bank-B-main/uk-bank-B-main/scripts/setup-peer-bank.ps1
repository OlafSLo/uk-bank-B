# Przygotowanie srodowiska pod bank kolegi (uk-bank-system) BEZ edycji ich repo.
# Uruchom w PowerShell z folderu uk-bank-B-main/uk-bank-B-main:
#   .\scripts\setup-peer-bank.ps1
#   .\scripts\setup-peer-bank.ps1 -PeerBankPath "C:\Users\olisz\uk-bank-system"

param(
    [string]$PeerBankPath = ""
)

$ErrorActionPreference = "Stop"

Write-Host "=== Przygotowanie integracji z uk-bank-system (Alice Bank) ===" -ForegroundColor Cyan

# 1. Siec cards-backend (wymagana przez docker-compose kolegi — external network)
$networks = docker network ls --format "{{.Name}}" 2>$null
if ($networks -notcontains "cards-backend") {
    Write-Host "Tworze siec Docker: cards-backend ..." -ForegroundColor Yellow
    docker network create cards-backend | Out-Null
    Write-Host "OK: cards-backend utworzona." -ForegroundColor Green
} else {
    Write-Host "OK: siec cards-backend juz istnieje." -ForegroundColor Green
}

# 2. Plik .env u kolegi (kopiujemy .env.example -> .env jesli brak)
if (-not $PeerBankPath) {
    $candidates = @(
        "$env:USERPROFILE\uk-bank-system",
        "C:\Users\olisz\uk-bank-system",
        (Join-Path (Split-Path (Split-Path $PSScriptRoot)) "..\..\uk-bank-system")
    )
    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c "docker-compose.yml")) {
            $PeerBankPath = (Resolve-Path $c).Path
            break
        }
    }
}

if ($PeerBankPath -and (Test-Path $PeerBankPath)) {
    $envFile = Join-Path $PeerBankPath ".env"
    $example = Join-Path $PeerBankPath ".env.example"
    if (-not (Test-Path $envFile) -and (Test-Path $example)) {
        Copy-Item $example $envFile
        # Backend kolegi jest na porcie 8001 (mapowanie w ich docker-compose)
        (Get-Content $envFile) -replace 'VITE_API_URL=http://localhost:8000', 'VITE_API_URL=http://localhost:8001' |
            Set-Content $envFile -Encoding UTF8
        Write-Host "OK: utworzono $envFile (z .env.example, VITE_API_URL=8001)" -ForegroundColor Green
    } elseif (Test-Path $envFile) {
        Write-Host "OK: .env u kolegi juz istnieje: $envFile" -ForegroundColor Green
    } else {
        Write-Host "UWAGA: Brak .env.example w $PeerBankPath" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Teraz uruchom bank kolegi:" -ForegroundColor Cyan
    Write-Host "  cd `"$PeerBankPath`"" -ForegroundColor White
    Write-Host "  docker compose up -d --build" -ForegroundColor White
    Write-Host "  docker exec uk-bank-system-backend-1 python manage.py migrate" -ForegroundColor White
    Write-Host "  docker compose restart ukps-listener" -ForegroundColor White
    Write-Host ""
    Write-Host "W .env kolegi dodaj (odbior FPS na konto Olafa):" -ForegroundColor Yellow
    Write-Host "  UKPS_INBOUND_FALLBACK_ACCOUNT=01246624" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "Nie znaleziono folderu uk-bank-system." -ForegroundColor Yellow
    Write-Host "Recznie:" -ForegroundColor Cyan
    Write-Host "  cd C:\Users\olisz\uk-bank-system" -ForegroundColor White
    Write-Host "  copy .env.example .env" -ForegroundColor White
    Write-Host "  (w .env ustaw VITE_API_URL=http://localhost:8001)" -ForegroundColor White
    Write-Host "  docker compose up -d --build" -ForegroundColor White
}

Write-Host ""
Write-Host "Mapa portow (bez kolizji):" -ForegroundColor Cyan
Write-Host "  UK Bank B (Ty)     -> http://localhost:8010"
Write-Host "  Alice Bank API     -> http://localhost:8001"
Write-Host "  Alice Bank GUI     -> http://localhost:5173"
Write-Host "  UKPS CHAPS/FPS/BACS-> 8420 / 8421 / 8422"
Write-Host ""
Write-Host "Test przelewu do kolegi:" -ForegroundColor Cyan
Write-Host "  python scripts\test_peer_bank_e2e.py" -ForegroundColor White
