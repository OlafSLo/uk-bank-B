"""Klient HTTP dla systemu KLIK-payments (C2B + P2P).

Repozytorium: https://github.com/MarshallBjorn/KLIK-payments
"""
import os
import uuid

import requests


def klik_config() -> dict:
    base = os.getenv("KLIK_BASE_URL", "http://host.docker.internal:8102/api/v1").rstrip("/")
    return {
        "base_url": base,
        "health_url": os.getenv("KLIK_HEALTH_URL", base.replace("/api/v1", "") + "/healthz/"),
        "api_key": os.getenv("KLIK_BANK_API_KEY", ""),
        "zone": os.getenv("KLIK_ZONE", "UK"),
        "webhook_url": os.getenv(
            "KLIK_WEBHOOK_URL",
            "http://host.docker.internal:8010/api/klik/webhook",
        ),
        "agent_url": os.getenv("KLIK_AGENT_URL", "http://localhost:8175"),
        "repo": "https://github.com/MarshallBjorn/KLIK-payments",
    }


class KlikClient:
    def __init__(self):
        self.config = klik_config()

    def _headers(self, idempotency: bool = True) -> dict:
        h = {
            "X-KLIK-Bank-Api-Key": self.config["api_key"],
            "Content-Type": "application/json",
        }
        if idempotency:
            h["Idempotency-Key"] = str(uuid.uuid4())
        return h

    def health_check(self) -> dict:
        cfg = self.config
        public = cfg["health_url"].replace("host.docker.internal", "localhost")
        result = {
            "ok": False,
            "base_url": cfg["base_url"].replace("host.docker.internal", "localhost"),
            "zone": cfg["zone"],
            "api_key_set": bool(cfg["api_key"]),
            "webhook_url": cfg["webhook_url"].replace("host.docker.internal", "localhost"),
            "agent_url": cfg["agent_url"],
            "repo": cfg["repo"],
        }
        if not cfg["api_key"]:
            result["hint"] = (
                "Ustaw KLIK_BANK_API_KEY (klucz z Django Admin KLIK → Banks) "
                "i webhook banku na http://host.docker.internal:8010/api/klik/webhook"
            )
            return result
        try:
            resp = requests.get(cfg["health_url"], timeout=4)
            result["ok"] = resp.status_code == 200
            result["status"] = resp.status_code
        except requests.RequestException as exc:
            result["error"] = str(exc)
            result["hint"] = (
                "Uruchom KLIK: docker compose -f docker-compose.yml -f docker-compose-dev.yml up -d "
                "(port API 8102 — patrz scripts/setup-klik.ps1)"
            )
        return result

    def generate_code(self, user_id: str) -> dict:
        resp = requests.post(
            f"{self.config['base_url']}/codes/generate",
            json={"user_id": user_id, "zone": self.config["zone"]},
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def confirm_payment(self, transaction_id: str, decision: str, reject_reason: str | None = None) -> dict:
        payload = {"transaction_id": transaction_id, "status": decision}
        if decision == "REJECTED":
            payload["reject_reason"] = reject_reason or "USER_DECLINED"
        resp = requests.post(
            f"{self.config['base_url']}/payments/confirm",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code >= 400:
            raise requests.HTTPError(f"{resp.status_code}: {resp.text}", response=resp)
        return resp.json()

    def register_alias(self, phone: str, iban: str) -> dict:
        resp = requests.post(
            f"{self.config['base_url']}/aliases/register",
            json={"phone": phone, "iban": iban, "zone": self.config["zone"]},
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code >= 400:
            raise requests.HTTPError(f"{resp.status_code}: {resp.text}", response=resp)
        return resp.json()

    def lookup_alias(self, phone: str) -> dict:
        from urllib.parse import quote

        encoded = quote(phone, safe="")
        resp = requests.get(
            f"{self.config['base_url']}/aliases/lookup/{encoded}",
            headers={"X-KLIK-Bank-Api-Key": self.config["api_key"]},
            timeout=10,
        )
        if resp.status_code >= 400:
            raise requests.HTTPError(f"{resp.status_code}: {resp.text}", response=resp)
        return resp.json()

    def delete_alias(self, phone: str) -> dict:
        from urllib.parse import quote

        encoded = quote(phone, safe="")
        resp = requests.delete(
            f"{self.config['base_url']}/aliases/{encoded}",
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code >= 400:
            raise requests.HTTPError(f"{resp.status_code}: {resp.text}", response=resp)
        if resp.content:
            return resp.json()
        return {}
