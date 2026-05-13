from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from domain.value_objects import AccountNumber, Money
from domain.repositories import AccountRepository


@dataclass
class FPSTransferUseCase:
    """Natychmiastowy przelew (Faster Payments) - do 1 dnia, szybciej niż BACS (3 dni)."""
    
    account_repository: AccountRepository
    
    def execute(self, from_account_id: AccountNumber, to_sort_code: str, 
                to_account_number: str, amount: Money) -> dict:
        """
        Wykonuje transfer FPS.
        
        FPS = Faster Payments
        - Działa w UK
        - Natychmiastowy lub do 1 dnia
        - Dla naszej symulacji: od razu success
        """
        
        # 1. Pobierz konto nadawcy (musi być u nas)
        source_account = self.account_repository.get_by_id(from_account_id)
        if not source_account:
            raise ValueError(f"Konto nadawcy {from_account_id.account_number} nie istnieje.")
        
        # 2. Walidacja: FPS ma limit 250,000 GBP w UK (uproszczenie)
        if amount.amount > Decimal("250000"):
            raise ValueError("FPS: Limit transakcji to max 250,000 GBP.")
        
        # 3. Obciąż nadawcę
        source_account.debit(amount)
        self.account_repository.save(source_account)
        
        # 4. Zwróć response z czasem (symulacja: od razu success)
        return {
            "status": "SUCCESS",
            "transfer_type": "Faster Payments (FPS)",
            "from_account": from_account_id.account_number,
            "to_sort_code": to_sort_code,
            "to_account": to_account_number,
            "amount": float(amount.amount),
            "currency": amount.currency.value,
            "timestamp": datetime.now().isoformat(),
            "settlement_time": "Natychmiastowy (do 1 dnia)",
            "message": f"Transfer {amount.amount} {amount.currency.value} został wysłany. Odbiorca otrzyma środki natychmiastowo lub w ciągu 1 dnia."
        }
