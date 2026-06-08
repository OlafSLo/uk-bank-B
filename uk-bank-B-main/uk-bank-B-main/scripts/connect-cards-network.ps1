# Podlacza kontener uk-bank-b do sieci cards-backend (modul kart).
# Card Provider wywoluje wtedy http://uk-bank-b:8000/capture
# Uruchom PO starcie modulu kart Filipa.

$ErrorActionPreference = "Stop"

$networks = docker network ls --format "{{.Name}}" 2>$null
if ($networks -notcontains "cards-backend") {
    Write-Host "BLAD: Siec cards-backend nie istnieje." -ForegroundColor Red
    Write-Host "Najpierw uruchom modul kart: docker compose up -d (w repo Karty-Platnicze)"
    exit 1
}

$running = docker ps --filter "name=uk-bank-b" --format "{{.Names}}" 2>$null
if (-not $running) {
    Write-Host "BLAD: Kontener uk-bank-b nie dziala. Uruchom: docker compose up -d" -ForegroundColor Red
    exit 1
}

docker network connect cards-backend uk-bank-b 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: uk-bank-b podlaczony do cards-backend (capture/settlement dziala)." -ForegroundColor Green
} else {
    Write-Host "OK: uk-bank-b juz jest w sieci cards-backend." -ForegroundColor Green
}
