import bcrypt
from decimal import Decimal

from domain.entities import Card
from domain.value_objects import AccountNumber, Currency, Money
from domain.repositories import AccountRepository, CardRepository
from infrastructure.card_gateway_client import CardGatewayClient


class CardService:
    def __init__(
        self,
        account_repo: AccountRepository,
        card_repo: CardRepository,
        gateway: CardGatewayClient | None = None,
    ):
        self.account_repo = account_repo
        self.card_repo = card_repo
        self.gateway = gateway or CardGatewayClient()

    def hash_pin(self, pin: str) -> str:
        return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def issue_card(self, sort_code: str, account_number: str, pin: str, user_id: str = "customer") -> Card:
        if len(pin) != 4 or not pin.isdigit():
            raise ValueError("Błąd: PIN musi składać się z dokładnie 4 cyfr.")

        acc = self.account_repo.get_by_id(AccountNumber(sort_code, account_number))
        if not acc:
            raise ValueError("Podane konto nie istnieje.")

        existing_cards = self.card_repo.get_by_account(account_number)
        if any(c.is_active for c in existing_cards):
            raise ValueError("To konto posiada już aktywną kartę. Zastrzeż ją, zanim wydasz nową.")

        is_junior = acc.account_type == "junior"
        daily_limit = Money(Decimal("50.00") if is_junior else Decimal("2000.00"), acc.balance.currency)

        try:
            gateway_response = self.gateway.issue_card(
                user_id=user_id,
                account_id=account_number,
                card_type="PREPAID",
                initial_balance=float(acc.balance.amount),
            )
            card_token = gateway_response["card_token"]
            self.gateway.prepare_prepaid_for_payments(card_token)
        except Exception as exc:
            health = self.gateway.health_check()
            if not health.get("ok"):
                raise ValueError(
                    "Moduł kart płatniczych jest niedostępny. "
                    f"Uruchom Payment Gateway ({health.get('url')}) i spróbuj ponownie. "
                    f"Szczegóły: {health.get('error', exc)}"
                ) from exc
            raise ValueError(f"Błąd wydania karty w Payment Gateway: {exc}") from exc

        expiry_month = gateway_response["expiry_month"]
        expiry_year = gateway_response["expiry_year"]
        expiry_date = f"{expiry_month:02d}/{expiry_year:02d}"

        card = Card(
            card_number=gateway_response["full_pan"],
            account_number=account_number,
            expiry_date=expiry_date,
            cvv=gateway_response["cvv"],
            pin_hash=self.hash_pin(pin),
            is_active=True,
            card_type="prepaid" if is_junior else "debit",
            daily_limit=daily_limit,
            card_token=card_token,
            gateway_status="ACTIVE",
            masked_pan=gateway_response.get("masked_pan", ""),
            expiry_month=expiry_month,
            expiry_year=expiry_year,
        )
        self.card_repo.save(card)
        try:
            self.sync_card_balance(card.card_token)
        except Exception:
            pass
        return card

    def sync_card_balance(self, card_token: str) -> float:
        """Doładowuje kartę prepaid różnicą między saldem konta a saldem na karcie."""
        card = self.card_repo.get_by_token(card_token)
        if not card:
            raise ValueError("Karta nie istnieje.")

        acc = self.account_repo.get_by_id(AccountNumber("102030", card.account_number))
        if not acc:
            raise ValueError("Konto nie istnieje.")

        status = self.gateway.get_card_status(card_token)
        card_balance = float(status.get("balance", 0))
        account_balance = float(acc.balance.amount)
        diff = round(account_balance - card_balance, 2)

        if diff > 0:
            result = self.gateway.topup(card_token, diff, acc.balance.currency.value)
            return float(result.get("new_balance", account_balance))
        return card_balance

    def get_cards_for_account(self, account_number: str) -> list[Card]:
        return self.card_repo.get_by_account(account_number)

    def block_card(self, card_number: str) -> None:
        card = self.card_repo.get_by_number(card_number)
        if not card:
            raise ValueError("Błąd: Podana karta nie istnieje.")

        if card.card_token:
            self.gateway.update_status(card.card_token, "BLOCKED", "Blocked by customer")

        card.is_active = False
        card.gateway_status = "BLOCKED"
        self.card_repo.save(card)

    def activate_card(self, card_token: str) -> None:
        card = self.card_repo.get_by_token(card_token)
        if not card:
            raise ValueError("Karta nie istnieje.")
        self.gateway.activate_card(card_token, card.account_number)
        card.is_active = True
        card.gateway_status = "ACTIVE"
        self.card_repo.save(card)
