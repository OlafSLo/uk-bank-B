#!/usr/bin/env python3
"""
Test przelewu UK Bank B -> bank partnerski (Alice Bank / uk-bank-system).

Wymaga:
  1. UKPS (noradenshi/uk-payment-systems) na portach 8420/8421/8422
  2. UK Bank B na :8010
  3. (Opcjonalnie) uk-bank-system kolegi na :8001 + ukps-listener

    python scripts/test_peer_bank_e2e.py
"""

import json
import os
import sys

import requests

BANK_URL = os.getenv("BANK_URL", "http://localhost:8010")
PEER_SORT = os.getenv("PEER_BANK_UKPS_SORT_CODE", "60-00-00")
PEER_BIC = os.getenv("PEER_BANK_BIC", "SNDRUK22")
SENDER_SORT = "10-20-30"
SENDER_ACCOUNT = "11111111"
TARGET_ACCOUNT = os.getenv("PEER_BANK_TARGET_ACCOUNT", "12345678")
AMOUNT = float(os.getenv("TEST_PEER_AMOUNT", "30.00"))


def step(name, ok, detail=None):
    print(f"[{'OK' if ok else 'FAIL'}] {name}")
    if detail is not None:
        if isinstance(detail, (dict, list)):
            print(json.dumps(detail, indent=2, ensure_ascii=False)[:900])
        else:
            print(f"       {detail}")
    return ok


def main() -> int:
    print("=" * 60)
    print("  UK Bank B -> bank partnerski (przez UKPS)")
    print("=" * 60)
    all_ok = True

    try:
        r = requests.get(f"{BANK_URL}/api/peer-bank/status", timeout=10)
        data = r.json()
        all_ok &= step("Status banku partnerskiego", r.status_code == 200, data)
        if not data.get("ukps_reachable"):
            print("\nUKPS niedostepny — uruchom uk-payment-systems.")
            return 1
    except Exception as e:
        return 1 if not step("Status peer-bank", False, str(e)) else 0

    payload = {
        "from_sort_code": SENDER_SORT,
        "from_account": SENDER_ACCOUNT,
        "to_sort_code": PEER_SORT,
        "to_account": TARGET_ACCOUNT,
        "amount": AMOUNT,
    }

    r = requests.post(f"{BANK_URL}/api/transfer/fps", json=payload, timeout=20)
    ok = r.status_code == 200
    body = r.json() if "application/json" in r.headers.get("content-type", "") else r.text
    all_ok &= step(
        f"FPS -> {PEER_BIC} ({PEER_SORT})",
        ok,
        body,
    )

    print("\n" + ("Test OK — przelew wyslany przez UKPS." if all_ok else "Test nie przeszedl."))
    if all_ok:
        print(
            "U kolegi: sprawdz saldo w uk-bank-system (port 5173) jesli dziala ukps-listener."
        )
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
