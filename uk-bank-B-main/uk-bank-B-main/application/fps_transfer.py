from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta
from domain.exceptions import InsufficientFundsError
from domain.value_objects import AccountNumber, Money
from domain.repositories import AccountRepository

class GridlockService:
    """Mechanizm rozwiązywania zatorów płatniczych (3.0)"""
    def __init__(self, repository):
        self.repo = repository
        self.queue = [] # Prosta kolejka w pamięci (na potrzeby projektu)

    def process_with_gridlock(self, from_acc, to_acc, amount):
        try:
            # Próba standardowa
            from_acc.debit(amount)
            self.repo.save(from_acc)
            return "SUCCESS"
        except InsufficientFundsError:
            # GRIDLOCK RESOLUTION:
            # Zamiast błędu, dodajemy do kolejki oczekujących
            self.queue.append({
                "from": from_acc.id.account_number,
                "to": to_acc,
                "amount": amount,
                "time": datetime.now()
            })
            return "QUEUED_IN_GRIDLOCK"

    def resolve_queue(self):
        """Próbuje przepchnąć zablokowane płatności po doładowaniu konta"""
        for tx in self.queue[:]:
            # Tutaj logika sprawdzająca czy teraz się uda...
            pass


@dataclass
class FPSTransferUseCase:
    account_repository: AccountRepository
    
    def execute(self, from_account_id: AccountNumber, to_sort_code: str, 
                to_account_number: str, amount: Money) -> dict:
        
        source_account = self.account_repository.get_by_id(from_account_id)
        if not source_account:
            raise ValueError("Konto nadawcy nie istnieje.")

        if not source_account.is_active:
            raise ValueError("Błąd: Konto nadawcy jest zamrożone (zablokowane). Przelew odrzucony.")

        # 1. Walidacja techniczna (Limit kwotowy FPS)
        if amount.amount > Decimal("250000"):
            raise ValueError("FPS: Limit transakcji to 250,000 GBP.")

        try:
            # 2. Próba obciążenia (Tu zadziała check limitu zadłużenia z encji)
            source_account.debit(amount)
            self.account_repository.save(source_account)
            
            return self._success_response(from_account_id, to_sort_code, to_account_number, amount)

        except InsufficientFundsError:
         
            return {
                "status": "GRIDLOCK",
                "message": "Alert: Przekroczono limit zadłużenia! Bank ma 2h na uzupełnienie środków.",
                "action_required": "Zwiększ kapitał lub wykonaj przelew z banku centralnego.",
                "deadline": (datetime.now() + timedelta(hours=2)).isoformat()
            }

    def _success_response(self, from_id, sort_code, to_acc, amount):
        return {
            "status": "SUCCESS",
            "transfer_type": "FPS",
            "amount": float(amount.amount),
            "timestamp": datetime.now().isoformat()
        }