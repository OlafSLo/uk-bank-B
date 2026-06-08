from dataclasses import dataclass
from enum import Enum
from domain.value_objects import Money, AccountNumber
from domain.exceptions import InsufficientFundsError, InactiveAccountError

class UserRole(Enum):
    CUSTOMER = "customer"
    BANK_EMPLOYEE = "employee"
    SYSTEM_OPERATOR = "operator"

@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: UserRole
    is_active: bool = True

@dataclass
class Account:
    id: AccountNumber
    balance: Money
    debt_limit: Money  # Limit zadłużenia banku/klienta
    is_active: bool = True
    account_type: str = "standard" # "standard" lub "junior"
    parent_account_number: str | None = None # Numer konta rodzica dla kont junior

    def credit(self, amount: Money):
        if not self.is_active:
            raise InactiveAccountError("Konto nieaktywne.")
        self.balance += amount

    def debit(self, amount: Money):
        if not self.is_active:
            raise InactiveAccountError("Konto zablokowane (brak płynności lub nieaktywne).")
        
        # Sprawdzamy limit płynności (na potrzeby 3.0)
        if self.balance.amount - amount.amount < -self.debt_limit.amount:
            raise InsufficientFundsError("Przekroczono limit zadłużenia (Liquidity Alert).")
        
        self.balance -= amount

@dataclass
class Card:
    card_number: str
    account_number: str
    expiry_date: str
    cvv: str
    pin_hash: str
    is_active: bool = True
    card_type: str = "debit"
    daily_limit: Money | None = None
    card_token: str = ""
    gateway_status: str = "REQUESTED"
    masked_pan: str = ""
    expiry_month: int = 0
    expiry_year: int = 0