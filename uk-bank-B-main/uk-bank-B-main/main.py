import os
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from decimal import Decimal
from domain.value_objects import AccountNumber, Money, Currency
from domain.entities import Account
from application.auth_service import AuthUseCase, AuthService
from infrastructure.postgresql_repository import PostgreSQLAccountRepository, PostgreSQLUserRepository, PostgreSQLTransactionRepository
from application.fps_transfer import FPSTransferUseCase
from application.chaps_transfer import CHAPSTransferUseCase
from application.swift_transfer import SWIFTTransferUseCase
from application.junior_transfer import JuniorTransferUseCase, ApproveJuniorTransferUseCase

app = FastAPI(title="UK Bank B - Enterprise System")

# Konfiguracja szablonów HTML dla nowego frontendu
templates = Jinja2Templates(directory="api/templates") if os.path.exists("api/templates") else Jinja2Templates(directory=".")

# Inicjalizacja komponentów
repo = PostgreSQLAccountRepository()
user_repo = PostgreSQLUserRepository()
tx_repo = PostgreSQLTransactionRepository()
auth_service = AuthService()
auth_use_case = AuthUseCase(user_repo, auth_service)

# --- AUTH ---
@app.post("/auth/register")
def register(username: str, password: str, role: str = "customer"):
    return auth_use_case.register(username, password, role)

@app.post("/auth/login")
def login(username: str, password: str):
    return auth_use_case.login(username, password)

# --- TWORZENIE KONT (w tym Junior) ---

@app.post("/accounts/create")
def create_account(account_number: str, account_type: str = "standard", parent_account_number: str = None, initial_balance: float = 100.0):
    """Pomocniczy endpoint do ręcznego tworzenia kont testowych (np. konto junior)."""
    existing = repo.get_by_id(AccountNumber("102030", account_number))
    if existing:
        raise HTTPException(status_code=400, detail="Konto o tym numerze już istnieje.")
        
    new_account = Account(
        id=AccountNumber("102030", account_number),
        balance=Money(Decimal(str(initial_balance)), Currency.GBP),
        debt_limit=Money(Decimal("0.00"), Currency.GBP),
        is_active=True,
        account_type=account_type,
        parent_account_number=parent_account_number
    )
    repo.save(new_account)
    return {"status": "SUCCESS", "message": f"Utworzono konto {account_type} o numerze {account_number}."}

# --- PRZELEWY ---

@app.post("/transfer/fps")
def transfer_fps(from_acc: str, to_acc: str, to_sort: str, amount: float):
    """FPS - Natychmiastowy do 250k GBP"""
    use_case = FPSTransferUseCase(repo)
    return use_case.execute(
        AccountNumber("102030", from_acc), 
        to_sort, to_acc, 
        Money(Decimal(str(amount)), Currency.GBP)
    )

@app.post("/transfer/chaps")
def transfer_chaps(from_acc: str, to_bank_id: str, to_acc: str, amount: float):
    """CHAPS - RTGS przez Bank Centralny"""
    use_case = CHAPSTransferUseCase(repo)
    return use_case.execute(
        AccountNumber("102030", from_acc),
        to_bank_id, to_acc,
        Money(Decimal(str(amount)), Currency.GBP)
    )

@app.post("/transfer/swift")
def transfer_swift(from_acc: str, to_bic: str, to_acc: str, amount: float, curr: str = "USD"):
    """SWIFT - Międzynarodowy z przewalutowaniem (wymóg 4.0/5.0)"""
    # Tu wstawiamy aml_service z poprzedniego kroku jako mock
    use_case = SWIFTTransferUseCase(repo, None) 
    return use_case.execute(
        AccountNumber("102030", from_acc),
        to_bic, to_acc,
        Money(Decimal(str(amount)), Currency(curr)),
        Currency(curr)
    )

# --- JUNIOR (Wymóg 4.0) ---
@app.post("/transfer/junior/request")
def junior_request(from_acc: str, to_acc: str, amount: float):
    """Zgłoszenie przelewu z konta Junior - trafia do weryfikacji rodzica."""
    use_case = JuniorTransferUseCase(repo, tx_repo)
    try:
        return use_case.request_transfer(
            from_account_id=AccountNumber("102030", from_acc),
            to_account_number=to_acc,
            amount=Money(Decimal(str(amount)), Currency.GBP)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- FRONTEND KONT JUNIOR ---

@app.get("/portal-junior", response_class=HTMLResponse)
def junior_portal(request: Request):
    """Wyświetla graficzny interfejs Portalu Junior."""
    return templates.TemplateResponse("junior_portal.html", {"request": request})

@app.post("/transfer/junior/approve")
def junior_approve(parent_acc: str, transaction_id: str, approve: bool):
    """Akceptacja (lub odrzucenie) przelewu juniora przez rodzica."""
    use_case = ApproveJuniorTransferUseCase(repo, tx_repo)
    try:
        return use_case.execute(parent_acc, transaction_id, approve)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))