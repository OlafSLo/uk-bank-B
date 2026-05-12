from dataclasses import dataclass
from domain.value_objects import Money, AccountNumber
from domain.exceptions import InsufficientFundsError, InactiveAccountError

@dataclass
class Account:
    id: AccountNumber
    balance: Money
    is_active: bool = True

    def credit(self, amount: Money):
        """Uznanie rachunku (wpływ)"""
        if not self.is_active:
            raise InactiveAccountError("Konto jest nieaktywne. Nie można wpłacić środków.")
        self.balance += amount

    def debit(self, amount: Money):
        """Obciążenie rachunku (wypływ)"""
        if not self.is_active:
            raise InactiveAccountError("Konto jest nieaktywne. Nie można wypłacić środków.")
        if self.balance.amount < amount.amount:
            raise InsufficientFundsError("Brak wystarczających środków na koncie.")
        self.balance -= amount