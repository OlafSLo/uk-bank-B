# UK Bank B — System Bankowości Internetowej

> **Symulacja brytyjskiego systemu bankowego** obsługująca 5 typów przelewów:
> Wewnętrzny (On-us), BACS, FPS, CHAPS i SWIFT.
>
> Aplikacja działa w **Dockerze** — nie musisz instalować Pythona, PostgreSQL ani
> żadnych bibliotek na swoim komputerze. Potrzebujesz tylko Dockera.

---

## Spis treści

1. [Czym jest ten projekt?](#1-czym-jest-ten-projekt)
2. [Czego potrzebujesz? (Prerequisites)](#2-czego-potrzebujesz-prerequisites)
3. [Krok po kroku — uruchomienie](#3-krok-po-kroku--uruchomienie)
4. [Jak korzystać z aplikacji?](#4-jak-korzystać-z-aplikacji)
5. [Dostępne typy przelewów](#5-dostępne-typy-przelewów)
6. [Wersje języków i narzędzi](#6-wersje-języków-i-narzędzi)
7. [Problemy i rozwiązania (Troubleshooting)](#7-problemy-i-rozwiązania-troubleshooting)
8. [Struktura projektu](#8-struktura-projektu)

---

## 1. Czym jest ten projekt?

To jest **symulacja brytyjskiego banku** (UK Bank B), która pokazuje jak działają
różne systemy przelewów używane w Wielkiej Brytanii:

| System | Opis |
|--------|------|
| **Wewnętrzny (On-us)** | Przelew między kontami w tym samym banku — natychmiastowy |
| **BACS** | Standardowy przelew międzybankowy — rozliczenie w 3 dni |
| **FPS** | Faster Payments — natychmiastowy, do £250 000 |
| **CHAPS** | RTGS przez Bank of England — natychmiastowy, do £10 000 000 |
| **SWIFT** | Międzynarodowy transfer z przewalutowaniem (GBP/EUR/USD) |

Aplikacja ma **graficzny interfejs użytkownika** (GUI) z formularzami logowania,
rejestracji i wykonywania przelewów — wszystko dostępne przez przeglądarkę.

---

## 2. Czego potrzebujesz? (Prerequisites)

### Wymagane

| Narzędzie | Minimalna wersja | Pobranie |
|-----------|-----------------|----------|
| **Docker Desktop** | wersja 24+ | [Pobierz Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| **System operacyjny** | Windows 10/11, macOS lub Linux | — |

### Sprawdź czy Docker jest zainstalowany

Otwórz **Terminal** (na Windows: **Wiersz Poleceń** lub **PowerShell**):

```bash
docker --version
```

Powinieneś zobaczyć coś takiego:

```
Docker version 27.0.3, build ...
```

### Jeśli nie masz Dockera — instrukcja instalacji

#### Windows / macOS

1. Wejdź na stronę: https://www.docker.com/products/docker-desktop/
2. Kliknij **"Download for Windows"** (lub macOS)
3. Uruchom pobrany plik i postępuj zgodnie z instalatorem
4. Po instalacji **uruchom Docker Desktop** (musi być włączony, żeby aplikacja działała)
5. Zaczekaj aż zobaczysz zielony napis **"Engine running"** w lewym dolnym rogu

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install docker.io docker-compose-v2
sudo systemctl start docker
sudo systemctl enable docker
```

> **Uwaga dla Windows**: Jeśli używasz PowerShell, po instalacji Dockera
> może być potrzebny restart komputera.

---

## 3. Krok po kroku — uruchomienie

### Krok 1: Pobierz projekt

Kliknij zielony przycisk **"Code"** na stronie GitHub, wybierz **"Download ZIP"**,
wypakuj archiwum w wybranym miejscu na dysku.

Możesz też sklonować repozytorium (jeśli znasz GIT):

```bash
git clone https://github.com/TWOJE-KONTO/uk-bank-B.git
cd uk-bank-B
```

### Krok 2: Otwórz terminal w folderze projektu

**Windows**: Otwórz folder `uk-bank-B-main/uk-bank-B-main/`, kliknij w pasku adresu,
wpisz `cmd` i naciśnij Enter. Otworzy się okno terminala.

**macOS/Linux**: Otwórz Terminal, wpisz `cd ` (z spacją na końcu), przeciągnij folder
`uk-bank-B-main/uk-bank-B-main/` do okna terminala i naciśnij Enter.

### Krok 3: Uruchom aplikację

W terminalu (upewnij się, że jesteś w folderze `uk-bank-B-main/uk-bank-B-main/`) wpisz:

```bash
docker compose up --build -d
```

> **Wyjaśnienie**: To polecenie:
> 1. Pobiera obrazy PostgreSQL 15 i Python 3.12 (tylko za pierwszym razem)
> 2. Buduje obraz aplikacji (instaluje biblioteki)
> 3. Uruchamia bazę danych PostgreSQL
> 4. Uruchamia aplikację bankową
> 5. Robi to wszystko automatycznie — nie musisz nic robić

**Czas oczekiwania**: Za pierwszym razem to może zająć **2-5 minut** (zależy od
szybkości internetu i komputera). Kolejne uruchomienia będą dużo szybsze.

### Krok 4: Sprawdź czy działa

W terminalu wpisz:

```bash
docker ps
```

Powinieneś zobaczyć dwa kontenery:
- `uk-bank-b-main-bank-app-1` — aplikacja bankowa
- `uk-bank-b-main-postgres-1` — baza danych PostgreSQL

Oba powinny mieć status **"Up"** (uruchomione).

### Krok 5: Otwórz aplikację w przeglądarce

Otwórz przeglądarkę (Chrome, Firefox, Edge) i wpisz w pasku adresu:

```
http://localhost:8000
```

Zobaczysz stronę logowania UK Bank B.

### Krok 6: Zatrzymanie aplikacji

Gdy skończysz pracę, możesz zatrzymać aplikację:

```bash
docker compose down
```

Aby całkowicie usunąć też bazę danych (razem z danymi kont):

```bash
docker compose down -v
```

---

## 4. Jak korzystać z aplikacji?

### Rejestracja konta

1. Wejdź na `http://localhost:8000/register`
2. Wpisz **nazwę użytkownika** (np. `jan`)
3. Wpisz **hasło** (minimum 4 znaki, np. `test123`)
4. Wybierz **rolę** (zostaw `customer`)
5. Kliknij **"Zarejestruj się"**
6. Zostaniesz przekierowany do strony logowania

### Logowanie

1. Wejdź na `http://localhost:8000/login`
2. Wpisz nazwę użytkownika i hasło
3. Kliknij **"Zaloguj się"**
4. Zobaczysz **Dashboard** (stronę główną) z saldami kont

### Dashboard (strona główna)

Na dashboardzie widzisz:
- **Salda kont** — kolorowe karty z kwotami i limitami zadłużenia
- **Szybkie przelewy** — siatka z 5 typami przelewów
- **Lista funkcjonalności** — opis wszystkich opcji systemu

Domyślnie są dwa konta demo:
- Konto `11111111` — £500.00
- Konto `22222222` — £50.00

### Wykonanie przelewu

1. Kliknij wybrany typ przelewu na dashboardzie (np. "Wewnętrzny")
2. Wypełnij formularz:
   - **Sort Code nadawcy** — 6 cyfr (np. `102030`)
   - **Konto nadawcy** — 8 cyfr (np. `11111111`)
   - **Sort Code odbiorcy** — 6 cyfr (np. `102030`)
   - **Konto odbiorcy** — 8 cyfr (np. `22222222`)
   - **Kwota** — w GBP
3. Kliknij **"Wykonaj przelew"**
4. Zobaczysz wynik — zielony komunikat sukcesu lub czerwony błąd

### Wylogowanie

Kliknij przycisk **"Wyloguj"** w prawym górnym rogu.

---

## 5. Dostępne typy przelewów

### 🏛️ Przelew Wewnętrzny (On-us Transfer)

| Cecha | Szczegóły |
|-------|-----------|
| Czas | Natychmiastowy |
| Limit | Brak |
| Opłata | Bezpłatny |
| Waluta | Tylko GBP |
| Opis | Przelew między kontami w UK Bank B |

### 📤 BACS (Bankers' Automated Clearing Services)

| Cecha | Szczegóły |
|-------|-----------|
| Czas | 3 dni robocze |
| Limit | Standardowy |
| Opłata | Niska |
| Waluta | GBP |
| Opis | Standardowy przelew międzybankowy w UK |

### ⚡ FPS (Faster Payments Service)

| Cecha | Szczegóły |
|-------|-----------|
| Czas | Natychmiastowy (sekundy) |
| Limit | £250 000 |
| Opłata | Niska |
| Waluta | GBP |
| Opis | System natychmiastowych płatności z mechanizmem Gridlock Resolution |

### 🏦 CHAPS (Clearing House Automated Payment System)

| Cecha | Szczegóły |
|-------|-----------|
| Czas | Natychmiastowy (RTGS) |
| Limit | £10 000 000 |
| Opłata | Wysoka (ok. £20-30) |
| Waluta | GBP |
| Opis | Real Time Gross Settlement przez Bank of England |

### 🌍 SWIFT (Society for Worldwide Interbank Financial Telecommunication)

| Cecha | Szczegóły |
|-------|-----------|
| Czas | 1-3 dni robocze |
| Limit | Międzynarodowy |
| Opłata | 1% kwoty przelewu |
| Waluty | GBP, EUR, USD |
| Opis | Międzynarodowy transfer z przewalutowaniem |

---

## 6. Wersje języków i narzędzi

| Technologia | Wersja | Uwagi |
|-------------|--------|-------|
| **Python** | 3.12 (slim) | Obraz Docker: `python:3.12-slim` |
| **FastAPI** | najnowsza | Framework webowy |
| **Starlette** | najnowsza (1.x) | Obsługa żądań HTTP + Jinja2 templates |
| **PostgreSQL** | 15 | Obraz Docker: `postgres:15` |
| **Uvicorn** | najnowsza | Serwer ASGI do uruchomienia aplikacji |
| **Jinja2** | najnowsza | Silnik szablonów HTML |
| **PyJWT** | najnowsza | Tokeny JWT do autoryzacji |
| **bcrypt** | 5.x | Bezpieczne haszowanie haseł |
| **psycopg2-binary** | najnowsza | Sterownik PostgreSQL dla Pythona |
| **APScheduler** | najnowsza | Zadania zaplanowane (archiwizacja) |
| **Pandas** | najnowsza | Przetwarzanie danych transakcji |
| **Docker** | 24+ | Platforma kontenerowa |
| **HTML/CSS** | — | Interfejs użytkownika z responsywnym designem |

### Lista bibliotek Python (`requirements.txt`)

```txt
fastapi
uvicorn[standard]
psycopg2-binary
sqlalchemy
pyjwt
bcrypt
requests
python-multipart
apscheduler
pandas
jinja2
aiofiles
```

---

## 7. Problemy i rozwiązania (Troubleshooting)

### Aplikacja nie uruchamia się

**Problem**: `docker compose up --build -d` zwraca błąd.

**Rozwiązanie**:
1. Sprawdź czy Docker Desktop jest **uruchomiony** (zielony pasek)
2. Spróbuj zrestartować Docker Desktop
3. Sprawdź czy port 8000 nie jest zajęty:
   ```bash
   netstat -ano | findstr :8000
   ```
4. Jeśli port jest zajęty, zatrzymaj program go używający

### Strona nie odpowiada (Internal Server Error)

**Problem**: Po zalogowaniu widzisz "Internal Server Error".

**Rozwiązanie**:
1. Zatrzymaj aplikację: `docker compose down`
2. Usuń bazę danych: `docker compose down -v` (to **usunie wszystkie dane**)
3. Uruchom ponownie: `docker compose up --build -d`

### Nie mogę się zalogować

**Problem**: Logowanie nie działa.

**Rozwiązanie**:
1. Upewnij się, że się zarejestrowałeś (strona `/register`)
2. Hasło musi mieć minimum 4 znaki
3. Spróbuj zresetować dane: `docker compose down -v && docker compose up --build -d`

### Błąd "Port already allocated"

**Problem**: Port 8000 lub 5432 jest już zajęty.

**Rozwiązanie**:
1. Znajdź proces: `netstat -ano | findstr :8000`
2. Zatrzymaj go lub zmień port w `docker-compose.yml`

### Jak zobaczyć logi aplikacji?

```bash
docker logs uk-bank-b-main-bank-app-1
```

### Jak zrestartować tylko aplikację (bez bazy)?

```bash
docker compose restart bank-app
```

### Jak wejść do bazy danych PostgreSQL?

```bash
docker exec -it uk-bank-b-main-postgres-1 psql -U bank_user -d bank_db
```

---

## 8. Struktura projektu

```
uk-bank-B-main/
├── api/                          # Interfejs API (FastAPI)
│   ├── routes.py                 # Główna aplikacja (endpointy + GUI)
│   ├── static/
│   │   └── style.css             # Stylowanie GUI
│   └── templates/                # Szablony HTML (Jinja2)
│       ├── login.html            # Strona logowania
│       ├── register.html         # Strona rejestracji
│       ├── dashboard.html        # Strona główna z saldami
│       ├── transfer_internal.html # Formularz przelewu wewnętrznego
│       ├── transfer_bacs.html    # Formularz BACS
│       ├── transfer_fps.html     # Formularz FPS
│       ├── transfer_chaps.html   # Formularz CHAPS
│       └── transfer_swift.html   # Formularz SWIFT
├── application/                  # Logika biznesowa (Use Cases)
│   ├── auth_service.py           # Rejestracja i logowanie (JWT + bcrypt)
│   ├── internal_transfer.py      # Przelew wewnętrzny
│   ├── bacs_transfer.py          # Przelew BACS
│   ├── fps_transfer.py           # Faster Payments + Gridlock
│   ├── chaps_transfer.py         # CHAPS / RTGS
│   ├── swift_transfer.py         # SWIFT międzynarodowy
│   └── transaction_query.py      # Wyszukiwanie transakcji
├── domain/                       # Warstwa domeny (model biznesowy)
│   ├── entities.py               # User, Account (klasy główne)
│   ├── value_objects.py          # Money, Currency, AccountNumber
│   ├── repositories.py           # Interfejsy baz danych
│   └── exceptions.py             # Wyjątki biznesowe
├── infrastructure/               # Implementacje techniczne
│   ├── postgresql_repository.py  # Baza PostgreSQL
│   ├── sqlite_repository.py      # Baza SQLite (alternatywa)
│   ├── memory_repository.py      # Baza w pamięci (testy)
│   └── archive_service.py        # Archiwizacja transakcji
├── migrate.py                    # Skrypt migracji bazy danych
├── main.py                       # Alternatywny punkt startowy (starszy)
├── docker-compose.yml            # Definicja kontenerów Docker
├── Dockerfile                    # Budowa obrazu aplikacji
└── requirements.txt              # Lista bibliotek Python
```

---

## Podsumowanie

Gratulacje! 🎉 Uruchomiłeś w pełni funkcjonalny system bankowy z:

- ✅ Rejestracją i logowaniem (JWT + bcrypt)
- ✅ 5 typami przelewów (Internal, BACS, FPS, CHAPS, SWIFT)
- ✅ Graficznym interfejsem użytkownika
- ✅ Bazą danych PostgreSQL
- ✅ Wszystko działa w Dockerze — zero konfiguracji

**Aplikacja dostępna pod adresem:** http://localhost:8000

**Dokumentacja API (dla programistów):** http://localhost:8000/docs
