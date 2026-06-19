#!/usr/bin/env python3
"""Rejestruje UK Bank B + demo agenta/merchanta w KLIK — uruchamiane w klik-init."""
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

# Django backend KLIK (montowany w obrazie Dockera)
BACKEND = Path("/klik-upstream/backend")
if BACKEND.is_dir():
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)

BANK_API_KEY = os.environ.get("KLIK_SEED_API_KEY", "klik_dev_uk_bank_b_school_demo")
AGENT_API_KEY = os.environ.get("KLIK_SEED_AGENT_API_KEY", "klik_dev_agent_uk_school_demo")
WEBHOOK = os.environ.get(
    "KLIK_WEBHOOK_URL",
    "http://uk-bank-b:8000/api/klik/webhook",
)
UK_AGENT_IBAN = {"type": "iban", "value": "GB29NWBK60161331926819"}
UK_MERCHANT_IBAN = {"type": "iban", "value": "GB82WEST12345698765432"}


def _setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
    import django

    for attempt in range(1, 31):
        try:
            django.setup()
            return
        except Exception as exc:
            print(f"[klik-init] czekam na Django/DB ({attempt}/30): {exc}", flush=True)
            time.sleep(2)
    print("[klik-init] BŁĄD: nie udało się uruchomić Django", flush=True)
    sys.exit(1)


def seed_bank():
    from banks.models import Bank, hash_api_key

    bank, created = Bank.objects.update_or_create(
        name="UK Bank B",
        defaults={
            "api_key_hash": hash_api_key(BANK_API_KEY),
            "zone": "UK",
            "currency": "GBP",
            "webhook_url": WEBHOOK,
            "c2b_enabled": True,
            "p2p_enabled": True,
            "p2p_lookup_fee": Decimal("0"),
            "active": True,
            "debt_limit": Decimal("999999999"),
        },
    )
    action = "utworzono" if created else "zaktualizowano"
    print(f"[klik-init] Bank {action}: {bank.name} (active={bank.active})", flush=True)
    print(f"[klik-init] Klucz banku (uk-bank-b): {BANK_API_KEY}", flush=True)
    return bank


def seed_agent(bank):
    from django.utils import timezone

    from agents.authentication import hash_api_key as hash_agent_key
    from agents.models import Agent, MSCAgreement
    from common.enums import Zone
    from merchants.models import Merchant

    agent, created = Agent.objects.update_or_create(
        name="UK Demo Agent",
        defaults={
            "api_key_hash": hash_agent_key(AGENT_API_KEY),
            "settlement_bank": bank,
            "account_identifier": UK_AGENT_IBAN,
            "zone": Zone.UK,
            "active": True,
        },
    )
    action = "utworzono" if created else "zaktualizowano"
    print(f"[klik-init] Agent {action}: {agent.name}", flush=True)
    print(f"[klik-init] Klucz agenta (terminal :8175): {AGENT_API_KEY}", flush=True)

    MSCAgreement.objects.update_or_create(
        agent=agent,
        valid_to=None,
        defaults={
            "klik_fee_perc": Decimal("0.30"),
            "agent_fee_perc": Decimal("1.00"),
            "valid_from": timezone.now() - timezone.timedelta(days=1),
        },
    )

    merchant, m_created = Merchant.objects.update_or_create(
        name="UK Demo Merchant",
        defaults={
            "settlement_bank": bank,
            "account_identifier": UK_MERCHANT_IBAN,
            "zone": Zone.UK,
            "active": True,
        },
    )
    print(
        f"[klik-init] Merchant {'utworzono' if m_created else 'zaktualizowano'}: "
        f"{merchant.name} (id={merchant.id})",
        flush=True,
    )


def ping_webhook():
    try:
        import requests

        ping_url = WEBHOOK.rstrip("/") + "/ping"
        r = requests.post(
            ping_url,
            json={"timestamp": "2026-01-01T00:00:00Z", "nonce": "klik-init"},
            timeout=10,
        )
        print(f"[klik-init] Webhook ping: HTTP {r.status_code}", flush=True)
    except Exception as exc:
        print(f"[klik-init] Webhook ping pominięty: {exc}", flush=True)


def main() -> int:
    _setup_django()
    bank = seed_bank()
    try:
        seed_agent(bank)
    except Exception as exc:
        print(f"[klik-init] BŁĄD seed agenta: {exc}", flush=True)
        return 1
    ping_webhook()
    return 0


if __name__ == "__main__":
    sys.exit(main())
