#!/usr/bin/env python3
"""Szybki test integracji UK Bank B ↔ moduł kart płatniczych."""

import json
import os
import sys
import time

import requests

BANK_URL = os.getenv("BANK_URL", "http://localhost:8000")
GATEWAY_URL = os.getenv("CARD_GATEWAY_URL", "http://localhost:8072")


def check(name: str, ok: bool, detail=None):
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")


def main() -> int:
    print("=" * 55)
    print("  UK Bank B – test integracji z modułem kart")
    print("=" * 55)

    all_ok = True

    for attempt in range(1, 6):
        try:
            r = requests.get(f"{BANK_URL}/api/info", timeout=5)
            if r.status_code == 200:
                break
        except Exception:
            if attempt == 5:
                r = None
            time.sleep(2)

    try:
        ok = r is not None and r.status_code == 200
        all_ok &= ok
        check("UK Bank B (/api/info)", ok, r.json() if ok else r.text)
    except Exception as e:
        all_ok = False
        check("UK Bank B (/api/info)", False, str(e))

    try:
        r = requests.get(f"{GATEWAY_URL}/docs", timeout=5)
        ok = r.status_code == 200
        all_ok &= ok
        check("Payment Gateway (/docs)", ok, GATEWAY_URL)
    except Exception as e:
        all_ok = False
        check("Payment Gateway (/docs)", False, str(e))

    try:
        r = requests.get(f"{BANK_URL}/api/integration/status", timeout=8)
        ok = r.status_code == 200
        data = r.json() if ok else {}
        gw_ok = data.get("card_gateway", {}).get("ok", False)
        all_ok &= ok and gw_ok
        check("Status integracji (bank -> gateway)", ok and gw_ok, json.dumps(data, indent=2)[:300])
    except Exception as e:
        all_ok = False
        check("Status integracji", False, str(e))

    print("-" * 55)
    if all_ok:
        print("Wynik: GOTOWE do prezentacji [OK]")
        print(f"  Demo:     {BANK_URL}/demo-karty")
        print(f"  POS:      {GATEWAY_URL}/pos")
        print(f"  Swagger:  {GATEWAY_URL}/docs")
        return 0
    print("Wynik: NIE GOTOWE [FAIL]")
    print("Uruchom: .\\scripts\\start-demo.ps1")
    return 1


if __name__ == "__main__":
    sys.exit(main())
