from abc import ABC, abstractmethod
from typing import Optional
from domain.entities import Account
from domain.value_objects import AccountNumber


class AccountRepository(ABC):
    """Interfejs repozytorium - kontrakt, który każda baza danych musi spełnić."""

    @abstractmethod
    def get_by_id(self, account_id: AccountNumber) -> Optional[Account]:
        """Pobiera konto po jego numerze. Zwraca Account lub None."""
        pass

    @abstractmethod
    def save(self, account: Account) -> None:
        """Zapisuje (lub aktualizuje) stan konta w bazie."""
        pass