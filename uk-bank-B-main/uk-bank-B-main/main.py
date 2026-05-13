from fastapi import FastAPI, HTTPException, Depends
from decimal import Decimal
from domain.value_objects import AccountNumber, Money, Currency
from application.auth_service import AuthUseCase, AuthService
from infrastructure.postgresql_repository import PostgreSQLAccountRepository, PostgreSQLUserRepository
from application.fps_transfer import FPSTransferUseCase
from application.chaps_transfer import CHAPSTransferUseCase
from application.swift_transfer import SWIFTTransferUseCase

app = FastAPI(title="UK Bank B - Enterprise System")

# Inicjalizacja komponentów
repo = PostgreSQLAccountRepository()
user_repo = PostgreSQLUserRepository()
auth_service = AuthService()
auth_use_case = AuthUseCase(user_repo, auth_service)

# --- AUTH ---
@app.post("/auth/register")
def register(username: str, password: str, role: str = "customer"):
    return auth_use_case.register(username, password, role)

@app.post("/auth/login")
def login(username: str, password: str):
    return auth_use_case.login(username, password)

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
    """Przelew z konta Junior - wymaga zatwierdzenia przez parent_id"""
    acc = repo.get_by_id(AccountNumber("102030", from_acc))
    if acc.account_type != "junior":
        raise HTTPException(status_code=400, detail="To nie jest konto Junior")
    
    # Logika: Zamiast wykonać przelew, zapisujemy go ze statusem 'AWAITING_PARENT_APPROVAL'
    return {"status": "PENDING", "message": "Czekam na zatwierdzenie rodzica (Konto: " + acc.parent_account_number + ")"}