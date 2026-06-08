# Pelne demo: modul kart (repo Filipa) + UK Bank B
# Uzycie: .\scripts\start-demo.ps1 [-CardsRepoPath "sciezka\do\repo"]

param(
    [string]$CardsRepoPath = ""
)

$ErrorActionPreference = "Stop"
$BankRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $CardsRepoPath) {
    $Candidates = @(
        "$env:USERPROFILE\Documents\GitHub\karty-platnicze-temp",
        "$env:USERPROFILE\Documents\GitHub\Karty-Platnicze-Aplikacje-Biznesowe",
        (Join-Path (Split-Path -Parent $BankRoot) "Karty-Platnicze-Aplikacje-Biznesowe")
    )
    foreach ($c in $Candidates) {
        if (Test-Path (Join-Path $c "docker-compose.yaml")) {
            $CardsRepoPath = $c
            break
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  UK Bank B + Modul Kart" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path $CardsRepoPath)) {
    Write-Host ""
    Write-Host "BLAD: Nie znaleziono repo modulu kart." -ForegroundColor Red
    Write-Host "Sklonuj: git clone https://github.com/FilipSl3/Karty-Platnicze-Aplikacje-Biznesowe"
    exit 1
}

Write-Host ""
Write-Host "[1/3] Modul kart: $CardsRepoPath" -ForegroundColor Yellow
Push-Location $CardsRepoPath
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host ""
    Write-Host "BLAD uruchamiania modulu kart (czesto konflikt sieci Docker)." -ForegroundColor Red
    Write-Host "Sprobuj: docker compose down w innych projektach uzywajacych 172.20/172.21"
    Write-Host "Potem ponow: docker compose up -d w repo kart"
    exit 1
}
Pop-Location
Write-Host "      Modul kart OK (porty 8072, 3072)" -ForegroundColor Green
Start-Sleep -Seconds 10

Write-Host "[2/3] UK Bank B..." -ForegroundColor Yellow
Push-Location $BankRoot
docker compose down --remove-orphans 2>$null
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location
Write-Host "      UK Bank B OK (port 8000)" -ForegroundColor Green
Start-Sleep -Seconds 5

Write-Host "[3/3] Podlaczenie sieci capture..." -ForegroundColor Yellow
& (Join-Path $BankRoot "scripts\connect-cards-network.ps1")

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GOTOWE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Bank:       http://localhost:8000"
Write-Host "  Demo:       http://localhost:8000/demo-karty"
Write-Host "  Terminal:   http://localhost:8072/pos"
Write-Host "  Test:       python scripts\demo_test.py"
Write-Host ""

Push-Location $BankRoot
python scripts/demo_test.py
Pop-Location
