import uuid
from decimal import Decimal

from domain.entities import Card
from domain.repositories import AccountRepository, CardRepository
from domain.value_objects import AccountNumber, Currency, Money


class CardSettlementService:
    """Obsługa settlementu z modułu kart (capture / authorize / refund)."""

    def __init__(self, account_repo: AccountRepository, card_repo: CardRepository):
        self.account_repo = account_repo
        self.card_repo = card_repo

    def _find_account_for_card(self, card: Card) -> AccountNumber:
        return AccountNumber("102030", card.account_number)

    def capture(
        self,
        authorization_code: str,
        amount: float,
        currency: str,
        card_token: str | None = None,
        transaction_id: str | None = None,
    ) -> dict:
        card = None
        if card_token:
            card = self.card_repo.get_by_token(card_token)
        if not card and authorization_code:
            card = self.card_repo.get_by_authorization_code(authorization_code)

        if not card:
            return {"status": "DECLINED", "message": "Card not found for capture"}

        account_id = self._find_account_for_card(card)
        account = self.account_repo.get_by_id(account_id)
        if not account:
            return {"status": "DECLINED", "message": "Account not found"}

        if not account.is_active:
            return {"status": "DECLINED", "decline_reason": "ACCOUNT_BLOCKED"}

        money = Money(Decimal(str(amount)), Currency(currency))
        try:
            account.debit(money)
        except Exception as exc:
            return {"status": "DECLINED", "decline_reason": str(exc)}

        self.account_repo.save(account)
        self.card_repo.save_capture(
            authorization_code=authorization_code,
            transaction_id=transaction_id or str(uuid.uuid4()),
            card_number=card.card_number,
            amount=amount,
            currency=currency,
            status="SETTLED",
        )
        return {"status": "SETTLED"}

    def authorize(
        self,
        account_id: str,
        amount: float,
        currency: str,
        transaction_id: str,
        merchant_name: str | None = None,
    ) -> dict:
        account = self.account_repo.get_by_id(AccountNumber("102030", account_id))
        if not account:
            return {
                "status": "DECLINED",
                "authorization_code": None,
                "decline_reason": "ACCOUNT_BLOCKED",
            }

        if not account.is_active:
            return {
                "status": "DECLINED",
                "authorization_code": None,
                "decline_reason": "ACCOUNT_BLOCKED",
            }

        money = Money(Decimal(str(amount)), Currency(currency))
        available = account.balance.amount + account.debt_limit.amount
        if money.amount > available:
            return {
                "status": "DECLINED",
                "authorization_code": None,
                "decline_reason": "INSUFFICIENT_FUNDS",
            }

        auth_code = uuid.uuid4().hex[:12].upper()
        self.card_repo.save_authorization_hold(
            authorization_code=auth_code,
            account_number=account_id,
            amount=amount,
            currency=currency,
            transaction_id=transaction_id,
            merchant_name=merchant_name or "",
        )
        return {
            "status": "APPROVED",
            "authorization_code": auth_code,
            "decline_reason": None,
        }

    def refund(
        self,
        account_id: str,
        amount: float,
        currency: str,
        original_transaction_id: str,
    ) -> dict:
        account = self.account_repo.get_by_id(AccountNumber("102030", account_id))
        if not account:
            return {"status": "DECLINED"}

        money = Money(Decimal(str(amount)), Currency(currency))
        account.credit(money)
        self.account_repo.save(account)
        self.card_repo.save_refund(original_transaction_id, amount, currency)
        return {"status": "REFUNDED"}
