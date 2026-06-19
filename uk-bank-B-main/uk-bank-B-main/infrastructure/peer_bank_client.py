"""Klient statusu banku partnerskiego (p-poweska/uk-bank-system).

Przelewy między bankami idą przez UKPS (CHAPS/FPS/BACS), nie bezpośrednim API
Django. Ten moduł sprawdza dostępność API kolegi i udostępnia dane routingu.
"""
import os

import requests


def peer_bank_config() -> dict:
    return {
        "name": os.getenv("PEER_BANK_NAME", "Alice Bank (UK Bank A)"),
        "bic": os.getenv("PEER_BANK_BIC", "SNDRUK22"),
        "ukps_sort_code": os.getenv("PEER_BANK_UKPS_SORT_CODE", "60-00-00"),
        "customer_sort_code": os.getenv("PEER_BANK_CUSTOMER_SORT_CODE", "10-20-30"),
        "api_url": os.getenv("PEER_BANK_API_URL", "http://host.docker.internal:8001").rstrip("/"),
        "frontend_url": os.getenv("PEER_BANK_FRONTEND_URL", "http://host.docker.internal:5173").rstrip("/"),
        "repo": "https://github.com/p-poweska/uk-bank-system",
        "routing": "UKPS",
    }


class PeerBankClient:
    def __init__(self):
        self.config = peer_bank_config()

    def health_check(self) -> dict:
        api = self.config["api_url"]
        public = api.replace("host.docker.internal", "localhost")
        result = {
            "ok": False,
            "name": self.config["name"],
            "bic": self.config["bic"],
            "ukps_sort_code": self.config["ukps_sort_code"],
            "api_url": public,
            "frontend_url": self.config["frontend_url"].replace("host.docker.internal", "localhost"),
            "routing": self.config["routing"],
        }
        for path in ("/api/docs/", "/api/schema/"):
            try:
                resp = requests.get(f"{api}{path}", timeout=4)
                if resp.status_code == 200:
                    result["ok"] = True
                    result["docs_path"] = path
                    return result
            except requests.RequestException as exc:
                result["error"] = str(exc)
        result["hint"] = (
            "Uruchom uk-bank-system kolegi: docker compose up -d (API na porcie 8001). "
            "Przelew i tak może przejść przez UKPS, jeśli ukps-listener u nich działa."
        )
        return result
