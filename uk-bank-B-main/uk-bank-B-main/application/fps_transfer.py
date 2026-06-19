from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta
from domain.exceptions import InsufficientFundsError
from domain.value_objects import AccountNumber, Money
from domain.repositories import AccountRepository
from typing import Any

@dataclass
class FPSTransferUseCase:
    account_repository: AccountRepository
    fps_client: Any = None
    
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
            
            if self.fps_client:
                try:
                    res = self.fps_client.send_payment(from_account_id.sort_code, from_account_id.account_number, to_sort_code, to_account_number, amount.amount)
                except Exception as e:
                    source_account.credit(amount)
                    raise ValueError(f"Odrzucono przez sieć FPS: {e}")

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