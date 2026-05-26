from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from domain.value_objects import AccountNumber, Money
from domain.repositories import AccountRepository


@dataclass
class CHAPSTransferUseCase:
    """CHAPS = Real Time Gross Settlement (RTGS) przez Bank of England."""
    
    account_repository: AccountRepository
    
    def execute(self, from_account_id: AccountNumber, to_sort_code: str, 
                to_account_number: str, amount: Money) -> dict:
        """
        CHAPS = Clearing House Automated Payment System
        - UK tylko
        - Natychmiastowy (RTGS - Real Time Gross Settlement)
        - Limit: 10 mln GBP
        - Dla dużych przelewów
        """
        
        # 1. Pobierz konto nadawcy
        source_account = self.account_repository.get_by_id(from_account_id)
        if not source_account:
            raise ValueError(f"Konto nadawcy {from_account_id.account_number} nie istnieje.")
        
        if not source_account.is_active:
            raise ValueError("Błąd: Konto nadawcy jest zamrożone (zablokowane). Przelew odrzucony.")

        # 2. Walidacja limitu CHAPS (10 mln GBP)
        if amount.amount > Decimal("10000000"):
            raise ValueError("CHAPS: Limit transakcji to max 10,000,000 GBP.")
        
        # 3. Obciąż nadawcę
        source_account.debit(amount)
        self.account_repository.save(source_account)
        
        # 4. Zwróć response (natychmiastowy)
        return {
            "status": "SUCCESS",
            "transfer_type": "CHAPS (Real Time Gross Settlement)",
            "from_account": from_account_id.account_number,
            "to_sort_code": to_sort_code,
            "to_account": to_account_number,
            "amount": float(amount.amount),
            "currency": amount.currency.value,
            "timestamp": datetime.now().isoformat(),
            "settlement_time": "Natychmiastowy (RTGS)",
            "bank": "Bank of England",
            "message": f"CHAPS transfer {amount.amount} {amount.currency.value} - natychmiastowe rozliczenie przez Bank of England."
        }
