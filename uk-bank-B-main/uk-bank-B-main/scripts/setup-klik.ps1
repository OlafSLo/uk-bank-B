# KLIK jest wbudowany w glowny docker-compose.yml — nie trzeba osobnego repo.
#
# Uruchom caly stack (bank + KLIK + agent):
#   docker compose up --build -d
#
# Ten skrypt tylko przypomina komende i porty.

Write-Host "=== KLIK jest juz w docker-compose.yml ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Jedna komenda (w folderze uk-bank-B-main/uk-bank-B-main):" -ForegroundColor Yellow
Write-Host "  docker compose up --build -d" -ForegroundColor White
Write-Host ""
Write-Host "Pierwszy build pobiera KLIK z GitHuba (internet). Potem offline OK." -ForegroundColor Gray
Write-Host ""
Write-Host "Adresy:" -ForegroundColor Cyan
Write-Host "  Bank + KLIK GUI:  http://localhost:8010/klik"
Write-Host "  Terminal sklepu:  http://localhost:8175"
Write-Host "  KLIK API:         http://localhost:8102"
Write-Host ""
Write-Host "PIN demo: 1234 | Konto: 11111111" -ForegroundColor Green
Write-Host "Klucz agenta (terminal): klik_dev_agent_uk_school_demo | Strefa: UK" -ForegroundColor Green
Write-Host ""
Write-Host "Test: python scripts\test_klik_e2e.py" -ForegroundColor Cyan
