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
from domain.entities import Account, User
from application.internal_transfer import InternalTransferUseCase
from application.auth_service import AuthUseCase, AuthService
from infrastructure.postgresql_repository import PostgreSQLAccountRepository, PostgreSQLUserRepository, PostgreSQLTransactionRepository, PostgreSQLCardRepository
from application.bacs_transfer import BACSTransferUseCase
from application.fps_transfer import FPSTransferUseCase
from application.chaps_transfer import CHAPSTransferUseCase
from application.swift_transfer import SWIFTTransferUseCase
from application.junior_transfer import JuniorTransferUseCase, ApproveJuniorTransferUseCase
from application.employee_service import EmployeeUseCase
from application.card_service import CardService


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
    global tx_repo, employee_service, card_repo, card_service

    repo = PostgreSQLAccountRepository()
    user_repo = PostgreSQLUserRepository()
    tx_repo = PostgreSQLTransactionRepository()
    card_repo = PostgreSQLCardRepository()
    auth_service = AuthService()
    auth_use_case = AuthUseCase(user_repo, auth_service)
    transfer_service = InternalTransferUseCase(repo)
    bacs_service = BACSTransferUseCase(repo)
    fps_service = FPSTransferUseCase(repo)
    chaps_service = CHAPSTransferUseCase(repo)
    swift_service = SWIFTTransferUseCase(repo)
    employee_service = EmployeeUseCase(repo)
    card_service = CardService(repo, card_repo)

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


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if user.role.value == "employee":
        return RedirectResponse(url="/back-office", status_code=302)

    # Pobierz wszystkie konta dla zalogowanego użytkownika (demo: pokazujemy konta testowe)
    acc1 = repo.get_by_id(AccountNumber("102030", "11111111"))
    acc2 = repo.get_by_id(AccountNumber("102030", "22222222"))
    accounts = [a for a in [acc1, acc2] if a]

    # Pobranie kont junior podpiętych pod główne konto 11111111 (Konto Rodzica)
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(repo.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT sort_code, account_number FROM accounts WHERE parent_account_number = '11111111'")
        junior_rows = cursor.fetchall()
        cursor.close()
        conn.close()
        for row in junior_rows:
            ja = repo.get_by_id(AccountNumber(row['sort_code'], row['account_number']))
            if ja: accounts.append(ja)
    except Exception as e:
        print("Błąd pobierania kont junior:", e)

    cards_by_account = {}
    for acc in accounts:
        cards_by_account[acc.id.account_number] = card_service.get_cards_for_account(acc.id.account_number)

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "user": user,
        "accounts": accounts,
        "cards_by_account": cards_by_account
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
        "transfer_type": transfer_type
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
        return {"status": "PENDING", "message": result}
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

# ========================
#   KARTY PŁATNICZE (API)
# ========================

@app.post("/api/cards/issue")
def issue_new_card(sort_code: str = Form(...), account_number: str = Form(...), pin: str = Form(...)):
    try:
        card = card_service.issue_card(sort_code, account_number, pin)
        return {"status": "SUCCESS", "message": f"Karta została wydana pomyślnie.", "card_number": card.card_number}
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
            "expiry_date": c.expiry_date,
            "is_active": c.is_active,
            "card_type": c.card_type,
            "daily_limit": float(c.daily_limit.amount) if c.daily_limit else None
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
        "name": "UK Bank System API",
        "status": "running",
        "gui": "/dashboard",
        "docs": "/docs"
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
