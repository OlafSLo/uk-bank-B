from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from decimal import Decimal

from domain.value_objects import AccountNumber, Money, Currency
from application.internal_transfer import InternalTransferUseCase
from infrastructure.sqlite_repository import SQLiteAccountRepository
from application.bacs_transfer import BACSTransferUseCase

app = FastAPI(title="UK Bank System API")
@app.get("/")
def home():
    return {
        "nazwa": "UK Bank System API",
        "status": "Działa",
        "interfejs_graficzny": "Przejdź pod adres /docs aby przetestować przelewy"
    }
# Podpinamy bazę i logikę
repo = SQLiteAccountRepository("bank.db")
transfer_service = InternalTransferUseCase(repo)
bacs_service = BACSTransferUseCase(repo)

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