#!/usr/bin/env python3
"""Test integracji UK Bank B ↔ KLIK-payments (C2B + status).

Wymaga:
  - UK Bank B na :8010 z ustawionym KLIK_BANK_API_KEY
  - KLIK na :8102 (docker compose + override portu)
  - Webhook banku w Django Admin KLIK

Użycie:
  python scripts/test_klik_e2e.py
"""
import os
import sys

import requests

BANK_URL = os.getenv("BANK_URL", "http://localhost:8010")
KLIK_HEALTH = os.getenv("KLIK_HEALTH_URL", "http://localhost:8102/healthz/")
SORT = "10-20-30"
ACCOUNT = "11111111"


def main() -> int:
    print("=== Test KLIK integracji UK Bank B ===\n")

    # 1. Status banku
    try:
        r = requests.get(f"{BANK_URL}/api/klik/status", timeout=5)
        r.raise_for_status()
        data = r.json()
        print("UK Bank B /api/klik/status:", "OK" if data.get("klik") else data)
        klik = data.get("klik", {})
        if not klik.get("api_key_set"):
            print("  UWAGA: KLIK_BANK_API_KEY nie ustawiony w kontenerze uk-bank-b")
            return 1
        if not klik.get("ok"):
            print("  KLIK niedostępny:", klik.get("error") or klik.get("hint"))
            return 1
    except Exception as exc:
        print(f"Błąd statusu banku: {exc}")
        return 1

    # 2. Health KLIK
    try:
        hr = requests.get(KLIK_HEALTH, timeout=5)
        print(f"KLIK healthz: HTTP {hr.status_code}")
        if hr.status_code != 200:
            return 1
    except Exception as exc:
        print(f"KLIK healthz niedostępny: {exc}")
        return 1

    # 3. Webhook ping
    try:
        pr = requests.post(
            f"{BANK_URL}/api/klik/webhook/ping",
            json={"timestamp": "2026-01-01T00:00:00Z", "nonce": "test"},
            timeout=5,
        )
        pr.raise_for_status()
        print("Webhook ping:", pr.json())
    except Exception as exc:
        print(f"Webhook ping failed: {exc}")
        return 1

    # 4. Generuj kod C2B
    try:
        gr = requests.post(
            f"{BANK_URL}/api/klik/codes/generate",
            json={"sort_code": SORT, "account_number": ACCOUNT},
            timeout=10,
        )
        gr.raise_for_status()
        code_data = gr.json()
        print(f"Wygenerowano kod KLIK: {code_data.get('code')} (user_id={code_data.get('user_id')})")
        print("\nNastępny krok manualny:")
        print(f"  1. Otwórz terminal agenta: http://localhost:8175")
        print(f"     Klucz agenta: klik_dev_agent_uk_school_demo | Strefa: UK")
        print(f"  2. Wpisz kod {code_data.get('code')} i kwotę")
        print(f"  3. W UK Bank B: http://localhost:8010/klik -> Akceptuj PIN 1234")
    except Exception as exc:
        print(f"Generowanie kodu failed: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(exc.response.text[:500])
        return 1

    print("\n=== Test podstawowy OK ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
