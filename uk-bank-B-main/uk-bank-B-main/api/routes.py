from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from contextlib import asynccontextmanager

from domain.value_objects import AccountNumber, Money, Currency
from domain.entities import Account
from application.internal_transfer import InternalTransferUseCase
from infrastructure.postgresql_repository import PostgreSQLAccountRepository
from application.bacs_transfer import BACSTransferUseCase
from application.fps_transfer import FPSTransferUseCase
from application.chaps_transfer import CHAPSTransferUseCase
from application.swift_transfer import SWIFTTransferUseCase


def setup_mock_data(repo: PostgreSQLAccountRepository):
    """Inicjalizuje dane testowe w bazie, jeśli baza jest pusta."""
    try:
        # Sprawdzamy, czy tabela jest pusta (czy mamy mniej niż 2 konta)
        conn = repo.db_url  # Użyjemy bezpośredniego połączenia do sprawdzenia
        import psycopg2
        conn = psycopg2.connect(repo.db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM accounts")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        if count >= 2:
            return  # Dane już istnieją
    except:
        pass  # Jeśli tabela nie istnieje lub błąd, dodajemy dane
    
    # Tworzymy konta testowe
    account_1 = Account(
        id=AccountNumber(sort_code="102030", account_number="11111111"),
        balance=Money(Decimal("500.00"), Currency.GBP)
    )
    account_2 = Account(
        id=AccountNumber(sort_code="102030", account_number="22222222"),
        balance=Money(Decimal("50.00"), Currency.GBP)
    )
    repo.save(account_1)
    repo.save(account_2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: inicjalizujemy repo po tym, jak środowisko jest gotowe
    global repo, transfer_service, bacs_service, fps_service, chaps_service, swift_service
    repo = PostgreSQLAccountRepository()
    transfer_service = InternalTransferUseCase(repo)
    bacs_service = BACSTransferUseCase(repo)
    fps_service = FPSTransferUseCase(repo)
    chaps_service = CHAPSTransferUseCase(repo)
    swift_service = SWIFTTransferUseCase(repo)
    
    # Inicjalizujemy dane testowe
    setup_mock_data(repo)
    
    yield
    # Shutdown: możemy tu zamknąć połączenia, jeśli trzeba

app = FastAPI(title="UK Bank System API", lifespan=lifespan)

# Globalne zmienne, które będą ustawione w lifespan
repo = None
transfer_service = None
bacs_service = None
fps_service = None
chaps_service = None
swift_service = None
@app.get("/")
def home():
    return {
        "nazwa": "UK Bank System API",
        "status": "Działa",
        "interfejs_graficzny": "Przejdź pod adres /docs aby przetestować przelewy"
    }

# Definiujemy, co użytkownik musi wpisać w "okienku"
class TransferRequest(BaseModel):
    from_sort_code: str
    from_account: str
    to_sort_code: str
    to_account: str
    amount: Decimal


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

        return {
            "status": "PENDING (Oczekujący)",
            "message": result_message
        }
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


class SWIFTTransferRequest(BaseModel):
    from_sort_code: str
    from_account: str
    to_sort_code: str
    to_account: str
    amount: Decimal
    to_currency: str = "GBP"  # Waluta docelowa


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