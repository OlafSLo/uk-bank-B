# Mapa portow — sala: kazdy uruchamia swoje repo po kolei, na koncu wszystko dziala naraz.
#
#   .\scripts\school-ports.ps1              mapa portow
#   .\scripts\school-ports.ps1 -Check       przed TWOIM startem (tylko porty UK Bank B)
#   .\scripts\school-ports.ps1 -Status      co juz dziala w sali (caly ekosystem)

param(
    [switch]$Check,
    [switch]$CheckAll,
    [switch]$Status
)

# Kto co odpala — kazdy zespol tylko swoje docker compose
$Ecosystem = [ordered]@{
    "UKPS (zespol platnosci)"     = @{ Ports = @(8420, 8421, 8422); Start = "cd uk-payment-systems && docker compose -f compose.yml up -d" }
    "Karty (zespol Filipa)"       = @{ Ports = @(8072, 3072);        Start = "cd Karty-Platnicze... && docker compose up -d" }
    "Alice Bank (zespol kolegi)"  = @{ Ports = @(8001, 5173);       Start = "cd uk-bank-system && docker compose up -d" }
    "SWIFT (zespol SWIFT)"        = @{ Ports = @(3000);             Start = "cd SWIFT-Aplikacje... && docker compose up -d" }
    "UK Bank B — TY"              = @{ Ports = @(8010, 8102, 8175, 5438); Start = "docker compose up --build -d" }
}

function Test-PortListening([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" } |
        Select-Object -First 1
    return [bool]$conn
}

function Test-GroupUp([int[]]$Ports) {
    ($Ports | Where-Object { Test-PortListening $_ }).Count -gt 0
}

Write-Host ""
Write-Host "Mapa portow — sala (kazdy po kolei, na koncu wszystko naraz)" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

if ($CheckAll) {
    Write-Host "Sprawdzam czy WSZYSTKIE porty ekosystemu sa wolne (start od zera)..." -ForegroundColor Yellow
    Write-Host ""
    $blocked = @()
    foreach ($entry in $Ecosystem.GetEnumerator()) {
        foreach ($p in $entry.Value.Ports) {
            if (Test-PortListening $p) { $blocked += $p }
        }
    }
    $blocked = $blocked | Sort-Object -Unique
    if ($blocked.Count -gt 0) {
        Write-Host "Zajete porty: $($blocked -join ', ')" -ForegroundColor Red
        Write-Host "Zatrzymaj stare kontenery (docker compose down w kazdym repo)." -ForegroundColor White
        exit 1
    }
    Write-Host "Wszystkie porty wolne." -ForegroundColor Green
    exit 0
}

if ($Check) {
    Write-Host "Sprawdzam porty UK Bank B przed TWOIM startem..." -ForegroundColor Yellow
    Write-Host "(Porty kolegow moga byc zajete — to OK, znaczy ze ich system juz dziala.)" -ForegroundColor DarkGray
    Write-Host ""
    $mine = $Ecosystem["UK Bank B — TY"].Ports
    $blocked = @()
    foreach ($p in $mine) {
        $up = Test-PortListening $p
        $st = if ($up) { "ZAJETY — nie uruchomisz banku"; $blocked += $p } else { "wolny — OK" }
        Write-Host ("  :{0,-5} {1}" -f $p, $st)
    }
    Write-Host ""
    if ($blocked.Count -gt 0) {
        Write-Host "Twoje porty zajete: $($blocked -join ', ')" -ForegroundColor Red
        Write-Host "  docker compose down   (w tym folderze)" -ForegroundColor White
        exit 1
    }
    Write-Host "Mozesz odpalic: docker compose up --build -d" -ForegroundColor Green
    Write-Host "Potem (jesli karty juz dzialaja): .\scripts\connect-cards-network.ps1" -ForegroundColor Green
    exit 0
}

if ($Status) {
    Write-Host "Co juz dziala w sali:" -ForegroundColor Yellow
    Write-Host ""
    $ready = 0
    foreach ($entry in $Ecosystem.GetEnumerator()) {
        $name = $entry.Key
        $ports = $entry.Value.Ports
        $up = Test-GroupUp $ports
        if ($up) { $ready++ }
        $portStr = ($ports -join ", ")
        $st = if ($up) { "DZIALA" } else { "jeszcze nie" }
        $color = if ($up) { "Green" } else { "DarkYellow" }
        Write-Host ("  [{0}] {1,-28} porty {2}" -f $st, $name, $portStr) -ForegroundColor $color
    }
    Write-Host ""
    Write-Host "Gotowe: $ready / $($Ecosystem.Count) systemow" -ForegroundColor $(if ($ready -eq $Ecosystem.Count) { "Green" } else { "Yellow" })
    if ($ready -eq $Ecosystem.Count) {
        Write-Host "Pelna integracja mozliwa — http://localhost:8010/integracje" -ForegroundColor Green
    } else {
        Write-Host "Poczekaj az pozostali uruchomia swoje repozytoria." -ForegroundColor DarkGray
    }
    exit 0
}

# Domyslnie: wydruk mapy + kto co odpala
foreach ($entry in $Ecosystem.GetEnumerator()) {
    $ports = $entry.Value.Ports -join ", "
    Write-Host ("  {0,-28} :{1}" -f $entry.Key, $ports)
}

Write-Host ""
Write-Host "Scenariusz sali:" -ForegroundColor Cyan
Write-Host "  1. Kazdy podchodzi po kolei i odpala TYLKO swoje repo (nie rob docker compose down u innych!)" -ForegroundColor White
Write-Host "  2. Na koncu wszystkie porty z mapy sa zajete = cala siec bankowa dziala" -ForegroundColor White
Write-Host "  3. Ty (UK Bank B): .\scripts\school-ports.ps1 -Check  ->  docker compose up --build -d" -ForegroundColor White
Write-Host ""
Write-Host "Sprawdz postep sali:  .\scripts\school-ports.ps1 -Status" -ForegroundColor Green
Write-Host "Twoj bank:            http://localhost:8010" -ForegroundColor Green
