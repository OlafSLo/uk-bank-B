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
4. [Integracja z modułem kart płatniczych](#4-integracja-z-modułem-kart-płatniczych) ⭐ **NOWOŚĆ**
5. [Scenariusz prezentacji dla wykładowcy](#5-scenariusz-prezentacji-dla-wykładowcy)
6. [Jak korzystać z aplikacji?](#6-jak-korzystać-z-aplikacji)
7. [Dostępne typy przelewów](#7-dostępne-typy-przelewów)
8. [Wersje języków i narzędzi](#8-wersje-języków-i-narzędzi)
9. [Problemy i rozwiązania (Troubleshooting)](#9-problemy-i-rozwiązania-troubleshooting)
10. [Struktura projektu](#10-struktura-projektu)

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

**Integracja z modułem kart płatniczych** (repozytorium zespołu kart):
- wydawanie kart przez Payment Gateway (REST + HMAC-SHA256),
- płatności kartą w terminalu POS,
- settlement (obciążenie konta klienta przez endpoint `/capture`).

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
- `uk-bank-b` — aplikacja bankowa
- `uk-bank-b-main-postgres-1` (lub podobna nazwa) — baza danych PostgreSQL

Oba powinny mieć status **"Up"** (uruchomione).

> **Uwaga:** Sam bank można uruchomić bez modułu kart (tylko przelewy).
> Aby **karty działały**, wykonaj dodatkowo sekcję [Integracja z modułem kart](#4-integracja-z-modułem-kart-płatniczych).

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

## 4. Integracja z modułem kart płatniczych

UK Bank B łączy się z modułem **Karty Płatnicze** (Payment Gateway + Card Provider)
z repozytorium: [FilipSl3/Karty-Platnicze-Aplikacje-Biznesowe](https://github.com/FilipSl3/Karty-Platnicze-Aplikacje-Biznesowe)

| Parametr | Wartość UK Bank B |
|----------|-------------------|
| Bank ID | `UK_BANK_B` |
| Klucz API | `bank-key-uk-b` |
| Sekret HMAC | `secret-uk-b-hmac` |
| Prefiks BIN | `460001` |
| Waluta | `GBP` |

### Szybki start (2 kroki)

**Krok 1 – moduł kart Filipa** (osobne repo, bez zmian):

```bash
git clone https://github.com/FilipSl3/Karty-Platnicze-Aplikacje-Biznesowe
cd Karty-Platnicze-Aplikacje-Biznesowe
docker compose up -d
```

Sprawdź: http://localhost:8072/docs

**Krok 2 – UK Bank B**:

```bash
cd uk-bank-B-main/uk-bank-B-main
docker compose up --build -d
.\scripts\connect-cards-network.ps1
```

To podłącza bank do sieci `cards-backend`, żeby **settlement** (`POST /capture`) działał.

**Test:**

```bash
python scripts/demo_test.py
python scripts/test_issue_card.py
python scripts/test_card_e2e.py
```

### Jednym skryptem (Windows)

```powershell
.\scripts\start-demo.ps1
```

### Adresy po uruchomieniu

| Serwis | Adres | Opis |
|--------|-------|------|
| **UK Bank B (GUI)** | http://localhost:8000 | Logowanie, dashboard, przelewy |
| **Wyrabianie karty** | http://localhost:8000/karta | Wydanie karty + instrukcja POS |
| **Strona demo** | http://localhost:8000/demo-karty | Status integracji + szybki test API |
| **Terminal POS** | http://localhost:8072/pos | Płatność kartą (symulacja sklepu) |
| **Swagger kart** | http://localhost:8072/docs | API Payment Gateway |
| **Panel admina kart** | http://localhost:3072 | admin / admin123 |
| **Swagger banku** | http://localhost:8000/docs | API UK Bank B (capture, authorize) |

### Jak to działa (opis krok po kroku)

Integracja łączy **trzy systemy**: GUI banku, moduł kart kolegi i konto klienta w PostgreSQL.

```
┌─────────────────┐     HMAC REST      ┌──────────────────────┐
│  UK Bank B GUI  │ ─────────────────► │  Payment Gateway     │
│  /karta         │  POST /cards/issue │  :8072               │
└────────┬────────┘                    └──────────┬───────────┘
         │                                          │ gRPC / ISO8583
         │ zapis karty w DB                         ▼
         │                               ┌──────────────────────┐
         │                               │  Card Provider       │
         │                               │  (saldo PREPAID)     │
         │                               └──────────┬───────────┘
         │                                          │
         │   Terminal POS :8072/pos                 │ autoryzacja
         │   (numer, CVV, kwota)                    │
         │                                          │
         │         ~30 s później (demo)             │
         │◄──────── POST /capture ──────────────────┘
         │          (sieć Docker cards-backend)
         ▼
   Obciążenie konta GBP
   (saldo spada na Dashboard)
```

**1. Wydanie karty (bank → gateway)**

- Klient wybiera konto i PIN na stronie `/karta`.
- Bank wysyła do Payment Gateway żądanie `POST /api/v1/cards/issue` z nagłówkami:
  `X-API-Key`, `X-Signature`, `X-Timestamp` (HMAC-SHA256).
- Gateway tworzy kartę **PREPAID** z prefiksem BIN `460001` i saldem początkowym = saldo konta.
- Bank automatycznie przechodzi cykl życia karty (PRODUCING → SHIPPED → ACTIVE), żeby można było od razu płacić.
- PAN, CVV i data ważności wracają do GUI **jednorazowo** – bank zapisuje też token karty w PostgreSQL.

**2. Płatność w terminalu POS (sklep → gateway → card provider)**

- W http://localhost:8072/pos wpisujesz dane karty i kwotę.
- POS wywołuje `POST /api/v1/payments/authorize`.
- Card Provider sprawdza PAN, CVV, datę ważności, status karty i saldo PREPAID.
- Wynik: **APPROVED** (kod `00`) lub **DECLINED** (np. kod `51` – brak środków).

**3. Settlement (card provider → bank)**

- Po autoryzacji moduł kart po ok. **30 sekund** wysyła do banku `POST http://uk-bank-b:8000/capture`.
- Bank znajduje kartę po `card_token`, obciąża konto klienta w GBP i zapisuje transakcję.
- Saldo na **Dashboard** spada o kwotę płatności.

**Ważne:** settlement działa tylko gdy kontener `uk-bank-b` jest podłączony do sieci Docker modułu kart:

```powershell
.\scripts\connect-cards-network.ps1
```

### Dodawanie karty – test krok po kroku (GUI)

Poniższy scenariusz możesz powtórzyć samodzielnie. Przetestowano na działającym stacku Docker (bank + moduł kart).

#### Przygotowanie (jednorazowo)

1. Uruchom moduł kart (repo Filipa):
   ```powershell
   cd Karty-Platnicze-Aplikacje-Biznesowe
   docker compose up -d
   ```
   Sprawdź: http://localhost:8072/docs (powinien się otworzyć Swagger).

2. Uruchom UK Bank B:
   ```powershell
   cd uk-bank-B-main\uk-bank-B-main
   docker compose up --build -d
   .\scripts\connect-cards-network.ps1
   ```

3. (Opcjonalnie) Test automatyczny całego łańcucha:
   ```powershell
   python scripts\test_card_e2e.py
   ```
   Skrypt: wydaje kartę → płaci w POS → czeka na settlement → sprawdza spadek salda.

#### Krok 1 – Zaloguj się do banku

1. Otwórz http://localhost:8000/login
2. Zaloguj się (lub zarejestruj konto na `/register`).
3. Na Dashboard zobaczysz konto demo `102030-11111111` ze saldem **£5000**.

#### Krok 2 – Wydaj kartę

1. W menu kliknij **Karty** (adres: http://localhost:8000/karta).
2. W formularzu wybierz konto **102030-11111111**.
3. Wpisz PIN, np. **`1234`** (dokładnie 4 cyfry).
4. Kliknij **Wydaj kartę PREPAID**.
5. Pojawi się okno z **numerem karty, CVV i datą ważności** – zapisz je (pokazane jednorazowo).
6. Po prawej stronie panel **„Terminal POS — co wpisać”** wypełni się automatycznie.
   Możesz też kliknąć **Wypełnij POS** przy istniejącej karcie na liście poniżej.

#### Krok 3 – Płatność w terminalu POS

1. Otwórz http://localhost:8072/pos (przycisk **Otwórz terminal POS** na stronie `/karta`).
2. Wpisz **dokładnie** wartości z kroku 2:

   | Pole w POS | Przykład | Uwaga |
   |------------|----------|-------|
   | Card Number | `4600017058941006` | 16 cyfr, **bez spacji** |
   | Expiry Month | `6` | liczba (dla 06/29 wpisz **6**) |
   | Expiry Year | **`29`** | **2 cyfry** – NIE wpisuj `2029` |
   | CVV | np. `979` | 3 cyfry z okna wydania karty |
   | Amount | `50.00` | nie większe niż saldo na karcie PREPAID |

3. Kliknij **Authorize Payment**.
4. Oczekiwany wynik: zielony napis **APPROVED** ✅

   Typowe błędy:
   - **DECLINED** + kod `51` → kwota za duża względem salda karty.
   - **ERROR** przy roku `2029` → użyj **`29`** (2 cyfry).
   - **DECLINED** → zły CVV lub numer karty ze spacjami.

#### Krok 4 – Sprawdź settlement (obciążenie konta)

1. Poczekaj ok. **30 sekund** (moduł kart ma skrócony czas settlement w demo).
2. Odśwież **Dashboard** (http://localhost:8000/dashboard).
3. Saldo konta `11111111` powinno spaść o kwotę płatności (np. z £5000 na £4950).

#### Krok 5 – Sync saldo (po wpłacie na konto)

Jeśli zrobiłeś przelew na konto i chcesz zaktualizować limit na karcie PREPAID:

1. Wejdź na http://localhost:8000/karta
2. Przy karcie kliknij **Sync saldo**
3. Saldo karty w module kart zrówna się z saldem konta bankowego

#### Test bez GUI (skrypty)

| Skrypt | Co robi |
|--------|---------|
| `python scripts\demo_test.py` | Sprawdza czy bank i gateway odpowiadają |
| `python scripts\test_issue_card.py` | Wydaje kartę przez HMAC (tylko gateway) |
| `python scripts\test_card_e2e.py` | Pełny test: wydanie → POS → settlement |
| `POST http://localhost:8000/api/integration/test` | Test API (Swagger / demo-karty) |

Przykład wyniku udanego testu POS (API):

```json
{
  "approved": true,
  "response_code": "00",
  "authorization_code": "2A03BC",
  "message": "Approved"
}
```


### Endpointy zaimplementowane w UK Bank B

| Endpoint | Kto wywołuje | Opis |
|----------|--------------|------|
| `POST /capture` | Card Provider | Finalne obciążenie konta po płatności |
| `POST /api/v1/authorize` | Card Provider (przyszłość) | Blokada środków |
| `POST /api/v1/refund` | Card Provider | Zwrot |

---

## 5. Scenariusz prezentacji dla wykładowcy

> **Czas:** ok. 5–7 minut  
> **Przygotowanie:** uruchom `.\scripts\start-demo.ps1` i otwórz http://localhost:8000/demo-karty

### Krok 1 – Pokaż, że systemy są połączone

1. Otwórz **http://localhost:8000/demo-karty**
2. Wszystkie statusy powinny być **zielone**
3. Kliknij **„Szybki test integracji”** – powinien zwrócić `"overall": "OK"`

### Krok 2 – Wydaj kartę klientowi

1. Zaloguj się: http://localhost:8000/login (lub zarejestruj konto)
2. Wejdź na **Karty**: http://localhost:8000/karta
3. Wybierz konto demo `11111111` (£5000), PIN `1234` → **Wydaj kartę PREPAID**
4. Pojawi się okno z **PAN, CVV, datą ważności** – zapisz je (pokazane jednorazowo)
5. Panel po prawej **„Terminal POS — co wpisać”** ma gotowe wartości (rok **29**, nie 2029)

### Krok 3 – Płatność w terminalu POS

1. Otwórz **http://localhost:8072/pos** (w nowej karcie)
2. Wpisz dane karty z kroku 2 (numer bez spacji, rok **29**, CVV z wydania)
3. Kwota: **50.00** (mniejsza niż saldo karty)
4. Wynik: **APPROVED** ✅

### Krok 4 – Settlement (obciążenie konta)

1. Poczekaj **~30 sekund** (settlement w module kart jest skrócony do demo)
2. Odśwież **Dashboard** banku
3. Saldo konta `11111111` spadnie o £50

### Krok 5 – Bezpieczeństwo (HMAC)

Wyjaśnij wykładowcy:
- Bank podpisuje żądania nagłówkami `X-API-Key`, `X-Signature`, `X-Timestamp`
- Payment Gateway weryfikuje podpis – ochrona przed fałszowaniem i replay attack
- Pokaż Swagger: http://localhost:8072/docs → `POST /api/v1/cards/issue`

### Krok 6 (opcjonalnie) – Panel operatora kart

1. http://localhost:3072 → login: **admin** / **admin123**
2. Pokaż listę kart, statusy, cykl życia

---

## 6. Jak korzystać z aplikacji?

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
- Konto `11111111` — £5000.00
- Konto `22222222` — £1200.00
- Sort code obu kont: `102030`

### Karty płatnicze

Szczegółowy test krok po kroku: sekcja [Dodawanie karty – test krok po kroku (GUI)](#dodawanie-karty--test-krok-po-kroku-gui).

1. Wejdź na http://localhost:8000/karta (menu **Karty**)
2. Wybierz konto, wpisz **4-cyfrowy PIN** i kliknij **Wydaj kartę PREPAID**
3. Zapisz **numer karty, CVV i datę ważności** (pokazane jednorazowo)
4. Użyj panelu **Terminal POS — co wpisać** albo przycisku **Wypełnij POS**
5. Płać kartą w terminalu: http://localhost:8072/pos (rok ważności: **29**, nie 2029)
6. Po wpłacie na konto użyj **Sync saldo** na stronie `/karta`
7. Status integracji: http://localhost:8000/demo-karty

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

## 7. Dostępne typy przelewów

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

## 8. Wersje języków i narzędzi

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

## 9. Problemy i rozwiązania (Troubleshooting)

### Karty: „Moduł kart płatniczych jest niedostępny”

**Przyczyna:** Payment Gateway nie działa lub bank nie ma do niego połączenia.

**Rozwiązanie:**
1. Uruchom moduł kart: `docker compose up -d` w repo Karty-Platnicze
2. Sprawdź: http://localhost:8072/docs
3. Uruchom bank z siecią `cards-backend`: `.\scripts\start-demo.ps1`
4. Test: `python scripts/demo_test.py`

### Karty: płatność DECLINED

**Przyczyny:**

| Objaw | Przyczyna | Rozwiązanie |
|-------|-----------|-------------|
| DECLINED, kod `51` | Kwota większa niż saldo PREPAID na karcie | Zmniejsz kwotę lub **Sync saldo** na `/karta` |
| ERROR przy roku | Wpisano `2029` zamiast `29` | W POS pole „rok” to **2 cyfry** |
| DECLINED | Zły CVV, spacje w numerze karty | Skopiuj PAN z `/karta` bez spacji |

### Karty: saldo konta wyczerpane po testach

**Przyczyna:** Wielokrotne testy settlement obciążyły konto demo.

**Rozwiązanie:**
```powershell
docker compose down -v
docker compose up --build -d
.\scripts\connect-cards-network.ps1
```

### Karty: płatność APPROVED, ale saldo banku się nie zmienia

**Przyczyna:** Bank nie jest osiągalny z sieci Docker modułu kart.

**Rozwiązanie:** Kontener banku musi nazywać się `uk-bank-b` i być w sieci `cards-backend`.
Użyj `docker compose up --remove-orphans` z tego repozytorium.

### Docker: konflikt sieci „Pool overlaps”

**Przyczyna:** Ręcznie utworzona sieć `cards-backend` koliduje z modułem kart.

**Rozwiązanie:**
```bash
docker network rm cards-backend
cd Karty-Platnicze-Aplikacje-Biznesowe
docker compose up --build -d
cd ../uk-bank-B-main/uk-bank-B-main
docker compose up --build -d
```

### Docker: port 8000 zajęty

**Rozwiązanie:**
```bash
docker compose down --remove-orphans
docker compose up --build -d
```

### Moduł kart na hoście, bank w Dockerze (Windows)

Jeśli moduł kart działa na `localhost:8072`, a bank w Dockerze:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-cards.yml up --build -d
```

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
docker logs uk-bank-b
```

### Jak zrestartować tylko aplikację (bez bazy)?

```bash
docker compose restart uk-bank-b
```

### Jak wejść do bazy danych PostgreSQL?

```bash
docker exec -it uk-bank-b-main-postgres-1 psql -U bank_user -d bank_db
```

---

## 10. Struktura projektu

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
│       ├── cards.html            # Wyrabianie karty + instrukcja POS
│       ├── cards_demo.html       # Demo integracji kart (prezentacja)
│       ├── transfer_internal.html # Formularz przelewu wewnętrznego
│       ├── transfer_bacs.html    # Formularz BACS
│       ├── transfer_fps.html     # Formularz FPS
│       ├── transfer_chaps.html   # Formularz CHAPS
│       └── transfer_swift.html   # Formularz SWIFT
├── application/                  # Logika biznesowa (Use Cases)
│   ├── card_service.py           # Wydawanie kart (Payment Gateway)
│   ├── card_settlement_service.py # Capture / authorize / refund
│   ├── auth_service.py           # Rejestracja i logowanie (JWT + bcrypt)
│   ├── internal_transfer.py      # Przelew wewnętrzny
│   └── ...
├── infrastructure/
│   ├── card_gateway_client.py    # Klient REST + HMAC do modułu kart
│   ├── postgresql_repository.py  # Baza PostgreSQL
│   └── ...
├── scripts/
│   ├── start-demo.ps1            # Uruchomienie pełnego demo (bank + karty)
│   ├── connect-cards-network.ps1 # Sieć cards-backend (settlement)
│   ├── demo_test.py              # Test połączenia bank ↔ gateway
│   ├── test_issue_card.py        # Test wydania karty (HMAC)
│   └── test_card_e2e.py          # Test E2E: wydanie → POS → settlement
├── docker-compose.yml            # UK Bank B + sieć cards-backend
├── Dockerfile                    # Budowa obrazu aplikacji
└── requirements.txt              # Lista bibliotek Python
```

---

## Podsumowanie

Gratulacje! 🎉 Uruchomiłeś w pełni funkcjonalny system bankowy z:

- ✅ Rejestracją i logowaniem (JWT + bcrypt)
- ✅ 5 typami przelewów (Internal, BACS, FPS, CHAPS, SWIFT)
- ✅ **Integracją z modułem kart płatniczych (Payment Gateway + POS + settlement)**
- ✅ Stroną wyrabiania kart: http://localhost:8000/karta
- ✅ Graficznym interfejsem użytkownika
- ✅ Bazą danych PostgreSQL
- ✅ Stroną demo do prezentacji: http://localhost:8000/demo-karty

**Aplikacja dostępna pod adresem:** http://localhost:8000

**Demo kart (prezentacja):** http://localhost:8000/demo-karty

**Dokumentacja API (dla programistów):** http://localhost:8000/docs
