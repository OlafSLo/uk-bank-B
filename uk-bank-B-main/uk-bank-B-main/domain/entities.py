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