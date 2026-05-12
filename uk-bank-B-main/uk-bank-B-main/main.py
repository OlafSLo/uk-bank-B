from decimal import Decimal

from domain.value_objects import AccountNumber, Money, Currency
from domain.entities import Account
from application.internal_transfer import InternalTransferUseCase
from infrastructure.sqlite_repository import SQLiteAccountRepository


def setup_mock_data(repo: SQLiteAccountRepository):
    """Pomocnicza funkcja do stworzenia dwóch kont początkowych w bazie."""
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
    print("Dodano konta początkowe do bazy danych.")


if __name__ == "__main__":
    # 1. Inicjalizacja bazy danych
    repository = SQLiteAccountRepository()

    # Tworzymy konta do testów
    setup_mock_data(repository)

    # 2. Inicjalizacja Przypadku Użycia (wstrzykujemy naszą bazę)
    transfer_use_case = InternalTransferUseCase(account_repository=repository)

    # 3. Definiujemy nadawcę, odbiorcę i kwotę przelewu
    sender_id = AccountNumber(sort_code="102030", account_number="11111111")
    receiver_id = AccountNumber(sort_code="102030", account_number="22222222")
    transfer_amount = Money(Decimal("100.00"), Currency.GBP)

    print(f"\nRozpoczynam przelew {transfer_amount.amount} {transfer_amount.currency.value}...")

    # 4. Wykonujemy przelew biznesowy!
    try:
        transfer_use_case.execute(
            from_account_id=sender_id,
            to_account_id=receiver_id,
            amount=transfer_amount
        )
        print("Przelew zakończony sukcesem!")
    except Exception as e:
        print(f"Błąd przelewu: {e}")

    # 5. Sprawdzamy nowy stan konta w bazie
    acc_1_after = repository.get_by_id(sender_id)
    acc_2_after = repository.get_by_id(receiver_id)

    print("\nStan kont po przelewie:")
    print(f"Konto Nadawcy ({acc_1_after.id.account_number}): {acc_1_after.balance.amount} GBP")
    print(f"Konto Odbiorcy ({acc_2_after.id.account_number}): {acc_2_after.balance.amount} GBP")