"""Logika integracji KLIK (C2B kody + P2P telefony) dla UK Bank B."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from domain.value_objects import AccountNumber, Money, Currency
from domain.repositories import AccountRepository
from infrastructure.klik_client import KlikClient, klik_config


def _now() -> datetime:
    return datetime.now(timezone.utc)


def account_user_id(sort_code: str, account_number: str) -> str:
    return f"{sort_code.replace('-', '')}-{account_number}"


def account_iban(sort_code: str, account_number: str) -> str:
    sc = sort_code.replace("-", "")
    return f"GB89UKBK{sc}{account_number}"


def parse_user_id(user_id: str) -> AccountNumber | None:
    if not user_id or "-" not in user_id:
        return None
    sort_raw, acc = user_id.split("-", 1)
    if len(sort_raw) != 6 or not sort_raw.isdigit() or len(acc) != 8 or not acc.isdigit():
        return None
    dashed = f"{sort_raw[0:2]}-{sort_raw[2:4]}-{sort_raw[4:6]}"
    return AccountNumber(dashed, acc)


def iban_to_account(iban: str) -> AccountNumber | None:
    iban = (iban or "").replace(" ", "").upper()
    if iban.startswith("GB") and len(iban) >= 22:
        sort_raw = iban[8:14]
        acc = iban[14:22]
        if sort_raw.isdigit() and acc.isdigit():
            return AccountNumber(
                f"{sort_raw[0:2]}-{sort_raw[2:4]}-{sort_raw[4:6]}", acc
            )
    return None


def normalize_sort_code(sort_code: str) -> str:
    raw = sort_code.replace("-", "").strip()
    if len(raw) != 6 or not raw.isdigit():
        raise ValueError("Nieprawidłowy sort code")
    return f"{raw[0:2]}-{raw[2:4]}-{raw[4:6]}"


@dataclass
class KlikService:
    account_repository: AccountRepository
    client: KlikClient = field(default_factory=KlikClient)
    demo_pin: str = "1234"
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _pending: dict[str, dict] = field(default_factory=dict, repr=False)
    _code_queue: list[dict] = field(default_factory=list, repr=False)
    _aliases: dict[str, dict] = field(default_factory=dict, repr=False)
    _state_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "klik_state.json",
        repr=False,
    )

    def __post_init__(self):
        self._load_state()

    def _load_state(self) -> None:
        if not self._state_path.exists():
            return
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            self._aliases = data.get("aliases", {})
        except Exception:
            pass

    def _save_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps({"aliases": self._aliases}, indent=2),
            encoding="utf-8",
        )

    def _prune_expired(self) -> None:
        now = _now()
        with self._lock:
            self._code_queue = [c for c in self._code_queue if c["expires_at"] > now]
            expired = [
                tid
                for tid, p in self._pending.items()
                if p.get("expiry_time") and p["expiry_time"] <= now
            ]
            for tid in expired:
                p = self._pending.pop(tid, None)
                if p:
                    p["status"] = "EXPIRED"

    def list_accounts(self) -> list[dict]:
        accounts = []
        for acc_num in ("11111111", "22222222"):
            acc_id = AccountNumber("102030", acc_num)
            acc = self.account_repository.get_by_id(acc_id)
            if not acc:
                continue
            uid = account_user_id(acc_id.sort_code, acc_id.account_number)
            phone = self._aliases.get(uid, {}).get("phone")
            accounts.append({
                "user_id": uid,
                "sort_code": acc_id.sort_code,
                "account_number": acc_id.account_number,
                "iban": account_iban(acc_id.sort_code, acc_id.account_number),
                "balance": float(acc.balance.amount),
                "phone": phone,
                "alias_registered": bool(phone),
            })
        return accounts

    def generate_code(self, sort_code: str, account_number: str) -> dict:
        acc_id = AccountNumber(normalize_sort_code(sort_code), account_number)
        acc = self.account_repository.get_by_id(acc_id)
        if not acc:
            raise ValueError(f"Konto {acc_id} nie istnieje.")

        user_id = account_user_id(acc_id.sort_code, acc_id.account_number)
        result = self.client.generate_code(user_id)
        expires_in = int(result.get("expires_in", 120))
        with self._lock:
            self._code_queue.append({
                "user_id": user_id,
                "code": result.get("code"),
                "expires_at": _now() + timedelta(seconds=expires_in),
            })
        return {
            "code": result.get("code"),
            "expires_in": expires_in,
            "expires_at": result.get("expires_at"),
            "user_id": user_id,
            "account": acc_id.account_number,
        }

    def handle_authorize_webhook(self, payload: dict) -> dict:
        self._prune_expired()
        transaction_id = payload.get("transaction_id")
        amount = payload.get("amount")
        if not transaction_id or amount is None:
            raise ValueError("transaction_id i amount są wymagane")

        expiry_dt = None
        if payload.get("expiry_time"):
            try:
                expiry_dt = datetime.fromisoformat(
                    str(payload["expiry_time"]).replace("Z", "+00:00")
                )
            except ValueError:
                expiry_dt = _now() + timedelta(seconds=120)
        else:
            expiry_dt = _now() + timedelta(seconds=120)

        user_id = payload.get("user_id")
        if not user_id:
            with self._lock:
                while self._code_queue:
                    cand = self._code_queue.pop(0)
                    if cand["expires_at"] > _now():
                        user_id = cand["user_id"]
                        break

        acc_id = parse_user_id(user_id) if user_id else None
        with self._lock:
            self._pending[transaction_id] = {
                "transaction_id": transaction_id,
                "amount": str(amount),
                "currency": payload.get("currency", "GBP"),
                "merchant_name": payload.get("merchant_name", ""),
                "is_on_us": payload.get("is_on_us", False),
                "expiry_time": expiry_dt,
                "zone": payload.get("zone", klik_config()["zone"]),
                "user_id": user_id,
                "account_id": f"{acc_id.sort_code}/{acc_id.account_number}" if acc_id else None,
                "status": "PENDING",
                "received_at": _now().isoformat(),
            }
        return {"received": True, "will_prompt_user": True}

    def handle_ping_webhook(self, payload: dict) -> dict:
        return {
            "timestamp": payload.get("timestamp"),
            "nonce": payload.get("nonce"),
            "pong": True,
        }

    def list_pending(self) -> list[dict]:
        self._prune_expired()
        items = []
        with self._lock:
            for tid, p in self._pending.items():
                if p.get("status") != "PENDING":
                    continue
                seconds_left = None
                if p.get("expiry_time"):
                    seconds_left = max(0, int((p["expiry_time"] - _now()).total_seconds()))
                balance = None
                sufficient = None
                acc_id = parse_user_id(p.get("user_id") or "")
                if acc_id:
                    acc = self.account_repository.get_by_id(acc_id)
                    if acc:
                        balance = float(acc.balance.amount)
                        sufficient = balance >= float(p["amount"])
                items.append({
                    **p,
                    "seconds_left": seconds_left,
                    "client_balance": balance,
                    "sufficient_balance": sufficient,
                })
        return items

    def accept_payment(self, transaction_id: str, pin: str) -> dict:
        self._prune_expired()
        with self._lock:
            payment = self._pending.get(transaction_id)
        if not payment or payment.get("status") != "PENDING":
            raise ValueError("Brak oczekującej autoryzacji KLIK.")

        if pin != self.demo_pin:
            raise ValueError("Błędny PIN (demo: 1234).")

        if payment.get("expiry_time") and payment["expiry_time"] <= _now():
            self._reject_remote(transaction_id, "TIMEOUT")
            with self._lock:
                payment["status"] = "EXPIRED"
            raise ValueError("Kod płatności wygasł.")

        user_id = payment.get("user_id")
        acc_id = parse_user_id(user_id or "")
        if not acc_id:
            raise ValueError("Nie można powiązać płatności z kontem.")

        acc = self.account_repository.get_by_id(acc_id)
        if not acc:
            raise ValueError("Konto nadawcy nie istnieje.")

        amount = Money(Decimal(str(payment["amount"])), Currency.GBP)
        if acc.balance.amount < amount.amount:
            self._reject_remote(transaction_id, "INSUFFICIENT_FUNDS")
            with self._lock:
                payment["status"] = "REJECTED"
            raise ValueError("Niewystarczające środki.")

        result = self.client.confirm_payment(transaction_id, "ACCEPTED")
        acc.debit(amount)
        self.account_repository.save(acc)

        with self._lock:
            payment["status"] = "ACCEPTED"
            self._pending.pop(transaction_id, None)

        return {
            **result,
            "debited_account": acc_id.account_number,
            "new_balance": float(acc.balance.amount),
        }

    def reject_payment(self, transaction_id: str, reason: str = "USER_DECLINED") -> dict:
        with self._lock:
            payment = self._pending.get(transaction_id)
        if not payment or payment.get("status") != "PENDING":
            raise ValueError("Brak oczekującej autoryzacji KLIK.")
        result = self._reject_remote(transaction_id, reason)
        with self._lock:
            payment["status"] = "REJECTED"
            self._pending.pop(transaction_id, None)
        return result

    def _reject_remote(self, transaction_id: str, reason: str) -> dict:
        reject_reason = reason if reason in {
            "INSUFFICIENT_FUNDS", "USER_DECLINED", "PIN_FAILED", "AML_BLOCK", "OTHER"
        } else "OTHER"
        try:
            return self.client.confirm_payment(transaction_id, "REJECTED", reject_reason)
        except Exception:
            return {"transaction_id": transaction_id, "status": "REJECTED"}

    def register_alias(self, sort_code: str, account_number: str, phone: str) -> dict:
        acc_id = AccountNumber(normalize_sort_code(sort_code), account_number)
        acc = self.account_repository.get_by_id(acc_id)
        if not acc:
            raise ValueError("Konto nie istnieje.")
        iban = account_iban(acc_id.sort_code, acc_id.account_number)
        result = self.client.register_alias(phone, iban)
        user_id = account_user_id(acc_id.sort_code, acc_id.account_number)
        with self._lock:
            self._aliases[user_id] = {"phone": phone, "iban": iban}
        self._save_state()
        return result

    def remove_alias(self, sort_code: str, account_number: str, phone: str) -> dict:
        sc = normalize_sort_code(sort_code)
        result = self.client.delete_alias(phone)
        user_id = account_user_id(sc, account_number)
        with self._lock:
            self._aliases.pop(user_id, None)
        self._save_state()
        return result

    def get_alias(self, sort_code: str, account_number: str) -> dict | None:
        user_id = account_user_id(normalize_sort_code(sort_code), account_number)
        return self._aliases.get(user_id)

    def send_p2p(self, from_sort: str, from_account: str, phone: str, amount: Decimal) -> dict:
        if amount <= 0:
            raise ValueError("Kwota musi być większa od zera.")

        sender_id = AccountNumber(normalize_sort_code(from_sort), from_account)
        sender = self.account_repository.get_by_id(sender_id)
        if not sender:
            raise ValueError("Konto nadawcy nie istnieje.")
        if sender.balance.amount < amount:
            raise ValueError("Niewystarczające środki.")

        alias = self.client.lookup_alias(phone)
        recipient_iban = alias.get("iban") or (
            (alias.get("account_identifier") or {}).get("value")
        )
        if not recipient_iban:
            raise ValueError("Alias KLIK nie zawiera IBAN odbiorcy.")

        sender_iban = account_iban(sender_id.sort_code, sender_id.account_number)
        if recipient_iban.replace(" ", "").upper() == sender_iban:
            raise ValueError("Nie możesz wysłać na własny numer telefonu.")

        money = Money(amount, Currency.GBP)
        recipient_id = iban_to_account(recipient_iban)
        sender.debit(money)
        self.account_repository.save(sender)

        credited_locally = False
        if recipient_id:
            recipient = self.account_repository.get_by_id(recipient_id)
            if recipient:
                recipient.credit(money)
                self.account_repository.save(recipient)
                credited_locally = True

        return {
            "status": "COMPLETED",
            "phone": phone,
            "recipient_iban": recipient_iban,
            "amount": str(amount),
            "currency": "GBP",
            "recipient_found_in_this_bank": credited_locally,
            "sender_balance": float(sender.balance.amount),
        }
