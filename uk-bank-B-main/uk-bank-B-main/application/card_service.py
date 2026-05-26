import random
import bcrypt
from datetime import datetime
from decimal import Decimal
from domain.entities import Card
from domain.value_objects import AccountNumber, Money
from domain.repositories import AccountRepository, CardRepository

class CardService:
    def __init__(self, account_repo: AccountRepository, card_repo: CardRepository):
        self.account_repo = account_repo
        self.card_repo = card_repo

    def hash_pin(self, pin: str) -> str:
        """Zabezpiecza PIN algorytmem bcrypt (tak jak hasła)"""
        return bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def issue_card(self, sort_code: str, account_number: str, pin: str) -> Card:
        """Wydaje nową kartę płatniczą przypisaną do konta."""
        if len(pin) != 4 or not pin.isdigit():
            raise ValueError("Błąd: PIN musi składać się z dokładnie 4 cyfr.")

        acc = self.account_repo.get_by_id(AccountNumber(sort_code, account_number))
        if not acc:
            raise ValueError("Podane konto nie istnieje.")

        existing_cards = self.card_repo.get_by_account(account_number)
        if any(c.is_active for c in existing_cards):
            raise ValueError("To konto posiada już aktywną kartę. Zastrzeż ją, zanim wydasz nową.")

        # Symulacja numeru karty np. MasterCard (zaczyna się od 5)
        card_number = "5" + "".join([str(random.randint(0, 9)) for _ in range(15)])
        
        # Karta ważna przez 3 lata
        now = datetime.now()
        expiry_year = (now.year + 3) % 100
        expiry_date = f"{now.month:02d}/{expiry_year:02d}"
        
        cvv = f"{random.randint(0, 999):03d}"
        
        # Rozróżnienie limitów i typu (Dorosły vs Dziecko)
        is_junior = acc.account_type == "junior"
        card_type = "prepaid" if is_junior else "debit"
        daily_limit = Decimal("50.00") if is_junior else Decimal("2000.00")

        card = Card(
            card_number=card_number, account_number=account_number, expiry_date=expiry_date,
            cvv=cvv, pin_hash=self.hash_pin(pin), is_active=True, card_type=card_type,
            daily_limit=Money(daily_limit, acc.balance.currency)
        )
        self.card_repo.save(card)
        return card
        
    def get_cards_for_account(self, account_number: str) -> list[Card]:
        return self.card_repo.get_by_account(account_number)

    def block_card(self, card_number: str) -> None:
        """Bezpowrotnie zastrzega / blokuje kartę płatniczą."""
        card = self.card_repo.get_by_number(card_number)
        if not card:
            raise ValueError("Błąd: Podana karta nie istnieje.")
        card.is_active = False
        self.card_repo.save(card)