import time
from fastapi import FastAPI, HTTPException, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from decimal import Decimal
from contextlib import asynccontextmanager
from typing import Optional
import os
import random

from domain.value_objects import AccountNumber, Money, Currency
from domain.entities import Account, User, Card
from application.internal_transfer import InternalTransferUseCase
from application.auth_service import AuthUseCase, AuthService
from infrastructure.postgresql_repository import PostgreSQLAccountRepository, PostgreSQLUserRepository, PostgreSQLTransactionRepository, PostgreSQLCardRepository
from infrastructure.card_gateway_client import CardGatewayClient
from infrastructure.swift_client import SwiftMiddlewareClient
from infrastructure.ukps_client import ChapsClient, FpsClient, BacsClient
from infrastructure.peer_bank_client import PeerBankClient, peer_bank_config
from infrastructure.klik_client import KlikClient, klik_config
from application.klik_service import KlikService
from application.swift_network_service import SwiftNetworkService
from application.bacs_transfer import BACSTransferUseCase
from application.fps_transfer import FPSTransferUseCase
from application.chaps_transfer import CHAPSTransferUseCase
from application.swift_transfer import SWIFTTransferUseCase
from application.junior_transfer import JuniorTransferUseCase, ApproveJuniorTransferUseCase
from application.employee_service import EmployeeUseCase
from application.card_service import CardService
from application.card_settlement_service import CardSettlementService


# --- Globalne komponenty ---
repo = None
user_repo = None
auth_service = None
auth_use_case = None
transfer_service = None
bacs_service = None
fps_service = None
chaps_service = None
swift_service = None
tx_repo = None
employee_service = None
card_repo = None
card_service = None
card_settlement_service = None
card_gateway = None
swift_client = None
swift_network_service = None
chaps_ukps_client = None
fps_ukps_client = None
bacs_ukps_client = None
peer_bank_client = None
klik_client = None
klik_service = None


def setup_mock_data(repo: PostgreSQLAccountRepository, auth: AuthUseCase):
    """Inicjalizuje dane testowe w bazie, jeśli baza jest pusta."""

    # 1. Automatyczne generowanie domyślnego konta pracownika
    try:
        auth.register("pracownik", "admin123", "employee")
        print("[MOCK] Utworzono domyślne konto pracownika (pracownik / admin123)")
    except Exception:
        pass # Użytkownik już istnieje w bazie

    # Sprawdź czy konta już istnieją (z retry)
    max_retries = 10
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            import psycopg2
            conn = psycopg2.connect(repo.db_url, connect_timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM accounts")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            if count >= 2:
                print(f"[MOCK] Konta testowe już istnieją ({count}), pomijam.")
                return
            break  # Połączenie OK, tabela istnieje - wychodzimy z pętli
        except Exception as e:
            print(f"[MOCK] Próba {attempt}/{max_retries}: baza niegotowa ({e})")
            if attempt == max_retries:
                print(f"[MOCK] Nie można sprawdzić bazy po {max_retries} próbach, próbuję mimo to...")
            else:
                time.sleep(delay)

    account_1 = Account(
        id=AccountNumber(sort_code="102030", account_number="11111111"),
        balance=Money(Decimal("5000.00"), Currency.GBP),
        debt_limit=Money(Decimal("100.00"), Currency.GBP)
    )
    account_2 = Account(
        id=AccountNumber(sort_code="102030", account_number="22222222"),
        balance=Money(Decimal("1200.00"), Currency.GBP),
        debt_limit=Money(Decimal("50.00"), Currency.GBP)
    )

    # Zapisz konta testowe (z retry)
    for attempt in range(1, max_retries + 1):
        try:
            repo.save(account_1)
            repo.save(account_2)
            print(f"[MOCK] Utworzono konta testowe: 11111111 (£5000), 22222222 (£1200)")
            return
        except Exception as e:
            print(f"[MOCK] Próba {attempt}/{max_retries}: błąd zapisu ({e})")
            if attempt == max_retries:
                print(f"[MOCK] Nie udało się zapisać kont testowych po {max_retries} próbach!")
                raise
            time.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global repo, user_repo, auth_service, auth_use_case
    global transfer_service, bacs_service, fps_service, chaps_service, swift_service
    global tx_repo, employee_service, card_repo, card_service, card_settlement_service, card_gateway
    global swift_client, swift_network_service
    global chaps_ukps_client, fps_ukps_client, bacs_ukps_client, peer_bank_client
    global klik_client, klik_service

    repo = PostgreSQLAccountRepository()
    user_repo = PostgreSQLUserRepository()
    tx_repo = PostgreSQLTransactionRepository()
    card_repo = PostgreSQLCardRepository()
    auth_service = AuthService()
    auth_use_case = AuthUseCase(user_repo, auth_service)

    chaps_ukps_client = ChapsClient()
    fps_ukps_client = FpsClient()
    bacs_ukps_client = BacsClient()

    # Automatyczna rejestracja w systemach UKPS
    bank_name = "UK Bank B"
    bank_bic = "UKBKGB01XXX"
    bank_sort = "10-20-30"
    init_balance = 5000000.00
    
    chaps_ukps_client.register(bank_name, bank_bic, bank_sort, init_balance)
    fps_ukps_client.register(bank_name, bank_bic, bank_sort, init_balance, participant_type="DIRECT", sponsor_bic="")
    bacs_ukps_client.register(bank_name, bank_bic, bank_sort, init_balance, su_code="123456", is_service_user=True, is_destination_user=True)

    transfer_service = InternalTransferUseCase(repo)
    bacs_service = BACSTransferUseCase(repo, bacs_ukps_client)
    fps_service = FPSTransferUseCase(repo, fps_ukps_client)
    chaps_service = CHAPSTransferUseCase(repo, chaps_ukps_client)
    swift_service = SWIFTTransferUseCase(repo)
    employee_service = EmployeeUseCase(repo)
    card_service = CardService(repo, card_repo)
    card_settlement_service = CardSettlementService(repo, card_repo)
    card_gateway = CardGatewayClient()
    swift_client = SwiftMiddlewareClient()
    swift_network_service = SwiftNetworkService(repo, swift_client)
    peer_bank_client = PeerBankClient()
    klik_client = KlikClient()
    klik_service = KlikService(repo, klik_client)

    setup_mock_data(repo, auth_use_case)
    yield


app = FastAPI(title="UK Bank System API", lifespan=lifespan)

# --- Konfiguracja szablonów i plików statycznych ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "api", "templates"))
static_dir = os.path.join(BASE_DIR, "api", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# --- Helper: pobieranie zalogowanego użytkownika z tokena ---
def get_current_user(request: Request) -> Optional[User]:
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        return auth_use_case.get_user_from_token(token)
    except:
        return None


# ========================
#       STRONY GUI
# ========================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"request": request})


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
def register_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "register.html", {"request": request})


def _load_user_accounts():
    acc1 = repo.get_by_id(AccountNumber("102030", "11111111"))
    acc2 = repo.get_by_id(AccountNumber("102030", "22222222"))
    accounts = [a for a in [acc1, acc2] if a]
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(repo.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT sort_code, account_number FROM accounts WHERE parent_account_number = '11111111'")
        for row in cursor.fetchall():
            ja = repo.get_by_id(AccountNumber(row["sort_code"], row["account_number"]))
            if ja:
                accounts.append(ja)
        cursor.close()
        conn.close()
    except Exception as e:
        print("Błąd pobierania kont junior:", e)
    return accounts


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if user.role.value == "employee":
        return RedirectResponse(url="/back-office", status_code=302)

    accounts = _load_user_accounts()
    cards_by_account = {
        acc.id.account_number: card_service.get_cards_for_account(acc.id.account_number)
        for acc in accounts
    }

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "user": user,
        "accounts": accounts,
        "cards_by_account": cards_by_account,
        "pos_url": os.getenv("CARD_POS_URL", "http://localhost:8072/pos"),
    })


@app.get("/karta", response_class=HTMLResponse, include_in_schema=False)
def cards_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user.role.value == "employee":
        return RedirectResponse(url="/back-office", status_code=302)

    accounts = _load_user_accounts()
    cards_by_account = {}
    gateway_balances = {}
    for acc in accounts:
        cards = card_service.get_cards_for_account(acc.id.account_number)
        cards_by_account[acc.id.account_number] = cards
        for c in cards:
            if c.card_token:
                try:
                    st = card_gateway.get_card_status(c.card_token)
                    gateway_balances[c.card_token] = st.get("balance", 0)
                except Exception:
                    gateway_balances[c.card_token] = None

    return templates.TemplateResponse(request, "cards.html", {
        "request": request,
        "user": user,
        "accounts": accounts,
        "cards_by_account": cards_by_account,
        "gateway_balances": gateway_balances,
        "pos_url": os.getenv("CARD_POS_URL", "http://localhost:8072/pos"),
    })


@app.get("/transfer/{transfer_type}", response_class=HTMLResponse, include_in_schema=False)
def transfer_page(request: Request, transfer_type: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if user.role.value == "employee":
        return RedirectResponse(url="/back-office", status_code=302)

    valid_types = ["internal", "bacs", "fps", "chaps", "swift"]
    if transfer_type not in valid_types:
        return HTMLResponse("Nieznany typ przelewu", status_code=404)

    return templates.TemplateResponse(request, f"transfer_{transfer_type}.html", {
        "request": request,
        "user": user,
        "transfer_type": transfer_type,
        "peer_bank": peer_bank_config() if transfer_type in ("bacs", "fps", "chaps") else None,
    })


# ========================
#   KONTO JUNIOR (Widoki)
# ========================

@app.get("/open-junior", response_class=HTMLResponse, include_in_schema=False)
def open_junior_page(request: Request):
    user = get_current_user(request)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request, "open_junior.html", {"request": request, "user": user})

@app.post("/open-junior", include_in_schema=False)
def open_junior_post(request: Request, child_name: str = Form(...), dob: str = Form(...), initial_deposit: float = Form(0.0)):
    user = get_current_user(request)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    parent_acc_num = "11111111" # W docelowym systemie pobierane z konta użytkownika
    parent_account = repo.get_by_id(AccountNumber("102030", parent_acc_num))
    
    if not parent_account:
        return HTMLResponse("<script>alert('Błąd: Konto rodzica nie istnieje.'); window.location='/dashboard';</script>")
        
    amount_to_deposit = Money(Decimal(str(initial_deposit)), Currency.GBP)
    
    try:
        if initial_deposit > 0:
            parent_account.debit(amount_to_deposit)
            repo.save(parent_account)
    except Exception as e:
        return HTMLResponse(f"<script>alert('Błąd: {str(e)}'); window.history.back();</script>")
        
    new_acc_num = str(random.randint(30000000, 39999999))
    
    new_account = Account(
        id=AccountNumber("102030", new_acc_num),
        balance=amount_to_deposit,
        debt_limit=Money(Decimal("0.00"), Currency.GBP),
        is_active=True,
        account_type="junior",
        parent_account_number=parent_acc_num
    )
    repo.save(new_account)
    return HTMLResponse(f"<script>alert('Sukces! Konto Junior dla {child_name} zostało otwarte. Pieniądze pobrano z Twojego konta. Numer konta: {new_acc_num}'); window.location='/dashboard';</script>")

@app.get("/portal-junior", response_class=HTMLResponse, include_in_schema=False)
def junior_portal(request: Request):
    """Wyświetla graficzny interfejs Portalu Junior."""
    user = get_current_user(request)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    parent_acc_num = "11111111"
    child_accounts = []
    pending_txs = []
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(repo.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT account_number, balance FROM accounts WHERE parent_account_number = %s", (parent_acc_num,))
        child_accounts = cursor.fetchall()
        
        cursor.execute("SELECT * FROM transactions WHERE transfer_type = 'JUNIOR' AND status = 'PENDING_APPROVAL'")
        all_pending = cursor.fetchall()
        
        child_acc_numbers = [c['account_number'] for c in child_accounts]
        pending_txs = [tx for tx in all_pending if tx['sender_account'] in child_acc_numbers]
        
        cursor.close()
        conn.close()
    except Exception as e:
        print("Błąd pobierania danych do portalu junior:", e)
        
    return templates.TemplateResponse(request, "junior_portal.html", {
        "request": request, 
        "user": user,
        "child_accounts": child_accounts,
        "pending_txs": pending_txs
    })

@app.get("/child-app/{account_number}", response_class=HTMLResponse, include_in_schema=False)
def child_app(request: Request, account_number: str):
    """Dedykowana aplikacja edukacyjna dla dziecka."""
    acc = repo.get_by_id(AccountNumber("102030", account_number))
    
    if not acc or acc.account_type != "junior":
        return HTMLResponse("<script>alert('Błąd: Konto nie istnieje lub nie jest kontem Junior.'); window.location='/dashboard';</script>")
        
    pending_txs = []
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(repo.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM transactions WHERE sender_account = %s AND status = 'PENDING_APPROVAL'", (account_number,))
        pending_txs = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Błąd pobierania danych do aplikacji dziecka:", e)
        
    return templates.TemplateResponse(request, "child_app.html", {
        "request": request,
        "account": acc,
        "pending_txs": pending_txs
    })


# ========================
#   BACK-OFFICE (Pracownik)
# ========================

@app.get("/back-office", response_class=HTMLResponse, include_in_schema=False)
def back_office_page(request: Request):
    user = get_current_user(request)
    if not user or user.role.value != "employee":
        return HTMLResponse("<script>alert('Brak uprawnień! Strona tylko dla pracowników banku.'); window.location='/dashboard';</script>")
    
    try:
        all_accounts = employee_service.get_all_accounts(user)
    except Exception as e:
        return HTMLResponse(f"<script>alert('Błąd: {e}'); window.location='/dashboard';</script>")
        
    return templates.TemplateResponse(request, "back_office.html", {
        "request": request,
        "user": user,
        "accounts": all_accounts
    })

@app.post("/back-office/toggle-status", include_in_schema=False)
def toggle_account_status(request: Request, sort_code: str = Form(...), account_number: str = Form(...), is_active: bool = Form(...)):
    user = get_current_user(request)
    try:
        employee_service.toggle_account_status(user, sort_code, account_number, is_active)
        status_str = "odblokowane" if is_active else "zamrożone (zablokowane)"
        return HTMLResponse(f"<script>alert('Konto {account_number} zostało {status_str}.'); window.location='/back-office';</script>")
    except Exception as e:
        return HTMLResponse(f"<script>alert('Błąd: {e}'); window.location='/back-office';</script>")

@app.post("/back-office/set-limit", include_in_schema=False)
def set_debt_limit(request: Request, sort_code: str = Form(...), account_number: str = Form(...), limit_amount: float = Form(...)):
    user = get_current_user(request)
    try:
        employee_service.set_debt_limit(user, sort_code, account_number, Decimal(str(limit_amount)))
        return HTMLResponse(f"<script>alert('Limit zadłużenia (overdraft) dla konta {account_number} został ustawiony na £{limit_amount}.'); window.location='/back-office';</script>")
    except Exception as e:
        return HTMLResponse(f"<script>alert('Błąd: {e}'); window.location='/back-office';</script>")


@app.get("/logout", include_in_schema=False)
def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("token")
    return resp


# ========================
#   ENDPOINTY FORMULARZY
# ========================

@app.post("/auth/register", include_in_schema=False)
def register_form(username: str = Form(...), password: str = Form(...), role: str = Form("customer")):
    try:
        result = auth_use_case.register(username, password, role)
        return RedirectResponse(url="/login?registered=1", status_code=302)
    except ValueError as e:
        return HTMLResponse(f"<script>alert('{e}'); window.location='/register';</script>", status_code=400)
    except Exception as e:
        return HTMLResponse(f"<script>alert('Błąd: {e}'); window.location='/register';</script>", status_code=400)


@app.post("/auth/login", include_in_schema=False)
def login_form(username: str = Form(...), password: str = Form(...)):
    try:
        result = auth_use_case.login(username, password)
        resp = RedirectResponse(url="/dashboard", status_code=302)
        resp.set_cookie(key="token", value=result["token"], httponly=True, max_age=28800)
        return resp
    except ValueError as e:
        return HTMLResponse(f"<script>alert('{e}'); window.location='/login';</script>", status_code=400)
    except Exception as e:
        return HTMLResponse(f"<script>alert('Błąd: {e}'); window.location='/login';</script>", status_code=400)


# ========================
#   API JSON (dla GUI AJAX)
# ========================

class TransferRequest(BaseModel):
    from_sort_code: str
    from_account: str
    to_sort_code: str
    to_account: str
    amount: Decimal


class SWIFTTransferRequest(BaseModel):
    from_sort_code: str
    from_account: str
    to_sort_code: str
    to_account: str
    amount: Decimal
    to_currency: str = "GBP"
    # Pola sieci SWIFT (opcjonalne – fallback do symulacji jeśli puste)
    receiver_bic: Optional[str] = None
    receiver_name: Optional[str] = None
    sender_name: Optional[str] = None
    charge_bearer: Optional[str] = "SHAR"
    remittance_info: Optional[str] = None
    use_network: bool = True
    auto_send: bool = True

@app.get("/api/account/{sort_code}/{account_number}")
def api_get_account(sort_code: str, account_number: str):
    """Zwraca dane konta w formacie JSON (dla AJAX w GUI)."""
    acc_id = AccountNumber(sort_code, account_number)
    account = repo.get_by_id(acc_id)
    if not account:
        raise HTTPException(status_code=404, detail="Konto nie znalezione")
    return {
        "sort_code": account.id.sort_code,
        "account_number": account.id.account_number,
        "balance": float(account.balance.amount),
        "currency": account.balance.currency.value,
        "is_active": account.is_active,
        "debt_limit": float(account.debt_limit.amount)
    }


@app.post("/api/transfer/internal")
def api_internal_transfer(req: TransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        receiver = AccountNumber(req.to_sort_code, req.to_account)
        money = Money(req.amount, Currency.GBP)
        transfer_service.execute(sender, receiver, money)
        return {"status": "SUCCESS", "message": "Przelew wewnętrzny wykonany pomyślnie"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/transfer/bacs")
def api_bacs_transfer(req: TransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        money = Money(req.amount, Currency.GBP)
        result = bacs_service.execute(
            from_account_id=sender,
            to_sort_code=req.to_sort_code,
            to_account_number=req.to_account,
            amount=money
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/transfer/fps")
def api_fps_transfer(req: TransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        money = Money(req.amount, Currency.GBP)
        result = fps_service.execute(
            from_account_id=sender,
            to_sort_code=req.to_sort_code,
            to_account_number=req.to_account,
            amount=money
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/demo-karty", response_class=HTMLResponse, include_in_schema=False)
def cards_demo_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    gateway_url = os.getenv("CARD_GATEWAY_URL", "http://localhost:8072")
    public_gateway = gateway_url.replace("payment-gateway:8000", "localhost:8072")
    return templates.TemplateResponse(request, "cards_demo.html", {
        "request": request,
        "user": user,
        "gateway_url": public_gateway,
        "gateway_docs": f"{public_gateway}/docs",
        "pos_url": f"{public_gateway}/pos",
        "admin_panel_url": os.getenv("CARD_ADMIN_PANEL_URL", "http://localhost:3072"),
    })


@app.get("/api/integration/status")
def integration_status():
    """Status integracji – do strony demo i monitoringu."""
    import requests as http_requests

    gateway = card_gateway.health_check() if card_gateway else {"ok": False}
    public_gateway = gateway.get("url", "http://localhost:8072").replace(
        "payment-gateway:8000", "localhost:8072"
    ).replace("host.docker.internal", "localhost")
    admin_url = os.getenv("CARD_ADMIN_PANEL_URL", "http://localhost:3072").replace(
        "host.docker.internal", "localhost"
    )

    pos_ok = admin_ok = False
    try:
        pos_ok = http_requests.get(f"{public_gateway}/pos", timeout=4).status_code == 200
    except Exception:
        pass
    try:
        admin_ok = http_requests.get(admin_url, timeout=4).status_code == 200
    except Exception:
        pass

    return {
        "bank": {"ok": True, "url": _bank_public_url()},
        "card_gateway": gateway,
        "pos": {"ok": pos_ok, "url": f"{public_gateway}/pos"},
        "admin_panel": {"ok": admin_ok, "url": admin_url},
        "integration": {
            "bank_id": "UK_BANK_B",
            "api_key": os.getenv("CARD_API_KEY", "bank-key-uk-b"),
            "bin_prefix": "460001",
            "currency": "GBP",
            "capture_endpoint": "POST http://uk-bank-b:8000/capture",
            "hint": "Uruchom scripts/connect-cards-network.ps1 po starcie modulu kart",
        },
    }


@app.post("/api/integration/test")
def integration_test():
    """Szybki test integracji – do prezentacji na zajęciach."""
    results = {"steps": []}

    gw = card_gateway.health_check()
    results["steps"].append({
        "name": "Payment Gateway dostępny",
        "ok": gw.get("ok", False),
        "detail": gw,
    })
    if not gw.get("ok"):
        results["overall"] = "FAIL"
        return results

    try:
        issued = card_gateway.issue_card(
            user_id="demo_test",
            account_id="11111111",
            card_type="PREPAID",
            initial_balance=100.0,
        )
        card_gateway.prepare_prepaid_for_payments(issued["card_token"])
        test_card = Card(
            card_number=issued["full_pan"],
            account_number="11111111",
            expiry_date=f"{issued['expiry_month']:02d}/{issued['expiry_year']}",
            cvv=issued["cvv"],
            pin_hash="demo",
            card_token=issued["card_token"],
            gateway_status="ACTIVE",
            masked_pan=issued.get("masked_pan", ""),
            expiry_month=issued["expiry_month"],
            expiry_year=issued["expiry_year"],
        )
        card_repo.save(test_card)
        results["steps"].append({
            "name": "Wydanie karty PREPAID (HMAC)",
            "ok": True,
            "detail": {
                "card_token": issued["card_token"],
                "masked_pan": issued.get("masked_pan"),
                "full_pan": issued.get("full_pan"),
                "cvv": issued.get("cvv"),
                "expiry": f"{issued.get('expiry_month'):02d}/{issued.get('expiry_year')}",
            },
        })
        capture = card_settlement_service.capture(
            authorization_code="DEMO-AUTH-TEST",
            amount=10.0,
            currency="GBP",
            card_token=issued["card_token"],
            transaction_id="demo-tx-001",
        )
        results["steps"].append({
            "name": "Capture (settlement) – obciążenie konta",
            "ok": capture.get("status") == "SETTLED",
            "detail": capture,
        })
    except Exception as exc:
        results["steps"].append({"name": "Test end-to-end", "ok": False, "detail": str(exc)})

    results["overall"] = "OK" if all(s["ok"] for s in results["steps"]) else "FAIL"
    return results


# ========================
#   KARTY PŁATNICZE (API)
# ========================

class CaptureRequest(BaseModel):
    authorization_code: str
    transaction_id: str | None = None
    amount: float
    currency: str = "GBP"
    merchant_id: str | None = None
    card_token: str | None = None


class AuthorizeRequest(BaseModel):
    account_id: str
    amount: float
    currency: str = "GBP"
    transaction_id: str
    merchant_name: str | None = None


class RefundRequest(BaseModel):
    account_id: str
    amount: float
    currency: str = "GBP"
    original_transaction_id: str


@app.post("/capture")
@app.post("/api/v1/capture")
def card_capture(req: CaptureRequest):
    """Settlement z modułu kart – obciążenie konta klienta."""
    return card_settlement_service.capture(
        authorization_code=req.authorization_code,
        amount=req.amount,
        currency=req.currency,
        card_token=req.card_token,
        transaction_id=req.transaction_id,
    )


@app.post("/api/v1/authorize")
def card_authorize(req: AuthorizeRequest):
    """Autoryzacja środków (kontrakt modułu kart – na przyszłość)."""
    return card_settlement_service.authorize(
        account_id=req.account_id,
        amount=req.amount,
        currency=req.currency,
        transaction_id=req.transaction_id,
        merchant_name=req.merchant_name,
    )


@app.post("/refund")
@app.post("/api/v1/refund")
def card_refund(req: RefundRequest):
    return card_settlement_service.refund(
        account_id=req.account_id,
        amount=req.amount,
        currency=req.currency,
        original_transaction_id=req.original_transaction_id,
    )


@app.post("/api/cards/issue")
def issue_new_card(
    request: Request,
    sort_code: str = Form(...),
    account_number: str = Form(...),
    pin: str = Form(...),
):
    try:
        user = get_current_user(request)
        user_id = user.username if user else "customer"
        card = card_service.issue_card(sort_code, account_number, pin, user_id=user_id)
        return {
            "status": "SUCCESS",
            "message": "Karta wydana przez moduł kart płatniczych (Payment Gateway).",
            "card_number": card.card_number,
            "card_token": card.card_token,
            "masked_pan": card.masked_pan,
            "expiry_date": card.expiry_date,
            "expiry_month": card.expiry_month,
            "expiry_year": card.expiry_year,
            "cvv": card.cvv,
            "gateway_status": card.gateway_status,
            "pos_hint": {
                "card_number": card.card_number,
                "expiry_month": card.expiry_month,
                "expiry_year": card.expiry_year,
                "cvv": card.cvv,
                "amount_example": "50.00",
                "note": "W POS: rok ważności to 2 cyfry (np. 29, NIE 2029). Kwota <= saldo karty.",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/cards/sync-balance")
def sync_card_balance(card_token: str = Form(...)):
    try:
        new_balance = card_service.sync_card_balance(card_token)
        return {"status": "SUCCESS", "new_balance": new_balance}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/cards/block")
def block_card_endpoint(card_number: str = Form(...)):
    try:
        card_service.block_card(card_number)
        return {"status": "SUCCESS", "message": "Karta została pomyślnie zastrzeżona."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/cards/{account_number}")
def get_cards(account_number: str):
    cards = card_service.get_cards_for_account(account_number)
    return [
        {
            "card_number": f"**** **** **** {c.card_number[-4:]}",
            "full_card_number": c.card_number,
            "expiry_date": c.expiry_date,
            "is_active": c.is_active,
            "card_type": c.card_type,
            "daily_limit": float(c.daily_limit.amount) if c.daily_limit else None,
            "card_token": c.card_token,
            "gateway_status": c.gateway_status,
            "masked_pan": c.masked_pan,
        } for c in cards
    ]


@app.post("/api/transfer/chaps")
def api_chaps_transfer(req: TransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        money = Money(req.amount, Currency.GBP)
        result = chaps_service.execute(
            from_account_id=sender,
            to_sort_code=req.to_sort_code,
            to_account_number=req.to_account,
            amount=money
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/transfer/swift")
def api_swift_transfer(req: SWIFTTransferRequest):
    sender = AccountNumber(req.from_sort_code, req.from_account)
    money = Money(req.amount, Currency.GBP)

    # Tryb sieciowy: realny komunikat ISO 20022 do middleware SWIFT
    receiver_bic = (req.receiver_bic or req.to_sort_code or "").strip().upper()
    if req.use_network and receiver_bic:
        try:
            return swift_network_service.send_international(
                from_account_id=sender,
                receiver_bic=receiver_bic,
                receiver_account=req.to_account,
                amount=money,
                to_currency=req.to_currency,
                receiver_name=req.receiver_name or "Beneficiary",
                sender_name=req.sender_name or "UK Bank B Customer",
                charge_bearer=(req.charge_bearer or "SHAR"),
                remittance_info=req.remittance_info or "",
                auto_send=req.auto_send,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"SWIFT middleware niedostępny: {e}")

    # Fallback: lokalna symulacja (bez sieci SWIFT)
    try:
        result = swift_service.execute(
            from_account_id=sender,
            to_sort_code=req.to_sort_code,
            to_account_number=req.to_account,
            amount=money,
            to_currency=req.to_currency
        )
        result["network"] = "SIMULATION (middleware wyłączony)"
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/swift/cancel/{uetr}")
def api_swift_cancel(uetr: str):
    try:
        return swift_network_service.cancel(uetr)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ukps/status")
def api_ukps_status():
    """Status integracji z UK Payment Systems (CHAPS, FPS, BACS)."""
    services = {}
    for name, client in (
        ("chaps", chaps_ukps_client),
        ("fps", fps_ukps_client),
        ("bacs", bacs_ukps_client),
    ):
        if client:
            health = client.health_check()
            health["url"] = _public_url(health.get("url", ""))
            services[name] = health
        else:
            services[name] = {"ok": False, "registered": False}
    all_ok = all(s.get("ok") and s.get("registered") for s in services.values())
    return {
        "bank": {
            "name": "UK Bank B",
            "bic": "UKBKGB01XXX",
            "sort_code": "10-20-30",
        },
        "services": services,
        "all_ok": all_ok,
        "docs": "https://github.com/noradenshi/uk-payment-systems/blob/main/docs/integrations/bank_pl.md",
        "test_accounts": {
            "barclays": "20-00-00",
            "hsbc": "40-00-00",
            "lloyds": "30-00-00",
            "alice_bank": "60-00-00",
            "peer_bank": peer_bank_config(),
        },
    }


@app.get("/api/peer-bank/status")
def api_peer_bank_status():
    """Status banku partnerskiego (Alice Bank / uk-bank-system) i dane routingu UKPS."""
    peer = peer_bank_client.health_check() if peer_bank_client else {"ok": False}
    ukps_ok = False
    if fps_ukps_client:
        ukps_ok = fps_ukps_client.health_check().get("ok", False)
    cfg = peer_bank_config()
    return {
        "peer_bank": peer,
        "ukps_reachable": ukps_ok,
        "how_to_send": {
            "routing": "UKPS (CHAPS / FPS / BACS)",
            "receiver_sort_code_ukps": cfg["ukps_sort_code"],
            "receiver_bic": cfg["bic"],
            "sender_sort_code": "10-20-30",
            "sender_account": "11111111",
            "do_not_use_sort_code": cfg["customer_sort_code"],
            "do_not_use_reason": (
                f"{cfg['customer_sort_code']} to sort code KONTA KLIENTA w Lyo Bank — "
                "nie adres banku w UKPS. Wysylaj na 60-00-00 (SNDRUK22)."
            ),
            "credit_peer_account": (
                "U kolegi w .env ustaw UKPS_INBOUND_FALLBACK_ACCOUNT=<numer konta, np. 01246624> "
                "i zrestartuj kontener ukps-listener. FPS nie niesie numeru konta w UKPS."
            ),
        },
        "ports": _school_ports(),
        "repo": cfg["repo"],
    }


# ========================
#   KLIK (płatności mobilne)
# ========================

class KlikGenerateCodeRequest(BaseModel):
    sort_code: str = "10-20-30"
    account_number: str = "11111111"


class KlikPinRequest(BaseModel):
    pin: str = "1234"


class KlikAliasRequest(BaseModel):
    sort_code: str = "10-20-30"
    account_number: str = "11111111"
    phone: str


class KlikP2PRequest(BaseModel):
    from_sort_code: str = "10-20-30"
    from_account: str = "11111111"
    phone: str
    amount: Decimal


@app.get("/api/klik/status")
def api_klik_status():
    status = klik_client.health_check() if klik_client else {"ok": False}
    cfg = klik_config()
    return {
        "klik": status,
        "zone": cfg["zone"],
        "webhook_path": "/api/klik/webhook/authorize",
        "demo_pin": "1234",
        "demo_accounts": [
            {"account": "11111111", "user_id": "102030-11111111", "phone_hint": "+447911111111"},
            {"account": "22222222", "user_id": "102030-22222222", "phone_hint": "+447922222222"},
        ],
        "agent_ui": cfg["agent_url"],
        "demo_agent_api_key": os.getenv(
            "KLIK_SEED_AGENT_API_KEY", "klik_dev_agent_uk_school_demo"
        ),
        "repo": cfg["repo"],
    }


@app.post("/api/klik/webhook/authorize")
async def klik_webhook_authorize(request: Request):
    """Webhook wywoływany przez KLIK po /payments/initiate (terminal agenta)."""
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    try:
        payload = await request.json()
        return klik_service.handle_authorize_webhook(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/klik/webhook/ping")
async def klik_webhook_ping(request: Request):
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    payload = await request.json()
    return klik_service.handle_ping_webhook(payload)


@app.get("/api/klik/accounts")
def api_klik_accounts():
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    return klik_service.list_accounts()


@app.post("/api/klik/codes/generate")
def api_klik_generate_code(req: KlikGenerateCodeRequest):
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    try:
        return klik_service.generate_code(req.sort_code, req.account_number)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/klik/pending")
def api_klik_pending():
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    return klik_service.list_pending()


@app.post("/api/klik/pending/{transaction_id}/accept")
def api_klik_accept(transaction_id: str, req: KlikPinRequest):
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    try:
        return klik_service.accept_payment(transaction_id, req.pin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/klik/pending/{transaction_id}/reject")
def api_klik_reject(transaction_id: str):
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    try:
        return klik_service.reject_payment(transaction_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/klik/alias/register")
def api_klik_alias_register(req: KlikAliasRequest):
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    try:
        return klik_service.register_alias(req.sort_code, req.account_number, req.phone.strip())
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/api/klik/alias")
def api_klik_alias_remove(req: KlikAliasRequest):
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    try:
        return klik_service.remove_alias(req.sort_code, req.account_number, req.phone.strip())
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/klik/alias/{sort_code}/{account_number}")
def api_klik_alias_get(sort_code: str, account_number: str):
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    alias = klik_service.get_alias(sort_code, account_number)
    return alias or {"phone": None}


@app.post("/api/klik/p2p/send")
def api_klik_p2p_send(req: KlikP2PRequest):
    if not klik_service:
        raise HTTPException(status_code=503, detail="KLIK service unavailable")
    try:
        return klik_service.send_p2p(req.from_sort_code, req.from_account, req.phone.strip(), req.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/klik", response_class=HTMLResponse, include_in_schema=False)
def klik_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    cfg = klik_config()
    return templates.TemplateResponse(request, "klik.html", {
        "request": request,
        "user": user,
        "agent_url": cfg["agent_url"],
        "zone": cfg["zone"],
    })


@app.get("/api/swift/status")
def api_swift_status():
    """Status integracji z siecią SWIFT (do GUI i monitoringu)."""
    health = swift_client.health_check() if swift_client else {"ok": False}
    public_url = (health.get("url") or "http://localhost:3000").replace(
        "swift-app", "localhost"
    ).replace("host.docker.internal", "localhost")
    token_ok = False
    banks = []
    if health.get("ok"):
        try:
            swift_client.get_token(force=True)
            token_ok = True
            banks = swift_client._token_banks
        except Exception:
            token_ok = False
    return {
        "bank": {"ok": True, "bic": swift_client.bank_bic if swift_client else "UKBKGB01XXX"},
        "swift_middleware": health,
        "dashboard_url": public_url,
        "auth_ok": token_ok,
        "allowed_banks": banks,
        "receive_endpoint": "POST /receive",
    }


def _school_ports() -> dict:
    return {
        "uk_bank_b": int(os.getenv("BANK_PUBLIC_PORT", os.getenv("BANK_PORT", "8010"))),
        "peer_bank_api": 8001,
        "peer_bank_frontend": 5173,
        "klik_standalone_api": 8000,
        "klik_standalone_agent": 5175,
        "klik_embedded_api": int(os.getenv("KLIK_WEB_PORT", "8102")),
        "klik_embedded_agent": int(os.getenv("KLIK_AGENT_PORT", "8175")),
        "cards_gateway": 8072,
        "cards_admin": 3072,
        "swift_middleware": 3000,
        "ukps_chaps": 8420,
        "ukps_fps": 8421,
        "ukps_bacs": 8422,
        "postgres_uk_bank_b": int(os.getenv("BANK_DB_PORT", "5438")),
    }


def _bank_public_url(path: str = "") -> str:
    port = os.getenv("BANK_PUBLIC_PORT", os.getenv("BANK_PORT", "8010"))
    return f"http://localhost:{port}{path}"


def _public_url(url: str) -> str:
    klik_web = os.getenv("KLIK_WEB_PORT", "8102")
    return (url or "").replace("payment-gateway:8000", "localhost:8072") \
        .replace("host.docker.internal", "localhost") \
        .replace("swift-app", "localhost") \
        .replace("klik-web:8000", f"localhost:{klik_web}")


@app.get("/api/integrations")
def api_integrations():
    """Zagregowany status wszystkich integracji (sprawdzane po stronie serwera).

    Sprawdzenia używają wewnętrznych adresów (host.docker.internal), więc realnie
    zwracają HTTP 200, a w GUI prezentujemy publiczne adresy (localhost).
    """
    import requests as http_requests

    checks: list[dict] = []

    def probe(name: str, group: str, url: str, method: str = "GET", ok_statuses: tuple[int, ...] | None = None):
        entry = {"name": name, "group": group, "url": _public_url(url), "method": method}
        allowed = ok_statuses or tuple(range(200, 400))
        try:
            if method == "GET":
                r = http_requests.get(url, timeout=4)
            else:
                r = http_requests.request(method, url, timeout=4)
            entry["status"] = r.status_code
            entry["ok"] = r.status_code in allowed
        except Exception as exc:
            entry["status"] = None
            entry["ok"] = False
            entry["error"] = str(exc)
        checks.append(entry)
        return entry

    # --- UK Bank B (samo siebie) ---
    checks.append({
        "name": "UK Bank B API", "group": "Bank", "url": _bank_public_url("/api/info"),
        "method": "GET", "status": 200, "ok": True,
    })

    # --- Moduł kart ---
    gw = card_gateway.health_check() if card_gateway else {"ok": False, "url": ""}
    gw_url = gw.get("url") or "http://host.docker.internal:8072"
    probe("Payment Gateway (Swagger)", "Karty płatnicze", f"{gw_url}/docs")
    probe("Terminal POS", "Karty płatnicze", f"{gw_url}/pos")
    admin_url = os.getenv("CARD_ADMIN_PANEL_URL", "http://host.docker.internal:3072")
    probe("Panel admina kart", "Karty płatnicze", admin_url)

    # --- Sieć SWIFT ---
    sw = swift_client.health_check() if swift_client else {"ok": False, "url": ""}
    sw_url = sw.get("url") or "http://host.docker.internal:3000"
    probe("Middleware SWIFT (API)", "Sieć SWIFT", f"{sw_url}/api/openapi.json")
    probe("Panel operatora SWIFT", "Sieć SWIFT", f"{sw_url}/")
    probe("Swagger SWIFT", "Sieć SWIFT", f"{sw_url}/docs")
    token_entry = {"name": "Autoryzacja OAuth2 (token)", "group": "Sieć SWIFT",
                   "url": _public_url(f"{sw_url}/auth/token"), "method": "POST"}
    try:
        if swift_client:
            swift_client.get_token(force=True)
            token_entry["status"] = 200
            token_entry["ok"] = True
    except Exception as exc:
        token_entry["status"] = None
        token_entry["ok"] = False
        token_entry["error"] = str(exc)
    checks.append(token_entry)

    # --- UKPS Services ---
    group_name = "UK Payment Schemes (UKPS)"
    chaps_url = os.getenv("UKPS_CHAPS_URL", "http://host.docker.internal:8420")
    probe("CHAPS Service", group_name, f"{chaps_url}/v1/healthz")
    fps_url = os.getenv("UKPS_FPS_URL", "http://host.docker.internal:8421")
    probe("FPS Service", group_name, f"{fps_url}/v1/healthz")
    bacs_url = os.getenv("UKPS_BACS_URL", "http://host.docker.internal:8422")
    probe("BACS Service", group_name, f"{bacs_url}/v1/healthz")

    # --- Bank partnerski (Alice Bank / uk-bank-system) ---
    peer_group = "Bank partnerski (UK Bank A)"
    peer_api = os.getenv("PEER_BANK_API_URL", "http://host.docker.internal:8001")
    peer_fe = os.getenv("PEER_BANK_FRONTEND_URL", "http://host.docker.internal:5173")
    probe("API banku partnerskiego (Swagger)", peer_group, f"{peer_api}/api/docs/")
    probe("Frontend banku partnerskiego", peer_group, f"{peer_fe}/login", ok_statuses=(200, 304))

    # --- KLIK-payments ---
    klik_group = "KLIK (płatności mobilne)"
    klik_health = os.getenv(
        "KLIK_HEALTH_URL",
        f"http://host.docker.internal:{os.getenv('KLIK_WEB_PORT', '8102')}/healthz/",
    )
    probe("KLIK API (healthz)", klik_group, klik_health)
    agent_url = os.getenv(
        "KLIK_AGENT_URL",
        f"http://host.docker.internal:{os.getenv('KLIK_AGENT_PORT', '8175')}",
    )
    probe("Terminal agenta KLIK", klik_group, agent_url, ok_statuses=(200, 304))

    total = len(checks)
    ok_count = sum(1 for c in checks if c.get("ok"))
    return {
        "summary": {"total": total, "ok": ok_count, "all_ok": ok_count == total},
        "checks": checks,
    }


@app.get("/integracje", response_class=HTMLResponse, include_in_schema=False)
def integrations_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request, "integrations.html", {
        "request": request,
        "user": user,
        "swift_dashboard": _public_url(os.getenv("SWIFT_MIDDLEWARE_URL", "http://localhost:3000")),
        "pos_url": _public_url(os.getenv("CARD_GATEWAY_URL", "http://localhost:8072")) + "/pos",
    })


class SwiftReceiveAck(BaseModel):
    pass


@app.post("/receive")
@app.post("/swift/receive")
async def swift_receive(request: Request):
    """Odbiór przychodzącego przelewu SWIFT (rola banku odbiorcy w sieci).

    Middleware forwarduje tu pacs.008 z nagłówkami X-SWIFT-*. Uznajemy konto
    i (jeśli podano callback) odsyłamy potwierdzenie ACK.
    """
    xml_body = (await request.body()).decode("utf-8", errors="ignore")
    h = request.headers
    result, status = swift_network_service.receive_incoming(
        xml_body=xml_body,
        currency=h.get("X-SWIFT-Currency", ""),
        uetr=h.get("X-SWIFT-UETR", ""),
        message_id=h.get("X-SWIFT-Message-Id", ""),
        receiver_account=h.get("X-SWIFT-Receiver-Account", ""),
        sender_account=h.get("X-SWIFT-Sender-Account", ""),
        settlement_date=h.get("X-SWIFT-Settlement-Date", ""),
    )

    callback_url = h.get("X-SWIFT-Callback-Url", "")
    if callback_url and status == 202:
        try:
            import requests as _rq
            _rq.post(callback_url, json={
                "status": "accepted",
                "bank": "UK Bank B",
                "received_at": result.get("received_at"),
                "message_id": result.get("message_id"),
                "uetr": result.get("uetr"),
                "receiver_account": h.get("X-SWIFT-Receiver-Account", ""),
            }, timeout=3.0)
        except Exception:
            pass

    from fastapi.responses import JSONResponse
    return JSONResponse(content=result, status_code=status)

# ========================
#   API JUNIOR TRANSFER
# ========================

@app.post("/accounts/create")
def create_account(account_number: str, account_type: str = "standard", parent_account_number: str = None, initial_balance: float = 100.0):
    existing = repo.get_by_id(AccountNumber("102030", account_number))
    if existing: raise HTTPException(status_code=400, detail="Konto już istnieje.")
    new_account = Account(
        id=AccountNumber("102030", account_number),
        balance=Money(Decimal(str(initial_balance)), Currency.GBP),
        debt_limit=Money(Decimal("0.00"), Currency.GBP),
        is_active=True, account_type=account_type, parent_account_number=parent_account_number
    )
    repo.save(new_account)
    return {"status": "SUCCESS", "message": f"Utworzono konto o numerze {account_number}."}

@app.post("/transfer/junior/request")
def junior_request(from_acc: str, to_acc: str, amount: float):
    use_case = JuniorTransferUseCase(repo, tx_repo)
    try:
        return use_case.request_transfer(AccountNumber("102030", from_acc), to_acc, Money(Decimal(str(amount)), Currency.GBP))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transfer/junior/approve")
def junior_approve(parent_acc: str, transaction_id: str, approve: bool):
    use_case = ApproveJuniorTransferUseCase(repo, tx_repo)
    try:
        return use_case.execute(parent_acc, transaction_id, approve)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ========================
#   API REST (kompatybilność)
# ========================

@app.get("/api/info")
def api_info():
    return {
        "name": "UK Bank B System API",
        "status": "running",
        "gui": "/dashboard",
        "docs": "/docs",
        "card_gateway": os.getenv("CARD_GATEWAY_URL", "http://localhost:8072"),
        "card_integration": "UK_BANK_B (BIN 460001, bank-key-uk-b)",
        "pos_terminal": f"{os.getenv('CARD_GATEWAY_URL', 'http://localhost:8072')}/pos",
        "swift_middleware": os.getenv("SWIFT_MIDDLEWARE_URL", "http://localhost:3000"),
        "swift_bic": os.getenv("SWIFT_BANK_BIC", "UKBKGB01XXX"),
    }


@app.post("/transfer/internal")
def internal_transfer(req: TransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        receiver = AccountNumber(req.to_sort_code, req.to_account)
        money = Money(req.amount, Currency.GBP)
        transfer_service.execute(sender, receiver, money)
        return {"message": "Przelew wykonany pomyślnie"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/accounts/{sort_code}/{account_number}", summary="Sprawdź stan konta")
def get_account_balance(sort_code: str, account_number: str):
    acc_id = AccountNumber(sort_code, account_number)
    account = repo.get_by_id(acc_id)
    if not account:
        raise HTTPException(status_code=404, detail="Nie znaleziono takiego konta")
    return {
        "account_number": account.id.account_number,
        "balance": account.balance.amount,
        "currency": account.balance.currency.value,
        "is_active": account.is_active
    }


@app.post("/transfer/bacs", summary="Standardowy przelew międzybankowy (BACS)")
def make_bacs_transfer(req: TransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        money = Money(req.amount, Currency.GBP)
        result_message = bacs_service.execute(
            from_account_id=sender,
            to_sort_code=req.to_sort_code,
            to_account_number=req.to_account,
            amount=money
        )
        return {"status": "PENDING (Oczekujący)", "message": result_message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/transfer/fps", summary="Natychmiastowy przelew (Faster Payments)")
def make_fps_transfer(req: TransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        money = Money(req.amount, Currency.GBP)
        result = fps_service.execute(
            from_account_id=sender,
            to_sort_code=req.to_sort_code,
            to_account_number=req.to_account,
            amount=money
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/transfer/chaps", summary="RTGS - Real Time Gross Settlement (CHAPS)")
def make_chaps_transfer(req: TransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        money = Money(req.amount, Currency.GBP)
        result = chaps_service.execute(
            from_account_id=sender,
            to_sort_code=req.to_sort_code,
            to_account_number=req.to_account,
            amount=money
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/transfer/swift", summary="Międzynarodowy transfer (SWIFT)")
def make_swift_transfer(req: SWIFTTransferRequest):
    try:
        sender = AccountNumber(req.from_sort_code, req.from_account)
        money = Money(req.amount, Currency.GBP)
        result = swift_service.execute(
            from_account_id=sender,
            to_sort_code=req.to_sort_code,
            to_account_number=req.to_account,
            amount=money,
            to_currency=req.to_currency
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
