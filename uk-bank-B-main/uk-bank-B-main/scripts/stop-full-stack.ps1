# Zatrzymuje wszystkie repozytoria pelnego stacku (w odwrotnej kolejnosci).
param(
    [string]$UkpsRepoPath = "",
    [string]$CardsRepoPath = "",
    [string]$PeerBankPath = "",
    [string]$SwiftRepoPath = "",
    [switch]$SkipSwift,
    [switch]$SkipPeer
)

$ErrorActionPreference = "Continue"
$BankRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Parent = Split-Path $BankRoot

function Find-Compose {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path $Path)) { return $null }
    foreach ($m in @("docker-compose.yml", "docker-compose.yaml", "compose.yml")) {
        if (Test-Path (Join-Path $Path $m)) { return $m }
    }
    return $null
}

if (-not $UkpsRepoPath)   { $p = Join-Path $Parent "uk-payment-systems"; if (Test-Path $p) { $UkpsRepoPath = $p } }
if (-not $CardsRepoPath)  { $p = Join-Path $Parent "Karty-Platnicze-Aplikacje-Biznesowe"; if (Test-Path $p) { $CardsRepoPath = $p } }
if (-not $PeerBankPath)   { $p = Join-Path $Parent "uk-bank-system"; if (Test-Path $p) { $PeerBankPath = $p } }
if (-not $SwiftRepoPath)  { $p = Join-Path $Parent "SWIFT-Aplikacje-Biznesowe"; if (Test-Path $p) { $SwiftRepoPath = $p } }

Write-Host "Zatrzymywanie pelnego stacku..." -ForegroundColor Cyan

Push-Location $BankRoot; docker compose down; Pop-Location

if (-not $SkipSwift -and $SwiftRepoPath) {
    $c = Find-Compose $SwiftRepoPath
    if ($c) { Push-Location $SwiftRepoPath; docker compose -f $c down; Pop-Location }
}
if (-not $SkipPeer -and $PeerBankPath) {
    $c = Find-Compose $PeerBankPath
    if ($c) { Push-Location $PeerBankPath; docker compose -f $c down; Pop-Location }
}
if ($CardsRepoPath) {
    $c = Find-Compose $CardsRepoPath
    if ($c) { Push-Location $CardsRepoPath; docker compose -f $c down; Pop-Location }
}
if ($UkpsRepoPath) {
    $c = Find-Compose $UkpsRepoPath
    if ($c) { Push-Location $UkpsRepoPath; docker compose -f $c down; Pop-Location }
}

Write-Host "Gotowe." -ForegroundColor Green
