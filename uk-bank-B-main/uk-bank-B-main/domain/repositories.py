from abc import ABC, abstractmethod
from typing import Optional
from domain.entities import Account, User, Card
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
        
    @abstractmethod
    def get_all(self) -> list[Account]:
        """Pobiera listę wszystkich kont w systemie."""
        pass


class UserRepository(ABC):
    """Interfejs repozytorium użytkowników."""

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Pobiera użytkownika po ID."""
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """Pobiera użytkownika po nazwie."""
        pass

    @abstractmethod
    def save(self, user: User) -> None:
        """Zapisuje (lub aktualizuje) użytkownika."""
        pass

class CardRepository(ABC):
    """Interfejs repozytorium kart płatniczych."""

    @abstractmethod
    def get_by_account(self, account_number: str) -> list[Card]:
        pass

    @abstractmethod
    def get_by_number(self, card_number: str) -> Optional[Card]:
        pass

    @abstractmethod
    def get_by_token(self, card_token: str) -> Optional[Card]:
        pass

    @abstractmethod
    def get_by_authorization_code(self, authorization_code: str) -> Optional[Card]:
        pass

    @abstractmethod
    def save(self, card: Card) -> None:
        pass

    @abstractmethod
    def save_capture(
        self,
        authorization_code: str,
        transaction_id: str,
        card_number: str,
        amount: float,
        currency: str,
        status: str,
    ) -> None:
        pass

    @abstractmethod
    def save_authorization_hold(
        self,
        authorization_code: str,
        account_number: str,
        amount: float,
        currency: str,
        transaction_id: str,
        merchant_name: str,
    ) -> None:
        pass

    @abstractmethod
    def save_refund(self, original_transaction_id: str, amount: float, currency: str) -> None:
        pass