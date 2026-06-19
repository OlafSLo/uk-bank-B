# Opcjonalnie: jedna osoba odpala caly ekosystem (dom / cwiczenie solo).
# W sali kazdy odpala swoje repo — patrz start-my-bank.ps1 i school-ports.ps1 -Status

param(
    [string]$UkpsRepoPath = "",
    [string]$CardsRepoPath = "",
    [string]$PeerBankPath = "",
    [string]$SwiftRepoPath = "",
    [switch]$SkipSwift,
    [switch]$SkipPeer,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
$BankRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Scripts = Join-Path $BankRoot "scripts"

function Find-Repo {
    param([string[]]$Candidates, [string[]]$Markers = @("docker-compose.yml", "docker-compose.yaml", "compose.yml"))
    foreach ($c in $Candidates) {
        if (-not $c) { continue }
        $resolved = $null
        try { $resolved = Resolve-Path $c -ErrorAction SilentlyContinue } catch {}
        if (-not $resolved) { continue }
        foreach ($m in $Markers) {
            if (Test-Path (Join-Path $resolved $m)) {
                return @{ Path = $resolved.Path; Compose = $m }
            }
        }
    }
    return $null
}

function Invoke-ComposeUp {
    param([hashtable]$Repo, [string]$Label)
    $buildFlag = if ($NoBuild) { "" } else { "--build" }
    Push-Location $Repo.Path
    Write-Host "      $Label : $($Repo.Path)" -ForegroundColor DarkGray
    if ($buildFlag) {
        docker compose -f $Repo.Compose up --build -d
    } else {
        docker compose -f $Repo.Compose up -d
    }
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "docker compose failed for $Label"
    }
    Pop-Location
}

function Wait-HttpOk {
    param([string]$Url, [int]$TimeoutSec = 180, [string]$Name = $Url)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
                Write-Host "      OK: $Name" -ForegroundColor Green
                return $true
            }
        } catch {}
        Start-Sleep -Seconds 3
    }
    Write-Host "      UWAGA: timeout — $Name ($Url)" -ForegroundColor Yellow
    return $false
}

function Ensure-PeerEnv {
    param([string]$Path)
    $envFile = Join-Path $Path ".env"
    $example = Join-Path $Path ".env.example"
    if (-not (Test-Path $envFile) -and (Test-Path $example)) {
        Copy-Item $example $envFile
    }
    if (-not (Test-Path $envFile)) { return }
    $content = Get-Content $envFile -Raw
    $content = $content -replace 'VITE_API_URL=http://localhost:8000', 'VITE_API_URL=http://localhost:8001'
    if ($content -notmatch 'UKPS_INBOUND_FALLBACK_ACCOUNT=\S') {
        $content = $content.TrimEnd() + "`nUKPS_INBOUND_FALLBACK_ACCOUNT=01246624`n"
    }
    Set-Content $envFile $content.TrimEnd() -Encoding UTF8 -NoNewline
    Add-Content $envFile "" -Encoding UTF8
}

$Parent = Split-Path $BankRoot

# --- autowykrywanie repozytoriow ---
if (-not $UkpsRepoPath) {
    $found = Find-Repo @(
        (Join-Path $Parent "uk-payment-systems"),
        "$env:USERPROFILE\uk-payment-systems",
        "$env:USERPROFILE\Documents\GitHub\uk-payment-systems"
    )
    if ($found) { $UkpsRepoPath = $found.Path }
}
if (-not $CardsRepoPath) {
    $found = Find-Repo @(
        (Join-Path $Parent "Karty-Platnicze-Aplikacje-Biznesowe"),
        "$env:USERPROFILE\Documents\GitHub\Karty-Platnicze-Aplikacje-Biznesowe",
        "$env:USERPROFILE\Documents\GitHub\karty-platnicze-temp"
    )
    if ($found) { $CardsRepoPath = $found.Path }
}
if (-not $PeerBankPath) {
    $found = Find-Repo @(
        (Join-Path $Parent "uk-bank-system"),
        (Join-Path (Split-Path $Parent) "uk-bank-system"),
        "$env:USERPROFILE\uk-bank-system",
        "C:\Users\olisz\uk-bank-system"
    )
    if ($found) { $PeerBankPath = $found.Path }
}
if (-not $SwiftRepoPath -and -not $SkipSwift) {
    $found = Find-Repo @(
        (Join-Path $Parent "SWIFT-Aplikacje-Biznesowe"),
        "$env:USERPROFILE\Documents\GitHub\SWIFT-Aplikacje-Biznesowe"
    )
    if ($found) { $SwiftRepoPath = $found.Path }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PELNY STACK — wszystkie systemy bankowe NARAZ" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Porty musza byc wolne PRZED startem (solo / pierwszy na czystym PC)
& (Join-Path $Scripts "school-ports.ps1") -CheckAll
if ($LASTEXITCODE -ne 0) { exit 1 }

$ukpsRepo  = if ($UkpsRepoPath)  { Find-Repo @($UkpsRepoPath) }  else { $null }
$cardsRepo = if ($CardsRepoPath) { Find-Repo @($CardsRepoPath) } else { $null }
$peerRepo  = if ($PeerBankPath -and -not $SkipPeer) { Find-Repo @($PeerBankPath) } else { $null }
$swiftRepo = if ($SwiftRepoPath -and -not $SkipSwift) { Find-Repo @($SwiftRepoPath) } else { $null }

$missing = @()
if (-not $ukpsRepo)  { $missing += "uk-payment-systems (UKPS)" }
if (-not $cardsRepo) { $missing += "Karty-Platnicze-Aplikacje-Biznesowe" }
if (-not $SkipPeer -and -not $peerRepo) { $missing += "uk-bank-system (Alice Bank)" }

if (-not $swiftRepo -and -not $SkipSwift) {
    Write-Host "SWIFT: repo nie znalezione — pomijam (-SkipSwift lub sklonuj SWIFT-Aplikacje-Biznesowe)" -ForegroundColor Yellow
}

if ($missing.Count -gt 0) {
    Write-Host "BLAD: Brakuje repozytoriow:" -ForegroundColor Red
    foreach ($m in $missing) { Write-Host "  - $m" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Sklonuj obok tego projektu, np.:" -ForegroundColor Cyan
    Write-Host "  git clone https://github.com/noradenshi/uk-payment-systems"
    Write-Host "  git clone https://github.com/FilipSl3/Karty-Platnicze-Aplikacje-Biznesowe"
    Write-Host "  git clone https://github.com/p-poweska/uk-bank-system"
    exit 1
}


Write-Host "[1/6] UKPS (CHAPS/FPS/BACS) — izba rozliczeniowa..." -ForegroundColor Yellow
Invoke-ComposeUp $ukpsRepo "UKPS"
Wait-HttpOk "http://localhost:8420/v1/healthz" 120 "UKPS CHAPS"
Wait-HttpOk "http://localhost:8421/v1/healthz" 60  "UKPS FPS"
Wait-HttpOk "http://localhost:8422/v1/healthz" 60  "UKPS BACS"

Write-Host "[2/6] Modul kart (Payment Gateway)..." -ForegroundColor Yellow
Invoke-ComposeUp $cardsRepo "Karty"
Start-Sleep -Seconds 8
Wait-HttpOk "http://localhost:8072/docs" 90 "Karty API"

Write-Host "[3/6] Alice Bank (bank kolegi)..." -ForegroundColor Yellow
if (-not $SkipPeer) {
    $nets = docker network ls --format "{{.Name}}" 2>$null
    if ($nets -notcontains "cards-backend") {
        docker network create cards-backend | Out-Null
    }
    Ensure-PeerEnv $peerRepo.Path
    Invoke-ComposeUp $peerRepo "Alice Bank"
    Start-Sleep -Seconds 15
    Wait-HttpOk "http://localhost:8001/api/docs/" 120 "Alice Bank API"
} else {
    Write-Host "      Pominiety (-SkipPeer)" -ForegroundColor DarkGray
}

Write-Host "[4/6] UK Bank B + KLIK (wbudowany)..." -ForegroundColor Yellow
Push-Location $BankRoot
if ($NoBuild) { docker compose up -d } else { docker compose up --build -d }
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location
Write-Host "      Czekam na build KLIK (moze potrwac kilka minut przy pierwszym razie)..." -ForegroundColor DarkGray
Wait-HttpOk "http://localhost:8010/api/info" 300 "UK Bank B"
Wait-HttpOk "http://localhost:8102/healthz/" 60 "KLIK API"

Write-Host "[5/6] Siec kart (capture / settlement)..." -ForegroundColor Yellow
& (Join-Path $Scripts "connect-cards-network.ps1")

Write-Host "[6/6] SWIFT middleware..." -ForegroundColor Yellow
if (-not $SkipSwift -and $swiftRepo) {
    Invoke-ComposeUp $swiftRepo "SWIFT"
    Wait-HttpOk "http://localhost:3000/docs" 90 "SWIFT"
} else {
    Write-Host "      Pominiety" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  WSZYSTKO URUCHOMIONE — mozesz laczyc systemy" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  UK Bank B (Ty)     http://localhost:8010" -ForegroundColor White
Write-Host "  Integracje         http://localhost:8010/integracje" -ForegroundColor White
Write-Host "  KLIK (kody)        http://localhost:8010/klik" -ForegroundColor White
Write-Host "  KLIK agent         http://localhost:8175" -ForegroundColor White
Write-Host "  Alice Bank GUI     http://localhost:5173" -ForegroundColor White
Write-Host "  Terminal kart      http://localhost:8072/pos" -ForegroundColor White
Write-Host "  UKPS CHAPS/FPS/BACS 8420 / 8421 / 8422" -ForegroundColor White
if (-not $SkipSwift -and $swiftRepo) {
    Write-Host "  SWIFT panel        http://localhost:3000" -ForegroundColor White
}
Write-Host ""
Write-Host "Testy:" -ForegroundColor Cyan
Write-Host "  python scripts\test_ukps_e2e.py" -ForegroundColor White
Write-Host "  python scripts\test_peer_bank_e2e.py" -ForegroundColor White
Write-Host "  python scripts\test_klik_e2e.py" -ForegroundColor White
Write-Host "  python scripts\demo_test.py" -ForegroundColor White
Write-Host ""
Write-Host "Zatrzymanie calego stacku: .\scripts\stop-full-stack.ps1" -ForegroundColor DarkGray
Write-Host ""
