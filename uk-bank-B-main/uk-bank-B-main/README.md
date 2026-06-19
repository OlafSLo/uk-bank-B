# UK Bank B — System Bankowości Internetowej

> **Symulacja brytyjskiego systemu bankowego** obsługująca 5 typów przelewów:
> Wewnętrzny (On-us), BACS, FPS, CHAPS i SWIFT.
>
> Aplikacja działa w **Dockerze** — nie musisz instalować Pythona, PostgreSQL ani
> żadnych bibliotek na swoim komputerze. Potrzebujesz tylko Dockera.

---

## Spis treści

1. [Czym jest ten projekt?](#1-czym-jest-ten-projekt)
2. [Mapa portów — sala (każdy po kolei)](#mapa-portów--sala-każdy-po-kolei-na-końcu-wszystko-działa)
3. [Czego potrzebujesz? (Prerequisites)](#2-czego-potrzebujesz-prerequisites)
4. [Krok po kroku — uruchomienie](#3-krok-po-kroku--uruchomienie)
5. [Integracja z modułem kart płatniczych](#4-integracja-z-modułem-kart-płatniczych) ⭐ **NOWOŚĆ**
6. [Integracja z UK Payment Systems (BACS/FPS/CHAPS)](#5-integracja-z-uk-payment-systems-bacsfpschaps) ⭐ **NOWOŚĆ**
7. [Integracja z siecią SWIFT (ISO 20022)](#6-integracja-z-siecią-swift-iso-20022) ⭐ **NOWOŚĆ**
8. [Scenariusz prezentacji dla wykładowcy](#7-scenariusz-prezentacji-dla-wykładowcy)
9. [Jak korzystać z aplikacji?](#8-jak-korzystać-z-aplikacji)
10. [Dostępne typy przelewów](#9-dostępne-typy-przelewów)
11. [Wersje języków i narzędzi](#10-wersje-języków-i-narzędzi)
12. [Problemy i rozwiązania (Troubleshooting)](#11-problemy-i-rozwiązania-troubleshooting)
13. [Struktura projektu](#12-struktura-projektu)

---

## Mapa portów — sala: każdy po kolei, na końcu wszystko działa

**Scenariusz:** jeden komputer w sali. Podchodzicie **po kolei** — każdy uruchamia **tylko swoje** repozitorium (`docker compose up`). **Nie zatrzymuj** tego, co odpalili koledzy (`docker compose down` tylko u siebie, na koniec zajęć).

Gdy wszyscy skończą, **wszystkie systemy działają naraz** i można robić przelewy między bankami, KLIK, karty itd.

| Kto | Repo | Porty | Co wpisuje |
|-----|------|-------|------------|
| Zespół UKPS | `noradenshi/uk-payment-systems` | 8420, 8421, 8422 | `docker compose -f compose.yml up -d` |
| Zespół kart | `FilipSl3/Karty-Platnicze…` | 8072, 3072 | `docker compose up -d` |
| Zespół Alice Bank | `p-poweska/uk-bank-system` | 8001, 5173 | `docker compose up -d` |
| Zespół SWIFT | `Jkwasnyy/SWIFT-Aplikacje…` | 3000 | `docker compose up -d` |
| **Ty (UK Bank B)** | **ten projekt** | **8010, 8102, 8175, 5438** | patrz niżej |

Każdy projekt ma **inne porty** — dlatego możecie dokładać kolejne systemy bez kolizji.

> **KLIK:** masz go **wbudowanego** w swój `docker compose` (8102 / 8175). Nie odpalaj osobnego repo KLIK na :8000.

### Twoja kolej — UK Bank B

```powershell
.\scripts\start-my-bank.ps1
```

Albo ręcznie:

```powershell
.\scripts\school-ports.ps1 -Check          # tylko TWOJE porty muszą być wolne
docker compose up --build -d
.\scripts\connect-cards-network.ps1        # gdy zespół kart już odpalił moduł
```

**Sprawdź postęp sali** (co już działa, czego brakuje):

```powershell
.\scripts\school-ports.ps1 -Status
```

Gdy wszystkie wiersze = `DZIALA`, pełna integracja: http://localhost:8010/integracje

<details>
<summary>Opcja: jedna osoba odpala wszystko (start-full-stack.ps1)</summary>

Jeśli ćwiczysz sam w domu, możesz uruchomić cały ekosystem jednym skryptem:

```powershell
.\scripts\start-full-stack.ps1
```

Zatrzymanie: `.\scripts\stop-full-stack.ps1`

</details>

Porty można nadpisać w `.env` (`BANK_PORT`, `KLIK_WEB_PORT`, `KLIK_AGENT_PORT`).

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

**Integracja z UK Payment Systems** (repozytorium kolegów – BACS, FPS, CHAPS):
- przelewy międzybankowe przez REST API (`noradenshi/uk-payment-systems`),
- auto-rejestracja banku i klucze API Bearer,
- konta testowe Barclays/HSBC/Lloyds/Alice Bank.

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

**W sali (Twoja kolej — reszta może już działać u kolegów):**

```powershell
.\scripts\start-my-bank.ps1
```

**Sam w domu (tylko Twój bank + KLIK):**

```powershell
.\scripts\school-ports.ps1 -Check
docker compose up --build -d
```

> Przy pierwszym buildzie pobiera KLIK z GitHuba (5–15 min). Kolejne starty: ~1–2 min.

### Krok 4: Sprawdź czy działa

W terminalu wpisz:

```bash
docker ps
```

Powinieneś zobaczyć m.in. kontenery `uk-bank-b`, `klik-web`, `klik-agent` ze statusem **Up**.

> **Uwaga:** Sam bank można uruchomić bez modułu kart (tylko przelewy).
> Aby **karty działały**, wykonaj dodatkowo sekcję [Integracja z modułem kart](#4-integracja-z-modułem-kart-płatniczych).

### Krok 5: Otwórz aplikację w przeglądarce

Otwórz przeglądarkę (Chrome, Firefox, Edge) i wpisz w pasku adresu:

```
http://localhost:8010
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
| **UK Bank B (GUI)** | http://localhost:8010 | Logowanie, dashboard, przelewy |
| **Integracja (status)** | http://localhost:8010/integracje | Status wszystkich systemów |
| **Wyrabianie karty** | http://localhost:8010/karta | Wydanie karty + instrukcja POS |
| **Strona demo** | http://localhost:8010/demo-karty | Status integracji + szybki test API |
| **Terminal POS** | http://localhost:8072/pos | Płatność kartą (symulacja sklepu) |
| **Swagger kart** | http://localhost:8072/docs | API Payment Gateway |
| **Panel admina kart** | http://localhost:3072 | admin / admin123 |
| **Swagger banku** | http://localhost:8010/docs | API UK Bank B (capture, authorize) |

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

1. Otwórz http://localhost:8010/login
2. Zaloguj się (lub zarejestruj konto na `/register`).
3. Na Dashboard zobaczysz konto demo `102030-11111111` ze saldem **£5000**.

#### Krok 2 – Wydaj kartę

1. W menu kliknij **Karty** (adres: http://localhost:8010/karta).
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
2. Odśwież **Dashboard** (http://localhost:8010/dashboard).
3. Saldo konta `11111111` powinno spaść o kwotę płatności (np. z £5000 na £4950).

#### Krok 5 – Sync saldo (po wpłacie na konto)

Jeśli zrobiłeś przelew na konto i chcesz zaktualizować limit na karcie PREPAID:

1. Wejdź na http://localhost:8010/karta
2. Przy karcie kliknij **Sync saldo**
3. Saldo karty w module kart zrówna się z saldem konta bankowego

#### Test bez GUI (skrypty)

| Skrypt | Co robi |
|--------|---------|
| `python scripts\demo_test.py` | Sprawdza czy bank i gateway odpowiadają |
| `python scripts\test_issue_card.py` | Wydaje kartę przez HMAC (tylko gateway) |
| `python scripts\test_card_e2e.py` | Pełny test: wydanie → POS → settlement |
| `POST http://localhost:8010/api/integration/test` | Test API (Swagger / demo-karty) |

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

## 5. Integracja z UK Payment Systems (BACS/FPS/CHAPS)

UK Bank B łączy się przez **REST API** z symulatorem brytyjskich systemów płatniczych
z repozytorium kolegów: [noradenshi/uk-payment-systems](https://github.com/noradenshi/uk-payment-systems).
Integracja jest **tylko po stronie UK Bank B** – repozytorium UKPS nie modyfikujemy.

| Parametr | Wartość UK Bank B |
|----------|-------------------|
| Nazwa banku | `UK Bank B` |
| BIC | `UKBKGB01XXX` |
| Sort code | `10-20-30` |
| CHAPS | port hosta `8420` (lub `8080` w README UKPS) |
| FPS | port hosta `8421` (lub `8081`) |
| BACS | port hosta `8422` (lub `8082`) |

Dokumentacja API po stronie UKPS: [Przewodnik integracji bankowej (PL)](https://github.com/noradenshi/uk-payment-systems/blob/main/docs/integrations/bank_pl.md).

### Szybki start (2 kroki)

**Krok 1 – UKPS u kolegów** (osobne repo, bez zmian u nich):

```bash
git clone https://github.com/noradenshi/uk-payment-systems
cd uk-payment-systems
docker compose up -d
```

Sprawdź health checki (u Ciebie UKPS mapuje porty na **8420/8421/8422**):
- CHAPS: http://localhost:8420/v1/healthz
- FPS: http://localhost:8421/v1/healthz
- BACS: http://localhost:8422/v1/healthz

**Krok 2 – UK Bank B**:

```bash
cd uk-bank-B-main/uk-bank-B-main
docker compose up --build -d
```

Przy starcie bank **automatycznie rejestruje się** w CHAPS, FPS i BACS (`POST /v1/participants/register`)
i zapisuje klucze API w pliku `data/ukps_api_keys.json` (żeby działało po restarcie).

**Test:**

```bash
python scripts/test_ukps_e2e.py
```

### Jak to działa

```
┌─────────────────┐   Bearer token    ┌──────────────────────┐
│  UK Bank B GUI  │ ────────────────► │  UKPS (3 usługi)     │
│  /transfer/fps  │  POST /v1/payments│  :8080 CHAPS         │
│  /transfer/chaps│                   │  :8081 FPS           │
│  /transfer/bacs │                   │  :8082 BACS          │
└────────┬────────┘                   └──────────────────────┘
         │ obciążenie konta klienta (PostgreSQL)
         ▼
   Saldo spada na Dashboard
```

- **FPS / CHAPS** – JSON `POST /v1/payments/fps` lub `/chaps` z `receiver_bic`, `receiver_sort_code`, `amount`, `msg_id`.
- **BACS** – plik **Standard 18** (`text/plain`) na `POST /v1/payments/bacs/submit`.
- BIC nadawcy i klucz API są wyprowadzane z rejestracji – nie trzeba ich podawać w każdym żądaniu.

### Konta testowe w UKPS (banki seed)

| Bank | Sort code | BIC |
|------|-----------|-----|
| Barclays | `20-00-00` | `BARCGB2L` |
| HSBC | `40-00-00` | `HSBCGB44` |
| Lloyds | `30-00-00` | `LLOYGB21` |
| Alice Bank | `60-00-00` | `SNDRUK22` |

W formularzach przelewów BACS/FPS/CHAPS wpisz sort code odbiorcy z tabeli (np. `20-00-00` dla Barclays).

### Adresy po uruchomieniu

| Serwis | Adres | Opis |
|--------|-------|------|
| **Status integracji** | http://localhost:8010/integracje | CHAPS/FPS/BACS + karty + SWIFT |
| **API status UKPS** | http://localhost:8010/api/ukps/status | Rejestracja i health checki |
| **Przelew FPS** | http://localhost:8010/transfer/fps | GUI |
| **Przelew CHAPS** | http://localhost:8010/transfer/chaps | GUI |
| **Przelew BACS** | http://localhost:8010/transfer/bacs | GUI |

### Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|-------------|
| `Brak klucza API` po restarcie | Usuń `data/ukps_api_keys.json` i zrestartuj bank **albo** zresetuj bazy UKPS (`docker compose down -v` w repo UKPS) |
| `409` przy rejestracji | Bank już istnieje w UKPS – ustaw `UKPS_CHAPS_API_KEY` itd. w `.env` lub zresetuj UKPS |
| `Connection refused` na 8420–8422 | Uruchom `docker compose up -d` w repozytorium `uk-payment-systems` |
| BACS odrzucony | Sprawdź format Standard 18 – bank buduje plik automatycznie |

### Integracja z bankiem partnerskim (Alice Bank)

UK Bank B wysyła przelewy do banku kolegi ([p-poweska/uk-bank-system](https://github.com/p-poweska/uk-bank-system)) **przez UKPS** — bez zmian w ich kodzie.

| Parametr | UK Bank B (Ty) | Bank kolegi (Alice Bank) |
|----------|----------------|--------------------------|
| Aplikacja | port **8010** | port **8001** (API), **5173** (frontend) |
| BIC w UKPS | `UKBKGB01XXX` | `SNDRUK22` |
| Sort code UKPS (odbiorca) | — | **`60-00-00`** |
| Konto nadawcy (demo) | `10-20-30` / `11111111` | — |

**Mapa portów (bez kolizji):**

| Serwis | Port |
|--------|------|
| UK Bank B | **8010** |
| Bank kolegi (API) | 8001 |
| Bank kolegi (React) | 5173 |
| UKPS CHAPS / FPS / BACS | 8420 / 8421 / 8422 |
| KLIK wbudowany (API / agent) | 8102 / 8175 |
| PostgreSQL UK Bank B | 5438 |

**Uruchomienie w sali:** każdy zespół odpala swoje repo (patrz [Mapa portów](#mapa-portów--sala-każdy-po-kolei-na-końcu-wszystko-działa)). Ty na końcu: `.\scripts\start-my-bank.ps1`.

**Opcja domowa (jeden skrypt):** `.\scripts\start-full-stack.ps1`

**Ręcznie (4 repozytoria):**

```bash
# 1. UKPS (wspólna izba)
cd uk-payment-systems && docker compose up -d

# 2. Bank kolegi (u nich — Ty tylko uruchamiasz lokalnie do testu)
git clone https://github.com/p-poweska/uk-bank-system
cd uk-bank-system && docker compose up -d

# 3. Twój bank
cd uk-bank-B-main/uk-bank-B-main && docker compose up --build -d
```

**Test przelewu do banku kolegi:**

```bash
python scripts/test_peer_bank_e2e.py
```

W GUI: **Przelewy → FPS** (najszybszy), formularz ma domyślnie odbiorcę `60-00-00` (Alice Bank).

> Aby środki **pojawiły się w aplikacji kolegi**, u nich musi działać kontener `ukps-listener` i zmienna `UKPS_INBOUND_FALLBACK_ACCOUNT` (numer konta w ich bazie). To konfigurują sami — Ty tylko wysyłasz przez UKPS.

Status: http://localhost:8010/api/peer-bank/status

---

## 5.1 Integracja z KLIK-payments (płatności mobilne)

UK Bank B łączy się z symulatorem **KLIK** (odpowiednik BLIK) z repozytorium:
[MarshallBjorn/KLIK-payments](https://github.com/MarshallBjorn/KLIK-payments).
Integracja jest **tylko po stronie UK Bank B** — repozytorium KLIK nie modyfikujemy.

| Parametr | Wartość |
|----------|---------|
| Strefa | `UK` (GBP) |
| KLIK API (wbudowany) | port hosta **8102** |
| Terminal agenta (wbudowany) | http://localhost:**8175** |
| KLIK u nich (osobny Docker) | **8000** / **5175** — nie koliduje z Twoimi portami |
| Webhook bazy (w KLIK Admin) | `http://uk-bank-b:8000/api/klik/webhook` — KLIK sam dokleja `/authorize` |
| Endpoint autoryzacji | `POST /api/klik/webhook/authorize` |
| PIN demo | `1234` |
| Klucz API banku | `klik_dev_uk_bank_b_school_demo` (auto) |
| Klucz API agenta (terminal :8175) | `klik_dev_agent_uk_school_demo` (auto) |
| Konto demo | `10-20-30` / `11111111` (£5000) |

### Moduły

- **C2B (Kody)** — klient generuje 6-cyfrowy kod w `/klik`, agent (terminal) inicjuje płatność, bank autoryzuje PIN-em i wywołuje `POST /payments/confirm` do KLIK.
- **P2P (Telefony)** — rejestracja aliasu telefon→IBAN w KLIK, lookup przed przelewem na numer telefonu.

### Szybki start (szkoła — jeden Docker)

W folderze `uk-bank-B-main/uk-bank-B-main`:

```powershell
docker compose up --build -d
```

Pierwszy build **pobiera KLIK z GitHuba** (potrzebny internet). Kolejne uruchomienia działają offline.

**Ile kontenerów?** Stack uruchamia **8 usług** (9 wpisów w `docker compose`, ale `klik-init` kończy się po sekundzie — rejestracja banku w KLIK):

| Kontener | Po co |
|----------|--------|
| `uk-bank-b` | Twój bank |
| `postgres` | Baza banku |
| `klik-web` | API KLIK |
| `klik-worker` | Webhooki płatności (C2B) |
| `klik-agent` | Terminal sklepu (:8175) |
| `klik-db` / `klik-redis` / `klik-rtgs` | Baza, kolejka, mock rozliczeń KLIK |

To normalne — KLIK to osobny system (jak UKPS), nie jeden kontener.

| Adres | Opis |
|-------|------|
| http://localhost:8010/klik | Bank — kody i P2P |
| http://localhost:8175 | Terminal agenta (sklep) |
| http://localhost:8102/admin/ | Panel KLIK (opcjonalnie) |

Klucz API banku, agenta i rejestracja w KLIK są **automatyczne** (`klik-init`).

**Terminal agenta (http://localhost:8175)** — przy pierwszym wejściu wpisz:

| Pole | Wartość |
|------|---------|
| Klucz API agenta | `klik_dev_agent_uk_school_demo` |
| Strefa | **UK** |
| Base URL | `/api/v1` |

**Flow C2B:**

1. http://localhost:8010/klik → **Generuj kod** (konto `11111111`)
2. http://localhost:8175 → wpisz kod i kwotę
3. W `/klik` → **Akceptuj** PIN **`1234`**

Status: http://localhost:8010/api/klik/status

<details>
<summary>Osobny KLIK u nich na :8000 (bez wbudowanego stacku)</summary>

Uruchom tylko bank + postgres (np. wyłącz usługi `klik-*` albo osobny profil compose).
W panelu KLIK ustaw webhook:

`http://host.docker.internal:8010/api/klik/webhook`

Bank otwierasz pod **http://localhost:8010** — kolizji z ich KLIK na **8000** nie będzie.

</details>

<details>
<summary>Stara metoda (osobne repo KLIK + ręczny Admin)</summary>

```powershell
.\scripts\setup-klik.ps1
# ... ręczna konfiguracja Django Admin ...
```

</details>

---

## 6. Integracja z siecią SWIFT (ISO 20022)

UK Bank B łączy się z **middleware SWIFT** (symulator sieci międzybankowej)
z repozytorium: [Jkwasnyy/SWIFT-Aplikacje-Biznesowe](https://github.com/Jkwasnyy/SWIFT-Aplikacje-Biznesowe).
Integracja jest **tylko po stronie UK Bank B** – modułu SWIFT nie modyfikujemy.

| Parametr | Wartość UK Bank B |
|----------|-------------------|
| BIC banku | `UKBKGB01XXX` (Bank UK 1) |
| Standard komunikatu | ISO 20022 **pacs.008** (XML) |
| Autoryzacja | OAuth2 `client_credentials` (`test-client` / `test-secret`) |
| Konto nadawcy (IBAN) | `GB29NWBK60161331926819` |
| Waluty | GBP / EUR / USD |
| Opłata banku | 1% kwoty |

### Jak to działa (architektura)

```
┌──────────────────┐   1. OAuth2 token    ┌────────────────────────┐
│  UK Bank B GUI   │ ───────────────────► │  Middleware SWIFT      │
│  /transfer/swift │   2. POST            │  :3000                 │
└────────┬─────────┘   /swift/message     └───────────┬────────────┘
         │              (pacs.008 XML)                 │ 3. routing + kolejka
         │                                              │    (inbox, 5s okno)
         │  obciążenie konta (kwota + 1%)               ▼
         │                                  ┌────────────────────────┐
         │                                  │  Bank odbiorcy /receive │
         │   ◄───── 5. ACK (callback) ──────│  (mock-bank lub UK B)   │
         ▼                                  └────────────────────────┘
   saldo spada                              4. forward po ~5 s
```

**Wysyłanie (UK Bank B → świat):**

1. Klient wypełnia formularz na `/transfer/swift` (BIC odbiorcy, konto, kwota, waluta, ChrgBr).
2. Bank loguje się do middleware (`POST /auth/token`) i dostaje token + listę BIC-ów.
3. Bank buduje komunikat **pacs.008** i wysyła `POST /swift/message` (nagłówek `Authorization: Bearer`).
4. Middleware waliduje, wyznacza trasę (routing wieloskokowy), liczy opłaty i umieszcza komunikat w kolejce.
5. Po przyjęciu (202) bank **obciąża konto** (kwota + 1% opłaty) i zwraca `UETR`, trasę i podział opłat.
6. Forward do banku odbiorcy następuje automatycznie (auto-send wywołuje `POST /api/send/{uetr}`)
   albo ręcznie z panelu operatora SWIFT.

**Odbieranie (świat → UK Bank B):**

- UK Bank B wystawia endpoint **`POST /receive`** (rola banku odbiorcy w sieci).
- Middleware forwarduje tam pacs.008 z nagłówkami `X-SWIFT-*`; bank waliduje komunikat,
  **uznaje konto** w GBP (z przeliczeniem waluty) i odsyła **ACK** na `X-SWIFT-Callback-Url`.

### Endpointy zaimplementowane w UK Bank B

| Endpoint | Opis |
|----------|------|
| `POST /api/transfer/swift` | Wysyłka międzynarodowa (tryb sieciowy lub fallback do symulacji) |
| `POST /receive` (`/swift/receive`) | Odbiór przychodzącego pacs.008 + ACK |
| `GET /api/swift/status` | Status połączenia z siecią SWIFT (zdrowie + token) |
| `POST /api/swift/cancel/{uetr}` | Anulowanie przelewu w oknie kolejki |

### Szybki start

**Krok 1 – middleware SWIFT** (osobne repo, bez zmian):

```bash
git clone https://github.com/Jkwasnyy/SWIFT-Aplikacje-Biznesowe
cd SWIFT-Aplikacje-Biznesowe
docker compose up -d --build
```

Sprawdź: http://localhost:3000 (panel operatora) i http://localhost:3000/docs (Swagger).

**Krok 2 – UK Bank B**:

```bash
cd uk-bank-B-main/uk-bank-B-main
docker compose up --build -d
```

Bank łączy się z middleware przez `host.docker.internal:3000` (zmienne w `docker-compose.yml`).

**Test E2E:**

```bash
python scripts/test_swift_e2e.py
```

### Jak sprawdzić, że integracja działa (najszybciej)

**Sposób 1 – strona „Integracje” w GUI (zalecany):**

1. Zaloguj się i wejdź na **http://localhost:8010/integracje** (link **Integracje** w menu lub kafelek na Dashboardzie).
2. Strona sama odpytuje wszystkie usługi i pokazuje **kody HTTP** z zielonymi plakietkami.
3. Gdy wszystko działa, u góry zobaczysz: **„✓ Wszystkie połączenia działają (8/8 · HTTP 200)”**:

   | Grupa | Sprawdzenie | Oczekiwane |
   |-------|-------------|------------|
   | Bank | UK Bank B API | HTTP 200 |
   | Karty płatnicze | Payment Gateway (Swagger), Terminal POS, Panel admina | HTTP 200 |
   | Sieć SWIFT | Middleware API, Panel operatora, Swagger, OAuth2 (token) | HTTP 200 |

   Strona ma auto-odświeżanie co 5 s oraz przyciski do panelu SWIFT i terminala POS.
4. Na dole strony jest sekcja **„Ostatnie przelewy SWIFT”** – lista UETR, kierunek
   (⬆ wychodzący / ⬇ przychodzący), trasa, kwota i status (`completed` / `queued` /
   `incoming`) zaciągana z panelu operatora. Surowe dane: `curl http://localhost:8010/api/swift/history`.

**Sposób 2 – endpoint JSON (CLI):**

```bash
curl http://localhost:8010/api/integrations     # zwraca summary {ok, total, all_ok} + listę checków
curl http://localhost:8010/api/swift/status      # status samej sieci SWIFT + token
curl http://localhost:8010/api/swift/history     # ostatnie przelewy SWIFT (UETR + status)
```

**Sposób 3 – test automatyczny E2E:**

```bash
python scripts/test_swift_e2e.py
```

Oczekiwany wynik (wszystko `[OK]`):

```
[OK] Status integracji (bank -> SWIFT)
[OK] Wyslanie SWIFT (pacs.008 -> middleware)   # zwraca UETR + trasę
[OK] Obciazenie konta nadawcy                  # saldo spada o kwotę + 1%
[OK] Odbieranie /receive (uznanie konta)       # ACK + uznanie konta w GBP
[OK] Uznanie konta odbiorcy (+GBP)
Wynik E2E SWIFT: SUKCES
```

> Pełne dostarczenie przelewu (status **COMPLETED** w panelu :3000) wymaga działających
> banków-makiet `mock-banks`. Jeśli kontener restartuje się na Windows, zobacz
> [znany problem CRLF](#znany-problem-windows-kontener-mock-banks-restartuje-się).

### Dodawanie przelewu SWIFT – test krok po kroku (GUI)

1. Zaloguj się: http://localhost:8010/login
2. Wejdź w **Przelewy → SWIFT** lub bezpośrednio http://localhost:8010/transfer/swift
3. Po prawej zobaczysz **status sieci SWIFT** (zielony = połączono, token OK).
4. Wybierz **Bank odbiorcy (BIC)** z listy, np. `PLBKPL01XXX` – konto i waluta uzupełnią się automatycznie.
5. Podaj **kwotę** (£ z konta) i ewentualnie zmień **walutę docelową** oraz **podział opłat (ChrgBr)**.
6. Kliknij **Wyślij przez SWIFT**.
7. W wyniku zobaczysz **UETR**, **trasę** (np. `UKBKGB01XXX → PLBKPL01XXX`), kwotę u odbiorcy
   i obciążenie konta (kwota + 1%).
8. Odśwież Dashboard – saldo konta spadnie o (kwota + opłata).
9. Panel operatora SWIFT (http://localhost:3000) pokazuje komunikat w kolejce/zrealizowanych.

### Dostępne banki odbiorcze (z konfiguracji middleware)

| BIC | Bank | Przykładowe konto (open) |
|-----|------|--------------------------|
| `PLBKPL01XXX` | Bank Polska 1 | `PL61109010140000071219812874` |
| `PLBKPL02XXX` | Bank Polska 2 | `PL62109010140000071219812875` |
| `UKBKGB02XXX` | Bank UK 2 | `GB29NWBK60161331926820` |
| `USBKUS01XXX` | Bank USA 1 | `US123456789012345678901234` |
| `USBKUS02XXX` | Bank USA 2 | `US223456789012345678901234` |
| `DEBKDE01XXX` | Bank EU DE 1 | `DE89370400440532013000` |

### Znany problem (Windows): kontener `mock-banks` restartuje się

Skrypt startowy banków-makiet w repozytorium SWIFT (`scripts/start_mock_banks.sh`) bywa
zapisany z końcami linii **CRLF**, przez co w kontenerze pojawia się błąd
`set: Illegal option -` i kontener `mock-banks` wpada w pętlę restartów.

To problem **modułu SWIFT na Windows**, nie UK Bank B. Wysyłka i odbiór po stronie banku
działają (middleware przyjmuje komunikat i zwraca `UETR`), a brakuje jedynie finalnego
dostarczenia do banku-makiety. Obejście (w **swoim** klonie repo SWIFT):

```bash
# zamień CRLF -> LF w skrypcie i przebuduj
cd SWIFT-Aplikacje-Biznesowe
sed -i 's/\r$//' scripts/start_mock_banks.sh   # lub: dos2unix scripts/start_mock_banks.sh
docker compose up -d --build mock-banks
```

W repozytorium często wystarczy dodać `* text=auto eol=lf` w `.gitattributes`.

---

## 7. Scenariusz prezentacji dla wykładowcy

> **Czas:** ok. 5–7 minut  
> **Przygotowanie:** uruchom `.\scripts\start-demo.ps1` i otwórz http://localhost:8010/demo-karty

### Krok 1 – Pokaż, że systemy są połączone

1. Otwórz **http://localhost:8010/demo-karty**
2. Wszystkie statusy powinny być **zielone**
3. Kliknij **„Szybki test integracji”** – powinien zwrócić `"overall": "OK"`

### Krok 2 – Wydaj kartę klientowi

1. Zaloguj się: http://localhost:8010/login (lub zarejestruj konto)
2. Wejdź na **Karty**: http://localhost:8010/karta
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

## 8. Jak korzystać z aplikacji?

### Rejestracja konta

1. Wejdź na `http://localhost:8010/register`
2. Wpisz **nazwę użytkownika** (np. `jan`)
3. Wpisz **hasło** (minimum 4 znaki, np. `test123`)
4. Wybierz **rolę** (zostaw `customer`)
5. Kliknij **"Zarejestruj się"**
6. Zostaniesz przekierowany do strony logowania

### Logowanie

1. Wejdź na `http://localhost:8010/login`
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

1. Wejdź na http://localhost:8010/karta (menu **Karty**)
2. Wybierz konto, wpisz **4-cyfrowy PIN** i kliknij **Wydaj kartę PREPAID**
3. Zapisz **numer karty, CVV i datę ważności** (pokazane jednorazowo)
4. Użyj panelu **Terminal POS — co wpisać** albo przycisku **Wypełnij POS**
5. Płać kartą w terminalu: http://localhost:8072/pos (rok ważności: **29**, nie 2029)
6. Po wpłacie na konto użyj **Sync saldo** na stronie `/karta`
7. Status integracji: http://localhost:8010/demo-karty

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

## 9. Dostępne typy przelewów

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

## 10. Wersje języków i narzędzi

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

## 11. Problemy i rozwiązania (Troubleshooting)

### SWIFT: status „Sieć SWIFT niedostępna”

**Przyczyna:** Middleware SWIFT nie działa lub bank go nie widzi.

**Rozwiązanie:**
1. Uruchom middleware: `docker compose up -d --build` w repo SWIFT-Aplikacje-Biznesowe
2. Sprawdź: http://localhost:3000 oraz http://localhost:3000/docs
3. Status z banku: `GET http://localhost:8010/api/swift/status`
4. Test: `python scripts/test_swift_e2e.py`

> Bez middleware przelew SWIFT zadziała w **trybie symulacji** (lokalne obciążenie konta bez sieci).

### SWIFT: przelew „queued” i nie dociera do odbiorcy (Windows)

**Przyczyna:** Kontener `mock-banks` w module SWIFT restartuje się przez końce linii CRLF
w `scripts/start_mock_banks.sh` (`set: Illegal option -`).

**Rozwiązanie (w swoim klonie repo SWIFT):**
```bash
sed -i 's/\r$//' scripts/start_mock_banks.sh   # lub dos2unix
docker compose up -d --build mock-banks
```
Strona banku (wysyłka + `/receive`) działa niezależnie od tego problemu.

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

### Docker: port zajęty (8010, 8102, 8175…)

**Rozwiązanie:**
```powershell
.\scripts\school-ports.ps1 -Check
docker compose down --remove-orphans
docker compose up --build -d
```

Poprzednia osoba mogła zostawić kontenery — `docker compose down` w **każdym** uruchomionym repo.

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
3. Sprawdź czy port 8010 nie jest zajęty:
   ```bash
   netstat -ano | findstr :8010
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

**Problem**: Port 8010 lub 5432 jest już zajęty.

**Rozwiązanie**:
1. Znajdź proces: `netstat -ano | findstr :8010`
2. Zatrzymaj go lub zmień `BANK_PORT` w `.env` / `docker-compose.yml`

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

## 12. Struktura projektu

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
│       └── transfer_swift.html   # Formularz SWIFT (sieć ISO 20022)
├── application/                  # Logika biznesowa (Use Cases)
│   ├── card_service.py           # Wydawanie kart (Payment Gateway)
│   ├── card_settlement_service.py # Capture / authorize / refund
│   ├── swift_network_service.py  # Wysyłka/odbiór SWIFT (pacs.008) + uznanie konta
│   ├── swift_transfer.py         # Symulacja SWIFT (fallback bez sieci)
│   ├── auth_service.py           # Rejestracja i logowanie (JWT + bcrypt)
│   ├── internal_transfer.py      # Przelew wewnętrzny
│   └── ...
├── infrastructure/
│   ├── card_gateway_client.py    # Klient REST + HMAC do modułu kart
│   ├── swift_client.py           # Klient middleware SWIFT (OAuth2 + pacs.008)
│   ├── postgresql_repository.py  # Baza PostgreSQL
│   └── ...
├── scripts/
│   ├── start-demo.ps1            # Uruchomienie pełnego demo (bank + karty)
│   ├── connect-cards-network.ps1 # Sieć cards-backend (settlement)
│   ├── demo_test.py              # Test połączenia bank ↔ gateway
│   ├── test_issue_card.py        # Test wydania karty (HMAC)
│   ├── test_card_e2e.py          # Test E2E: wydanie → POS → settlement
│   └── test_swift_e2e.py         # Test E2E: SWIFT wyślij + odbierz
├── docker-compose.yml            # UK Bank B + integracje (karty, SWIFT)
├── Dockerfile                    # Budowa obrazu aplikacji
└── requirements.txt              # Lista bibliotek Python
```

---

## Podsumowanie

Gratulacje! 🎉 Uruchomiłeś w pełni funkcjonalny system bankowy z:

- ✅ Rejestracją i logowaniem (JWT + bcrypt)
- ✅ 5 typami przelewów (Internal, BACS, FPS, CHAPS, SWIFT)
- ✅ **Integracją z modułem kart płatniczych (Payment Gateway + POS + settlement)**
- ✅ **Integracją z siecią SWIFT (ISO 20022 pacs.008, OAuth2, /receive)**
- ✅ Stroną wyrabiania kart: http://localhost:8010/karta
- ✅ Graficznym interfejsem użytkownika
- ✅ Bazą danych PostgreSQL
- ✅ Stroną demo do prezentacji: http://localhost:8010/demo-karty

**Aplikacja dostępna pod adresem:** http://localhost:8010

**Demo kart (prezentacja):** http://localhost:8010/demo-karty

**Dokumentacja API (dla programistów):** http://localhost:8010/docs
