#!/usr/bin/env python3
"""
Test E2E integracji SWIFT: UK Bank B -> middleware -> bank odbiorcy,
oraz odbieranie przelewu (/receive) z uznaniem konta.

Wymaga: uruchomionego UK Bank B (:8000) i middleware SWIFT (:3000).

    python scripts/test_swift_e2e.py
"""

import json
import os
import sys

import requests

BANK_URL = os.getenv("BANK_URL", "http://localhost:8010")
SWIFT_URL = os.getenv("SWIFT_MIDDLEWARE_URL", "http://localhost:3000")
SORT_CODE = "102030"
ACCOUNT = "11111111"


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
    print("  UK Bank B - test E2E SWIFT (wyslij + odbierz)")
    print("=" * 60)
    all_ok = True

    # 1. Status integracji
    try:
        r = requests.get(f"{BANK_URL}/api/swift/status", timeout=10)
        data = r.json()
        ok = r.status_code == 200 and data.get("swift_middleware", {}).get("ok")
        all_ok &= step("Status integracji (bank -> SWIFT)", ok, data)
        if not ok:
            print("\nUruchom middleware SWIFT (port 3000) i sprobuj ponownie.")
            return 1
    except Exception as e:
        return 1 if not step("Status integracji", False, str(e)) else 0

    # 2. Wyslanie przelewu miedzynarodowego (network mode)
    bal_before = get_balance()
    step(f"Saldo konta {ACCOUNT} przed", bal_before is not None, f"GBP {bal_before}")

    payload = {
        "from_sort_code": SORT_CODE,
        "from_account": ACCOUNT,
        "to_sort_code": "PLBKPL01XXX",
        "receiver_bic": "PLBKPL01XXX",
        "to_account": "PL61109010140000071219812874",
        "receiver_name": "Polska Spolka Importowa",
        "amount": "100.00",
        "to_currency": "EUR",
        "charge_bearer": "SHAR",
        "remittance_info": "E2E test",
        "use_network": True,
        "auto_send": True,
    }
    try:
        r = requests.post(f"{BANK_URL}/api/transfer/swift", json=payload, timeout=20)
        data = r.json()
        ok = r.status_code == 200 and bool(data.get("uetr"))
        all_ok &= step("Wyslanie SWIFT (pacs.008 -> middleware)", ok, data)
        uetr = data.get("uetr")
    except Exception as e:
        all_ok &= step("Wyslanie SWIFT", False, str(e))
        uetr = None

    bal_after = get_balance()
    debited = bal_before is not None and bal_after is not None and bal_after < bal_before
    all_ok &= step("Obciazenie konta nadawcy", debited,
                   {"before": bal_before, "after": bal_after})

    # 3. Odbieranie: symulacja forwardu z middleware do /receive
    incoming_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">'
        '<FIToFICstmrCdtTrf><GrpHdr><MsgId>MSG-IN-001</MsgId></GrpHdr>'
        '<CdtTrfTxInf><PmtId><UETR>11111111-2222-3333-4444-555555555555</UETR></PmtId>'
        '<IntrBkSttlmAmt Ccy="GBP">250.00</IntrBkSttlmAmt>'
        '<InstdAmt Ccy="GBP">250.00</InstdAmt></CdtTrfTxInf>'
        '</FIToFICstmrCdtTrf></Document>'
    )
    headers = {
        "Content-Type": "application/xml",
        "X-SWIFT-UETR": "11111111-2222-3333-4444-555555555555",
        "X-SWIFT-Message-Id": "MSG-IN-001",
        "X-SWIFT-Currency": "GBP",
        "X-SWIFT-Receiver-Account": "GB29NWBK60161331926819",
        "X-SWIFT-Sender-Account": "PL61109010140000071219812874",
    }
    bal_before_in = get_balance()
    try:
        r = requests.post(f"{BANK_URL}/receive", data=incoming_xml, headers=headers, timeout=10)
        data = r.json()
        ok = r.status_code == 202 and data.get("status") == "accepted"
        all_ok &= step("Odbieranie /receive (uznanie konta)", ok, data)
    except Exception as e:
        all_ok &= step("Odbieranie /receive", False, str(e))

    bal_after_in = get_balance()
    credited = (bal_before_in is not None and bal_after_in is not None
                and bal_after_in > bal_before_in)
    all_ok &= step("Uznanie konta odbiorcy (+GBP)", credited,
                   {"before": bal_before_in, "after": bal_after_in})

    print("-" * 60)
    if all_ok:
        print("Wynik E2E SWIFT: SUKCES")
        print(f"  Formularz:  {BANK_URL}/transfer/swift")
        print(f"  Panel SWIFT:{SWIFT_URL}")
        return 0
    print("Wynik E2E SWIFT: czesc krokow nie przeszla (zobacz wyzej)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
