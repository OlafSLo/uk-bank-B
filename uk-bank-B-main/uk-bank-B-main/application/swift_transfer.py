from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from domain.value_objects import AccountNumber, Money, Currency
from domain.repositories import AccountRepository


@dataclass
class SWIFTTransferUseCase:
    """SWIFT - Międzynarodowy transfer bankowy (SEPA, ACH, itp)."""
    
    account_repository: AccountRepository
    
    # Symulacja exchange rates
    EXCHANGE_RATES = {
        ("GBP", "EUR"): Decimal("1.17"),
        ("GBP", "USD"): Decimal("1.27"),
        ("EUR", "GBP"): Decimal("0.85"),
        ("EUR", "USD"): Decimal("1.09"),
        ("USD", "GBP"): Decimal("0.79"),
        ("USD", "EUR"): Decimal("0.92"),
    }
    
    SWIFT_FEE_PERCENT = Decimal("0.01")  # 1% opłata
    
    def execute(self, from_account_id: AccountNumber, to_sort_code: str,
                to_account_number: str, amount: Money, 
                to_currency: str = "GBP") -> dict:
        """
        SWIFT = Society for Worldwide Interbank Financial Telecommunication
        - Międzynarodowy
        - Obsługuje GBP, EUR, USD, itp
        - Czas: 1-3 dni
        - Opłata: 1%
        - Exchange rate (symulacja)
        """
        
        # 1. Pobierz konto nadawcy
        source_account = self.account_repository.get_by_id(from_account_id)
        if not source_account:
            raise ValueError(f"Konto nadawcy {from_account_id.account_number} nie istnieje.")
        
        if not source_account.is_active:
            raise ValueError("Błąd: Konto nadawcy jest zamrożone (zablokowane). Przelew odrzucony.")

        # 2. Walidacja waluty docelowej
        try:
            dest_currency = Currency[to_currency]
        except KeyError:
            raise ValueError(f"Nieobsługiwana waluta: {to_currency}. Dostępne: GBP, EUR, USD")
        
        # 3. Limit SWIFT: 5 mln GBP
        if amount.amount > Decimal("5000000"):
            raise ValueError("SWIFT: Limit transakcji to max 5,000,000 GBP.")
        
        # 4. Oblicz opłatę (1% kwoty)
        fee = amount.amount * self.SWIFT_FEE_PERCENT
        total_debit = amount.amount + fee
        
        # 5. Sprawdź czy są wystarczające środki (na opłatę też)
        if source_account.balance.amount < total_debit:
            raise ValueError(
                f"Brak wystarczających środków. Potrzebujesz: {total_debit} "
                f"(przelew: {amount.amount} + opłata: {fee}), masz: {source_account.balance.amount}"
            )
        
        # 6. Obciąż nadawcę (kwota + opłata)
        total_money = Money(total_debit, amount.currency)
        source_account.debit(total_money)
        self.account_repository.save(source_account)
        
        # 7. Oblicz exchange rate (symulacja)
        rate_key = (amount.currency.value, to_currency)
        if rate_key in self.EXCHANGE_RATES:
            exchange_rate = self.EXCHANGE_RATES[rate_key]
            received_amount = amount.amount * exchange_rate
        else:
            # Jeśli ta kombinacja nie istnieje, zwróć 1:1
            exchange_rate = Decimal("1.00")
            received_amount = amount.amount
        
        # 8. Zwróć response
        return {
            "status": "PENDING",
            "transfer_type": "SWIFT (Międzynarodowy)",
            "from_account": from_account_id.account_number,
            "from_currency": amount.currency.value,
            "to_sort_code": to_sort_code,
            "to_account": to_account_number,
            "to_currency": to_currency,
            "amount_sent": float(amount.amount),
            "fee": float(fee),
            "total_debit": float(total_debit),
            "exchange_rate": float(exchange_rate),
            "amount_received": float(received_amount),
            "timestamp": datetime.now().isoformat(),
            "settlement_time": "1-3 dni robocze",
            "message": f"SWIFT: Wysłano {amount.amount} {amount.currency.value}, "
                       f"opłata {fee} {amount.currency.value}. "
                       f"Odbiorca otrzyma ~{received_amount} {to_currency} (kurs: {exchange_rate})."
        }
