from dataclasses import dataclass
from domain.value_objects import AccountNumber, Money
from domain.repositories import AccountRepository
from domain.exceptions import DomainException


@dataclass
class InternalTransferUseCase:
    """Przypadek użycia: Przelew wewnętrzny (On-us Transfer)"""

    account_repository: AccountRepository

    def execute(self, from_account_id: AccountNumber, to_account_id: AccountNumber, amount: Money):
        # 1. Pobierz konta
        source_account = self.account_repository.get_by_id(from_account_id)
        target_account = self.account_repository.get_by_id(to_account_id)

        if not source_account:
            raise ValueError(f"Konto nadawcy {from_account_id} nie istnieje.")
        if not target_account:
            raise ValueError(f"Konto odbiorcy {to_account_id} nie istnieje.")

        # 2. Wykonaj logikę biznesową (obciążenie nadawcy, uznanie odbiorcy)
        source_account.debit(amount)
        target_account.credit(amount)

        # 3. Zapisz zaktualizowane konta w repozytorium
        self.account_repository.save(source_account)
        self.account_repository.save(target_account)