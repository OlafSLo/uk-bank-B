#!/usr/bin/env python3
"""
Pełny test integracji kart: wydanie → płatność POS → settlement na koncie bankowym.

Uruchomienie (moduł kart + bank muszą działać):
    python scripts/test_card_e2e.py
"""

import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.card_gateway_client import CardGatewayClient

BANK_URL = os.getenv("BANK_URL", "http://localhost:8000")
GATEWAY_URL = os.getenv("CARD_GATEWAY_URL", "http://localhost:8072")
SORT_CODE = "102030"
ACCOUNT = "11111111"
PAYMENT_AMOUNT = float(os.getenv("TEST_PAYMENT_AMOUNT", "10.0"))
SETTLEMENT_WAIT_SEC = int(os.getenv("SETTLEMENT_WAIT_SEC", "35"))


def step(name: str, ok: bool, detail=None) -> bool:
    mark = "OK" if ok else "FAIL"
    print(f"[{mark}] {name}")
    if detail is not None:
        if isinstance(detail, (dict, list)):
            print(json.dumps(detail, indent=2, ensure_ascii=False))
        else:
            print(f"       {detail}")
    return ok


def get_account_balance() -> float | None:
    try:
        r = requests.get(f"{BANK_URL}/api/account/{SORT_CODE}/{ACCOUNT}", timeout=8)
        if r.status_code == 200:
            return float(r.json()["balance"])
    except Exception:
        pass
    return None


def main() -> int:
    print("=" * 60)
    print("  UK Bank B - test E2E kart (wydanie -> POS -> settlement)")
    print("=" * 60)

    all_ok = True

    gw = CardGatewayClient()
    health = gw.health_check()
    all_ok &= step("Payment Gateway dostępny", health.get("ok"), health)

    bal_before = get_account_balance()
    all_ok &= step(
        f"Saldo konta {ACCOUNT} przed testem",
        bal_before is not None,
        f"GBP {bal_before:.2f}" if bal_before is not None else "brak odpowiedzi banku",
    )
    if bal_before is not None and bal_before < PAYMENT_AMOUNT:
        print(
            f"\nUWAGA: Saldo (GBP {bal_before:.2f}) jest za niskie na platnosc GBP {PAYMENT_AMOUNT:.2f}."
            "\nZresetuj bazę: docker compose down -v && docker compose up --build -d"
        )
        return 1

    try:
        issued = gw.issue_card(
            user_id="e2e_test",
            account_id=ACCOUNT,
            card_type="PREPAID",
            initial_balance=min(bal_before or 100.0, 500.0),
        )
        gw.prepare_prepaid_for_payments(issued["card_token"])
        pan = issued["full_pan"]
        cvv = issued["cvv"]
        month = issued["expiry_month"]
        year = issued["expiry_year"]
        all_ok &= step(
            "Wydanie karty PREPAID (HMAC → Gateway)",
            bool(pan),
            {
                "pan": pan,
                "cvv": cvv,
                "expiry_month": month,
                "expiry_year": year,
                "pos_hint": "W POS wpisz rok jako 2 cyfry (np. 29, NIE 2029)",
            },
        )
    except Exception as exc:
        step("Wydanie karty PREPAID", False, str(exc))
        return 1

    pos_body = {
        "card_number": pan,
        "expiry_month": month,
        "expiry_year": year,
        "cvv": cvv,
        "amount": PAYMENT_AMOUNT,
        "currency": "PLN",
        "merchant_id": "SHOP_001",
        "merchant_name": "Test Shop",
    }
    try:
        r = requests.post(
            f"{GATEWAY_URL}/api/v1/payments/authorize",
            json=pos_body,
            timeout=30,
        )
        pay = r.json()
        approved = r.status_code == 200 and pay.get("approved") is True
        all_ok &= step("Płatność POS (POST /api/v1/payments/authorize)", approved, pay)
    except Exception as exc:
        all_ok &= step("Płatność POS", False, str(exc))
        return 1

    if not approved:
        print("\nTypowe powody DECLINED:")
        print("  - rok ważności 2029 zamiast 29")
        print("  - kwota większa niż saldo PREPAID na karcie")
        print("  - zły CVV lub numer karty")
        return 1

    print(f"\nCzekam {SETTLEMENT_WAIT_SEC}s na settlement (obciążenie konta)...")
    time.sleep(SETTLEMENT_WAIT_SEC)

    bal_after = get_account_balance()
    settled = bal_after is not None and bal_before is not None and bal_after < bal_before
    all_ok &= step(
        "Settlement – spadek salda konta bankowego",
        settled,
        {
            "balance_before": bal_before,
            "balance_after": bal_after,
            "expected_drop": PAYMENT_AMOUNT,
        },
    )

    print("-" * 60)
    if all_ok:
        print("Wynik E2E: SUKCES")
        print(f"  GUI karty:  {BANK_URL}/karta")
        print(f"  Terminal:   {GATEWAY_URL}/pos")
        return 0

    print("Wynik E2E: BŁĄD")
    print("Sprawdź: .\\scripts\\connect-cards-network.ps1 (sieć cards-backend)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
