import uuid
from decimal import Decimal
from domain.value_objects import AccountNumber, Money, Currency
from domain.exceptions import InsufficientFundsError

class JuniorTransferUseCase:
    def __init__(self, account_repo, transaction_repo):
        self.account_repo = account_repo
        self.transaction_repo = transaction_repo

    def request_transfer(self, from_account_id: AccountNumber, to_account_number: str, amount: Money):
        # 1. Pobierz konto nadawcy z bazy
        source_account = self.account_repo.get_by_id(from_account_id)
        if not source_account:
            raise ValueError("Konto nadawcy nie istnieje.")

        if not source_account.is_active:
            raise ValueError("Błąd: Konto nadawcy jest zamrożone (zablokowane). Zgłoszenie odrzucone.")

        # 2. Walidacja typu konta
        if source_account.account_type != "junior":
            raise ValueError("Błąd: Używasz endpointu dla kont junior na koncie standardowym.")

        # 3. Weryfikacja, czy junior ma w ogóle środki (bez ich zabierania)
        if source_account.balance.amount < amount.amount:
            raise InsufficientFundsError("Brak wystarczających środków na koncie, aby zgłosić ten przelew.")

        # 4. Wygeneruj ID transakcji i zapisz w bazie jako oczekującą
        tx_id = str(uuid.uuid4())
        self.transaction_repo.save(
            tx_id=tx_id,
            sender=source_account.id.account_number,
            receiver=to_account_number,
            amount=float(amount.amount),
            currency=amount.currency.value,
            tx_type="JUNIOR",
            status="PENDING_APPROVAL"
        )

        return {
            "status": "PENDING",
            "transaction_id": tx_id,
            "message": f"Przelew zgłoszony. Czeka na zatwierdzenie przez rodzica (Konto: {source_account.parent_account_number})."
        }

class ApproveJuniorTransferUseCase:
    def __init__(self, account_repo, transaction_repo):
        self.account_repo = account_repo
        self.transaction_repo = transaction_repo

    def execute(self, parent_account_number: str, transaction_id: str, approve: bool):
        # 1. Pobierz transakcję z bazy
        tx = self.transaction_repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError("Transakcja nie istnieje.")

        if tx["status"] != "PENDING_APPROVAL":
            raise ValueError(f"Transakcja nie oczekuje na akceptację (Obecny status: {tx['status']}).")

        # 2. Pobierz konto juniora i zweryfikuj czy to ten rodzic
        junior_account = self.account_repo.get_by_id(AccountNumber("102030", tx["sender_account"]))
        if not junior_account or junior_account.parent_account_number != parent_account_number:
            raise ValueError("Brak uprawnień. Twoje konto nie jest podpięte jako rodzic tego konta juniora.")

        # 3. Odrzucenie przelewu
        if not approve:
            self.transaction_repo.save(
                tx_id=tx["id"], sender=tx["sender_account"], receiver=tx["receiver_account"],
                amount=tx["amount"], currency=tx["currency"], tx_type=tx["transfer_type"],
                status="REJECTED_BY_PARENT"
            )
            return {"status": "REJECTED", "message": "Przelew został odrzucony przez rodzica."}

        # 4. Akceptacja przelewu - pobranie środków z konta juniora i wysłanie do odbiorcy
        amount = Money(Decimal(str(tx["amount"])), Currency(tx["currency"]))
        junior_account.debit(amount)
        self.account_repo.save(junior_account)

        # Uznanie konta odbiorcy (jeśli konto istnieje w naszym banku)
        receiver_account = self.account_repo.get_by_id(AccountNumber("102030", tx["receiver_account"]))
        if receiver_account:
            receiver_account.credit(amount)
            self.account_repo.save(receiver_account)

        self.transaction_repo.save(
            tx_id=tx["id"], sender=tx["sender_account"], receiver=tx["receiver_account"],
            amount=tx["amount"], currency=tx["currency"], tx_type=tx["transfer_type"],
            status="COMPLETED"
        )

        return {"status": "APPROVED", "message": "Przelew zatwierdzony i zrealizowany pomyślnie."}