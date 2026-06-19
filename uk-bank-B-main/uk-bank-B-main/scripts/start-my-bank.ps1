# Uruchom TYLKO UK Bank B (+ wbudowany KLIK).
# Reszta (UKPS, karty, bank kolegi, SWIFT) powinna juz dzialac u innych w sali.
#
#   .\scripts\start-my-bank.ps1

$ErrorActionPreference = "Stop"
$BankRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host ""
Write-Host "UK Bank B — start w sali (Twoj kolej)" -ForegroundColor Cyan
Write-Host ""

& (Join-Path $BankRoot "scripts\school-ports.ps1") -Check
if ($LASTEXITCODE -ne 0) { exit 1 }

Push-Location $BankRoot
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location

Write-Host ""
Write-Host "Czekam na bank..." -ForegroundColor DarkGray
Start-Sleep -Seconds 8

$nets = docker network ls --format "{{.Name}}" 2>$null
if ($nets -contains "cards-backend") {
    Write-Host "Podlaczam siec kart (capture)..." -ForegroundColor Yellow
    & (Join-Path $BankRoot "scripts\connect-cards-network.ps1")
} else {
    Write-Host "Siec cards-backend jeszcze nie ma — zespol kart musi odpalic swoje repo." -ForegroundColor Yellow
    Write-Host "Potem recznie: .\scripts\connect-cards-network.ps1" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Twoj bank:     http://localhost:8010" -ForegroundColor Green
Write-Host "Integracje:    http://localhost:8010/integracje" -ForegroundColor Green
Write-Host "KLIK agent:    http://localhost:8175" -ForegroundColor Green
Write-Host "  klucz agenta: klik_dev_agent_uk_school_demo  strefa: UK" -ForegroundColor DarkGray
Write-Host "Postep sali:   .\scripts\school-ports.ps1 -Status" -ForegroundColor Green
Write-Host ""
