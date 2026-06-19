from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class Currency(Enum):
    GBP = "GBP"
    EUR = "EUR"
    USD = "USD"

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Nie można dodawać różnych walut")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Nie można odejmować różnych walut")
        return Money(self.amount - other.amount, self.currency)

@dataclass(frozen=True)
class AccountNumber:
    sort_code: str      # 6 cyfr, np. '123456' (akceptuje też XX-XX-XX)
    account_number: str # 8 cyfr, np. '12345678'

    def __post_init__(self):
        sc = self.sort_code.replace("-", "").replace(" ", "").strip()
        acc = self.account_number.replace("-", "").replace(" ", "").strip()
        object.__setattr__(self, "sort_code", sc)
        object.__setattr__(self, "account_number", acc)