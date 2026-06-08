import os
from datetime import datetime
from decimal import Decimal

from domain.value_objects import AccountNumber, Money, Currency
from domain.repositories import AccountRepository
from infrastructure.swift_client import SwiftMiddlewareClient


class SwiftNetworkService:
    """Łączy UK Bank B z siecią SWIFT (middleware ISO 20022 pacs.008).

    Wysyłanie: obciąża konto (kwota + 1% opłaty), buduje pacs.008, uwierzytelnia
    się (OAuth2) i wysyła do middleware; opcjonalnie auto-wyzwala forward.
    Odbieranie: endpoint /receive uznaje konto i odsyła ACK (callback).
    """

    EXCHANGE_RATES = {
        ("GBP", "EUR"): Decimal("1.17"),
        ("GBP", "USD"): Decimal("1.27"),
        ("GBP", "GBP"): Decimal("1.00"),
        ("EUR", "GBP"): Decimal("0.85"),
        ("EUR", "USD"): Decimal("1.09"),
        ("USD", "GBP"): Decimal("0.79"),
        ("USD", "EUR"): Decimal("0.92"),
    }
    SWIFT_FEE_PERCENT = Decimal("0.01")
    SORT_CODE = "102030"

    # Mapowanie kont odbiorczych (IBAN/Id z pacs.008) -> konto UK Bank B.
    INBOUND_ACCOUNT_MAP = {
        "GB29NWBK60161331926819": "11111111",
    }
    HOUSE_ACCOUNT = os.getenv("SWIFT_HOUSE_ACCOUNT", "11111111")

    def __init__(self, account_repo: AccountRepository, client: SwiftMiddlewareClient | None = None):
        self.account_repo = account_repo
        self.client = client or SwiftMiddlewareClient()

    # ===== WYSYŁANIE (UK Bank B -> świat) =====
    def send_international(
        self,
        *,
        from_account_id: AccountNumber,
        receiver_bic: str,
        receiver_account: str,
        amount: Money,
        to_currency: str = "GBP",
        receiver_name: str = "Beneficiary",
        sender_name: str = "UK Bank B Customer",
        charge_bearer: str = "SHAR",
        remittance_info: str = "",
        auto_send: bool = True,
    ) -> dict:
        account = self.account_repo.get_by_id(from_account_id)
        if not account:
            raise ValueError(f"Konto nadawcy {from_account_id.account_number} nie istnieje.")
        if not account.is_active:
            raise ValueError("Konto nadawcy jest zablokowane. Przelew odrzucony.")

        to_currency = (to_currency or "GBP").upper()
        if to_currency not in {"GBP", "EUR", "USD"}:
            raise ValueError(f"Nieobsługiwana waluta docelowa: {to_currency} (GBP/EUR/USD).")

        if amount.amount > Decimal("5000000"):
            raise ValueError("SWIFT: limit transakcji to 5,000,000.")

        fee = (amount.amount * self.SWIFT_FEE_PERCENT).quantize(Decimal("0.01"))
        total_debit = amount.amount + fee
        if account.balance.amount < total_debit:
            raise ValueError(
                f"Brak środków. Potrzeba {total_debit} (kwota {amount.amount} + opłata {fee}), "
                f"masz {account.balance.amount}."
            )

        rate = self.EXCHANGE_RATES.get((amount.currency.value, to_currency), Decimal("1.00"))
        received_amount = (amount.amount * rate).quantize(Decimal("0.01"))

        # 1. Zbuduj komunikat pacs.008 (kwota międzybankowa w walucie docelowej)
        xml, meta = self.client.build_pacs008_xml(
            amount=f"{received_amount:.2f}",
            currency=to_currency,
            receiver_bic=receiver_bic.strip().upper(),
            receiver_account=receiver_account.strip(),
            receiver_name=receiver_name or "Beneficiary",
            sender_name=sender_name or "UK Bank B Customer",
            charge_bearer=(charge_bearer or "SHAR").upper(),
            remittance_info=remittance_info,
        )

        # 2. Wyślij do middleware SWIFT
        status, body = self.client.send_message(xml)
        if status not in (200, 202):
            detail = body.get("error") or body.get("raw") or body
            raise ValueError(f"SWIFT middleware odrzucił komunikat ({status}): {detail}")

        uetr = body.get("uetr", meta["uetr"])

        # 3. Obciąż konto dopiero po przyjęciu komunikatu
        account.debit(Money(total_debit, amount.currency))
        self.account_repo.save(account)

        # 4. Opcjonalnie wyzwól forward (operator dashboard robi to ręcznie)
        send_result = None
        if auto_send:
            try:
                s_status, s_body = self.client.send_now(uetr)
                send_result = {"status_code": s_status, "body": s_body}
            except Exception as exc:
                send_result = {"error": str(exc)}

        return {
            "status": "SENT" if auto_send else "ACCEPTED",
            "transfer_type": "SWIFT (ISO 20022 pacs.008)",
            "uetr": uetr,
            "message_id": body.get("message_id", meta["message_id"]),
            "sender_bic": meta["sender_bic"],
            "receiver_bic": receiver_bic.strip().upper(),
            "receiver_bank": body.get("receiver_bank"),
            "route": body.get("route", []),
            "estimated_seconds": body.get("estimated_seconds"),
            "fee_breakdown": body.get("fee_breakdown", {}),
            "cancel_window_seconds": body.get("cancel_window_seconds"),
            "from_account": from_account_id.account_number,
            "from_currency": amount.currency.value,
            "to_currency": to_currency,
            "amount_sent": float(amount.amount),
            "bank_fee": float(fee),
            "total_debit": float(total_debit),
            "exchange_rate": float(rate),
            "amount_received": float(received_amount),
            "auto_send": auto_send,
            "send_result": send_result,
            "timestamp": datetime.now().isoformat(),
            "message": (
                f"SWIFT: wysłano {amount.amount} {amount.currency.value} "
                f"(opłata {fee}). Odbiorca {receiver_bic} otrzyma ~{received_amount} {to_currency}. "
                f"UETR={uetr}."
            ),
        }

    def cancel(self, uetr: str) -> dict:
        status, body = self.client.cancel(uetr)
        return {"status_code": status, "body": body}

    # ===== ODBIERANIE (świat -> UK Bank B) =====
    def receive_incoming(
        self,
        *,
        xml_body: str,
        currency: str,
        uetr: str,
        message_id: str,
        receiver_account: str,
        sender_account: str = "",
        settlement_date: str = "",
    ) -> tuple[dict, int]:
        """Odpowiednik mock-banku: waliduje pacs.008 i uznaje konto UK Bank B."""
        if currency and currency not in {"PLN", "EUR", "USD", "GBP"}:
            return {"status": "rejected", "reason": "unsupported_currency"}, 422
        if "<FIToFICstmrCdtTrf" not in xml_body:
            return {"status": "rejected", "reason": "invalid_pacs008"}, 400
        if "<UETR>" not in xml_body:
            return {"status": "rejected", "reason": "missing_uetr"}, 400
        if "<IntrBkSttlmAmt" not in xml_body:
            return {"status": "rejected", "reason": "missing_settlement_amount"}, 400

        closed_accounts = {"GB00CLOSED0000000000000000"}
        if receiver_account in closed_accounts:
            return {"status": "rejected", "reason": "receiver_account_closed"}, 422

        amount = self._extract_settlement_amount(xml_body)
        credited_account = None
        credited_amount = None
        if amount is not None and currency in {"GBP", "EUR", "USD"}:
            acc_num = self.INBOUND_ACCOUNT_MAP.get(receiver_account, self.HOUSE_ACCOUNT)
            account = self.account_repo.get_by_id(AccountNumber(self.SORT_CODE, acc_num))
            if account:
                try:
                    gbp_amount = self._to_gbp(amount, currency)
                    account.credit(Money(gbp_amount, Currency.GBP))
                    self.account_repo.save(account)
                    credited_account = acc_num
                    credited_amount = float(gbp_amount)
                except Exception:
                    credited_account = None

        return {
            "status": "accepted",
            "bank": "UK Bank B",
            "received_at": datetime.utcnow().isoformat() + "Z",
            "message_id": message_id,
            "uetr": uetr,
            "credited_account": credited_account,
            "credited_amount_gbp": credited_amount,
        }, 202

    def _to_gbp(self, amount: Decimal, currency: str) -> Decimal:
        if currency == "GBP":
            return amount.quantize(Decimal("0.01"))
        rate = self.EXCHANGE_RATES.get((currency, "GBP"), Decimal("1.00"))
        return (amount * rate).quantize(Decimal("0.01"))

    @staticmethod
    def _extract_settlement_amount(xml_body: str) -> Decimal | None:
        import re

        m = re.search(r"<IntrBkSttlmAmt[^>]*>([\d.]+)</IntrBkSttlmAmt>", xml_body)
        if not m:
            m = re.search(r"<InstdAmt[^>]*>([\d.]+)</InstdAmt>", xml_body)
        if not m:
            return None
        try:
            return Decimal(m.group(1))
        except Exception:
            return None
