#!/usr/bin/env python3
"""
Test E2E integracji UK Bank B <-> UK Payment Systems (CHAPS, FPS, BACS).

Wymaga:
  1. UKPS u kolegow: docker compose up -d (porty 8080/8081/8082)
  2. UK Bank B: docker compose up --build -d (port 8010)

    python scripts/test_ukps_e2e.py
"""

import json
import os
import sys

import requests

BANK_URL = os.getenv("BANK_URL", "http://localhost:8010")
CHAPS_URL = os.getenv("UKPS_CHAPS_URL", "http://localhost:8420")
FPS_URL = os.getenv("UKPS_FPS_URL", "http://localhost:8421")
BACS_URL = os.getenv("UKPS_BACS_URL", "http://localhost:8422")

SORT_CODE = "10-20-30"
ACCOUNT = "11111111"
TARGET_SORT = "20-00-00"
TARGET_ACCOUNT = "12345678"
AMOUNT = float(os.getenv("TEST_UKPS_AMOUNT", "25.00"))


def step(name, ok, detail=None):
    print(f"[{'OK' if ok else 'FAIL'}] {name}")
    if detail is not None:
        if isinstance(detail, (dict, list)):
            print(json.dumps(detail, indent=2, ensure_ascii=False)[:900])
        else:
            print(f"       {detail}")
    return ok


def get_balance():
    try:
        r = requests.get(f"{BANK_URL}/api/account/{SORT_CODE}/{ACCOUNT}", timeout=8)
        if r.status_code == 200:
            return float(r.json()["balance"])
    except Exception:
        pass
    return None


def main() -> int:
    print("=" * 60)
    print("  UK Bank B - test E2E UK Payment Systems (UKPS)")
    print("=" * 60)
    all_ok = True

    for name, url in (("CHAPS", CHAPS_URL), ("FPS", FPS_URL), ("BACS", BACS_URL)):
        try:
            r = requests.get(f"{url}/v1/healthz", timeout=5)
            all_ok &= step(f"UKPS {name} (/v1/healthz)", r.status_code == 200, url)
        except Exception as e:
            all_ok &= step(f"UKPS {name} (/v1/healthz)", False, str(e))

    if not all_ok:
        print("\nUruchom UKPS u kolegow:")
        print("  git clone https://github.com/noradenshi/uk-payment-systems")
        print("  cd uk-payment-systems && docker compose up -d")
        return 1

    try:
        r = requests.get(f"{BANK_URL}/api/ukps/status", timeout=10)
        data = r.json()
        registered = all(s.get("registered") for s in data.get("services", {}).values())
        all_ok &= step("Rejestracja banku w UKPS", r.status_code == 200 and registered, data)
        if not registered:
            print("\nZrestartuj bank (docker compose restart uk-bank-b) po starcie UKPS.")
            return 1
    except Exception as e:
        return 1 if not step("Status UKPS (bank)", False, str(e)) else 0

    bal_before = get_balance()
    step(f"Saldo konta {ACCOUNT} przed", bal_before is not None, f"GBP {bal_before}")

    payload = {
        "from_sort_code": SORT_CODE,
        "from_account": ACCOUNT,
        "to_sort_code": TARGET_SORT,
        "to_account": TARGET_ACCOUNT,
        "amount": AMOUNT,
    }

    for transfer_type, endpoint in (
        ("FPS", "/api/transfer/fps"),
        ("CHAPS", "/api/transfer/chaps"),
        ("BACS", "/api/transfer/bacs"),
    ):
        try:
            r = requests.post(f"{BANK_URL}{endpoint}", json=payload, timeout=15)
            ok = r.status_code == 200
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
            all_ok &= step(f"Przelew {transfer_type} -> Barclays ({TARGET_SORT})", ok, body)
        except Exception as e:
            all_ok &= step(f"Przelew {transfer_type}", False, str(e))

    bal_after = get_balance()
    if bal_before is not None and bal_after is not None:
        step("Saldo po testach", True, f"GBP {bal_after} (bylo {bal_before})")

    print("\n" + ("Wszystkie testy OK." if all_ok else "Niektore testy nie przeszly."))
    print(f"Status integracji: {BANK_URL}/integracje")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
