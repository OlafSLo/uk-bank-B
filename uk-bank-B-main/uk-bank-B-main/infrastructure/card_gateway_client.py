import hashlib
import hmac
import json
import os
import time
from typing import Any

import requests


class CardGatewayClient:
    """Klient REST Payment Gateway (moduł kart Filipa) z podpisem HMAC-SHA256."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        hmac_secret: str | None = None,
        admin_key: str | None = None,
    ):
        self.api_key = api_key or os.getenv("CARD_API_KEY", "bank-key-uk-b")
        self.hmac_secret = hmac_secret or os.getenv("CARD_HMAC_SECRET", "secret-uk-b-hmac")
        self.admin_key = admin_key or os.getenv("CARD_ADMIN_KEY", "admin-secret-key-2026")
        self.base_url = self._resolve_base_url(base_url)

    def _resolve_base_url(self, base_url: str | None) -> str:
        if base_url:
            return base_url.rstrip("/")
        env_url = os.getenv("CARD_GATEWAY_URL", "").strip()
        if env_url:
            return env_url.rstrip("/")
        # Kolejność prób: Docker internal → host → localhost
        for candidate in (
            "http://payment-gateway:8000",
            "http://host.docker.internal:8072",
            "http://localhost:8072",
        ):
            try:
                r = requests.get(f"{candidate}/docs", timeout=2)
                if r.status_code == 200:
                    return candidate
            except requests.RequestException:
                continue
        return "http://localhost:8072"

    def _sign(self, body: dict) -> tuple[str, str]:
        timestamp = str(int(time.time()))
        body_json = json.dumps(body, separators=(",", ":"), sort_keys=True)
        payload = timestamp + body_json
        signature = hmac.new(
            self.hmac_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature, timestamp

    def _signed_post(self, path: str, body: dict) -> dict:
        body_json = json.dumps(body, separators=(",", ":"), sort_keys=True)
        timestamp = str(int(time.time()))
        payload = timestamp + body_json
        signature = hmac.new(
            self.hmac_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        response = requests.post(
            f"{self.base_url}{path}",
            data=body_json,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
                "X-Signature": signature,
                "X-Timestamp": timestamp,
            },
            timeout=15,
        )
        if not response.ok:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise requests.HTTPError(f"{response.status_code}: {detail}", response=response)
        return response.json()

    def _api_post(self, path: str, body: dict, *, use_admin: bool = False) -> dict:
        headers = {"Content-Type": "application/json"}
        if use_admin:
            headers["X-Admin-Key"] = self.admin_key
        else:
            headers["X-API-Key"] = self.api_key
        response = requests.post(
            f"{self.base_url}{path}",
            json=body,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def _api_patch(self, path: str, body: dict, *, use_admin: bool = False) -> dict:
        headers = {"Content-Type": "application/json"}
        if use_admin:
            headers["X-Admin-Key"] = self.admin_key
        else:
            headers["X-API-Key"] = self.api_key
        response = requests.patch(
            f"{self.base_url}{path}",
            json=body,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def issue_card(
        self,
        user_id: str,
        account_id: str,
        card_type: str,
        initial_balance: float = 0,
    ) -> dict[str, Any]:
        body = {
            "user_id": user_id,
            "account_id": account_id,
            "card_type": card_type,
            "initial_balance": initial_balance,
        }
        return self._signed_post("/api/v1/cards/issue", body)

    def get_card_status(self, card_token: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/api/v1/cards/{card_token}",
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def activate_card(self, card_token: str, activated_by: str) -> dict[str, Any]:
        return self._api_post(
            f"/api/v1/cards/{card_token}/activate",
            {"activated_by": activated_by},
        )

    def update_status(self, card_token: str, status: str, reason: str = "") -> dict[str, Any]:
        return self._api_patch(
            f"/api/v1/cards/{card_token}/status",
            {"status": status, "reason": reason},
        )

    def advance_lifecycle(self, card_token: str, new_status: str) -> dict[str, Any]:
        return self._api_patch(
            f"/api/v1/cards/{card_token}/lifecycle",
            {"new_status": new_status, "changed_by": "uk-bank-b"},
            use_admin=True,
        )

    def topup(self, card_token: str, amount: float, currency: str = "GBP") -> dict[str, Any]:
        return self._api_post(
            f"/api/v1/cards/{card_token}/topup",
            {"amount": amount, "currency": currency},
        )

    def prepare_prepaid_for_payments(self, card_token: str) -> None:
        """Przechodzi cykl produkcji i aktywuje kartę PREPAID (wymagane przez moduł kart)."""
        for status in ("PRODUCING", "SHIPPED"):
            self.advance_lifecycle(card_token, status)
        self.activate_card(card_token, "uk-bank-b-auto")

    def health_check(self) -> dict[str, Any]:
        """Sprawdza dostępność Payment Gateway (z fallback URL)."""
        last_error = "unreachable"
        for candidate in self._gateway_candidates():
            try:
                response = requests.get(f"{candidate}/docs", timeout=4)
                if response.status_code == 200:
                    self.base_url = candidate
                    return {"ok": True, "url": candidate, "status_code": 200}
            except requests.RequestException as exc:
                last_error = str(exc)
        return {"ok": False, "url": self.base_url, "error": last_error}

    def _gateway_candidates(self) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for u in (
            self.base_url,
            os.getenv("CARD_GATEWAY_URL", ""),
            "http://payment-gateway:8000",
            "http://host.docker.internal:8072",
            "http://localhost:8072",
        ):
            u = (u or "").strip().rstrip("/")
            if u and u not in seen:
                seen.add(u)
                urls.append(u)
        return urls
