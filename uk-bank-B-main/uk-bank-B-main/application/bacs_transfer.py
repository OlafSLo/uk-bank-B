from dataclasses import dataclass
from domain.value_objects import AccountNumber, Money
from domain.repositories import AccountRepository


@dataclass
class BACSTransferUseCase:
    """Przypadek użycia: Standardowy przelew międzybankowy (BACS)"""

    account_repository: AccountRepository

    def execute(self, from_account_id: AccountNumber, to_sort_code: str, to_account_number: str, amount: Money) -> str:
        # 1. Pobieramy TYLKO konto nadawcy
        source_account = self.account_repository.get_by_id(from_account_id)

        if not source_account:
            raise ValueError(f"Konto nadawcy {from_account_id.account_number} nie istnieje w naszym banku.")

        # 2. Obciążamy konto naszego klienta
        source_account.debit(amount)

        # 3. Zapisujemy nowy stan konta w naszej bazie
        self.account_repository.save(source_account)


        # zwracamy po prostu komunikat o statusie
        return f"Zlecenie przyjęte. Kwota {amount.amount} GBP została wysłana do banku {to_sort_code} i będzie rozliczona w ciągu 3 dni."