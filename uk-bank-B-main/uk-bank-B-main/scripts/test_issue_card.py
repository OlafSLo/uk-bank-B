#!/usr/bin/env python3
"""Test wydania karty UK Bank B -> Payment Gateway (HMAC, UK_BANK_B)."""

import json
import os
import sys

# Dodaj root projektu do PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.card_gateway_client import CardGatewayClient


def main() -> int:
    gw = CardGatewayClient()
    print(f"Gateway URL: {gw.base_url}")

    health = gw.health_check()
    print(f"Health: {json.dumps(health, indent=2)}")
    if not health.get("ok"):
        print("\nUruchom modul kart (port 8072), potem sprobuj ponownie.")
        return 1

    print("\nWydawanie karty PREPAID dla konta 11111111...")
    try:
        result = gw.issue_card(
            user_id="uk_bank_test",
            account_id="11111111",
            card_type="PREPAID",
            initial_balance=5000.0,
        )
        token = result["card_token"]
        gw.prepare_prepaid_for_payments(token)
        print("SUKCES!")
        print(f"  Token:    {token}")
        print(f"  PAN:      {result.get('full_pan')}")
        print(f"  CVV:      {result.get('cvv')}")
        print(f"  Expiry:   {result.get('expiry_month'):02d}/{result.get('expiry_year')}")
        print(f"  Status:   ACTIVE (po lifecycle)")
        print(f"\nPlatnosc: http://localhost:8072/pos")
        return 0
    except Exception as exc:
        print(f"BLAD: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
