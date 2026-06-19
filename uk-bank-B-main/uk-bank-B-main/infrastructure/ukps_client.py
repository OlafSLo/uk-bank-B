import json
import os
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import requests

_KEYS_FILE = Path(os.getenv("UKPS_API_KEYS_FILE", "data/ukps_api_keys.json"))

# Porty hosta: domyślne UKPS (808x) oraz mapowanie z docker compose kolegów (842x)
_SCHEME_HOST_PORTS: dict[str, tuple[int, ...]] = {
    "chaps": (8080, 8420),
    "fps": (8081, 8421),
    "bacs": (8082, 8422),
}


def format_sort_code(sc: str) -> str:
    """Zwraca format XX-XX-XX wymagany przez UKPS."""
    sc = sc.replace("-", "").replace(" ", "").strip()
    if len(sc) == 6:
        return f"{sc[:2]}-{sc[2:4]}-{sc[4:]}"
    return sc


def get_bic_from_sort_code(sc: str) -> str:
    """Mapuje testowe Sort Code'y na BIC banków w środowisku UKPS."""
    sc_clean = sc.replace("-", "").replace(" ", "").strip()
    mapping = {
        "200000": "BARCGB2L",
        "400000": "HSBCGB44",
        "300000": "LLOYGB21",
        "600000": "SNDRUK22",
        "102030": "UKBKGB01XXX",
    }
    return mapping.get(sc_clean, "BARCGB2L")


def _load_persisted_keys() -> dict[str, str]:
    try:
        if _KEYS_FILE.is_file():
            data = json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: str(v) for k, v in data.items() if v}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return {}


def _persist_api_key(scheme: str, api_key: str) -> None:
    if not api_key:
        return
    keys = _load_persisted_keys()
    keys[scheme.upper()] = api_key
    _KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _KEYS_FILE.write_text(json.dumps(keys, indent=2), encoding="utf-8")
    print(f"[UKPS] Klucz API {scheme.upper()} zapisany w {_KEYS_FILE}")


def _rpad(value: str, width: int) -> str:
    return (value + " " * width)[:width]


def _lpad(value: str | int, width: int) -> str:
    text = str(value)
    if len(text) >= width:
        return text[:width]
    return (" " * (width - len(text))) + text


def build_bacs_std18_file(
    to_sort_code: str,
    to_account_number: str,
    amount: Decimal,
    su_code: str = "123456",
) -> str:
    """Buduje plik Standard 18 (rekordy 1, 4, 5, 9) zgodny z parserem UKPS."""
    dest_sort = format_sort_code(to_sort_code).replace("-", "")
    dest_account = to_account_number.replace(" ", "").strip()[:8]
    dest_account = dest_account.ljust(8, "0") if dest_account else "00000000"
    pence = int(amount * 100)
    date = datetime.now().strftime("%y%m%d")
    vol_no = "1"

    rec1 = (
        "1"
        + _lpad(vol_no, 7)
        + _rpad(dest_sort, 9)
        + _rpad(dest_account, 9)
        + (" " * 29)
        + _lpad(pence, 11)
        + _lpad(1, 7)
        + _rpad(date, 6)
        + " "
    )
    rec4 = (
        "4"
        + _lpad(vol_no, 7)
        + _rpad(dest_sort, 9)
        + _rpad(dest_account, 9)
        + _lpad(pence, 11)
        + _rpad("UK BANK B", 15)
        + _rpad("TRANSFER", 14)
        + _rpad(su_code, 13)
        + " "
    )
    rec5 = "5" + _lpad(vol_no, 7) + (" " * 40) + _lpad(1, 8) + (" " * 24)
    rec9 = (
        "9"
        + _lpad(vol_no, 7)
        + (" " * 12)
        + _lpad(pence, 11)
        + _lpad(1, 9)
        + _lpad(10, 14)
        + (" " * 26)
    )
    for line in (rec1, rec4, rec5, rec9):
        if len(line) != 80:
            raise ValueError(f"Nieprawidłowa długość rekordu BACS ({len(line)}): {line!r}")
    return "\n".join((rec1, rec4, rec5, rec9)) + "\n"


class UKPSClient:
    """Bazowy klient dla usług UK Payment Systems z auto-rejestracją."""

    def __init__(self, port: int, scheme: str):
        self.scheme = scheme
        self.port = port
        self.env_url = os.getenv(f"UKPS_{scheme.upper()}_URL", "")
        self.base_url = self._resolve_base_url()
        self.api_key = os.getenv(f"UKPS_{scheme.upper()}_API_KEY", "").strip()
        if not self.api_key:
            self.api_key = _load_persisted_keys().get(scheme.upper(), "")
        self.registration_data = None

    def _resolve_base_url(self, force: bool = False) -> str:
        if self.env_url and not force:
            return self.env_url.rstrip("/")
        ports = _SCHEME_HOST_PORTS.get(self.scheme, (self.port,))
        hosts = [
            f"http://{self.scheme}-app",
            "http://host.docker.internal",
            "http://172.17.0.1",
            "http://172.18.0.1",
            "http://localhost",
        ]
        for port in ports:
            for host in hosts:
                candidate = f"{host}:{port}"
                try:
                    if requests.get(f"{candidate}/v1/healthz", timeout=1.5).status_code == 200:
                        return candidate
                except requests.RequestException:
                    continue
        fallback_port = ports[-1]
        return f"http://host.docker.internal:{fallback_port}"

    def register(self, name: str, bic: str, sort_code: str, initial_balance: float, **kwargs):
        """Rejestruje bank w UKPS aby uzyskać i zapisać klucz API."""
        if self.api_key:
            return
        self.registration_data = {
            "name": name,
            "bic": bic,
            "sort_code": format_sort_code(sort_code),
            "balance": initial_balance,
        }
        self.registration_data.update(kwargs)
        self._try_register()

    def _try_register(self) -> str | None:
        """Próbuje zarejestrować bank. Zwraca None w przypadku sukcesu lub komunikat błędu."""
        if self.api_key or not self.registration_data:
            return None

        self.base_url = self._resolve_base_url()
        url = f"{self.base_url}/v1/participants/register"
        try:
            resp = requests.post(url, json=self.registration_data, timeout=5)
            if resp.status_code in (200, 201):
                self.api_key = resp.json().get("api_key", "")
                if self.api_key:
                    _persist_api_key(self.scheme, self.api_key)
                print(f"[UKPS] Zarejestrowano w {self.scheme.upper()}. API Key: {self.api_key[:8]}...")
                return None
            if resp.status_code == 409:
                msg = (
                    f"Bank już zarejestrowany w {self.scheme.upper()}, ale klucz API nie jest znany. "
                    f"Ustaw UKPS_{self.scheme.upper()}_API_KEY w .env lub usuń dane UKPS "
                    f"(docker compose down -v w repozytorium uk-payment-systems)."
                )
                print(f"[UKPS] {msg}")
                return msg
            msg = f"Błąd rejestracji w {self.scheme.upper()}: {resp.status_code} {resp.text}"
            print(f"[UKPS] {msg}")
            return msg
        except Exception as e:
            msg = f"System {self.scheme.upper()} niedostępny pod adresem {self.base_url} ({e})"
            print(f"[UKPS] {msg}")
            return msg

    def health_check(self) -> dict:
        """Sprawdza dostępność usługi UKPS i status rejestracji banku."""
        try:
            resp = requests.get(f"{self.base_url}/v1/healthz", timeout=3)
            ok = resp.status_code == 200
        except requests.RequestException as exc:
            self.base_url = self._resolve_base_url(force=True)
            try:
                resp = requests.get(f"{self.base_url}/v1/healthz", timeout=3)
                ok = resp.status_code == 200
            except requests.RequestException as retry_exc:
                return {
                    "ok": False,
                    "scheme": self.scheme.upper(),
                    "url": self.base_url,
                    "registered": bool(self.api_key),
                    "error": str(retry_exc),
                    "hint": "Uruchom UKPS: docker compose up -d w repo uk-payment-systems",
                }
            return {
                "ok": ok,
                "scheme": self.scheme.upper(),
                "url": self.base_url,
                "registered": bool(self.api_key),
            }
        return {
            "ok": ok,
            "scheme": self.scheme.upper(),
            "url": self.base_url,
            "registered": bool(self.api_key),
        }

    def _post(self, path: str, payload, is_json: bool = True) -> dict:
        registration_error = None
        if not self.api_key:
            registration_error = self._try_register()

        if not self.api_key:
            error_detail = registration_error or "Nieznany błąd rejestracji."
            raise ConnectionError(
                f"Brak klucza API dla {self.scheme.upper()}. "
                f"Próba rejestracji nie powiodła się: {error_detail}"
            )

        headers = {"Authorization": f"Bearer {self.api_key}"}
        if is_json:
            headers["Content-Type"] = "application/json"
        else:
            headers["Content-Type"] = "text/plain"

        url = f"{self.base_url}{path}"
        try:
            if is_json:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            else:
                response = requests.post(url, data=payload, headers=headers, timeout=10)

            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                return {"message": response.text}
        except requests.exceptions.RequestException as e:
            err_msg = str(e)
            if getattr(e, "response", None) is not None:
                try:
                    err_msg = e.response.json().get("error", err_msg)
                except Exception:
                    err_msg = e.response.text or err_msg
            raise ConnectionError(f"Błąd systemu {self.scheme.upper()}: {err_msg}")


class ChapsClient(UKPSClient):
    def __init__(self):
        super().__init__(8080, "chaps")

    def send_payment(
        self,
        from_sort_code: str,
        from_account: str,
        to_sort_code: str,
        to_account: str,
        amount: Decimal,
    ) -> dict:
        payload = {
            "receiver_bic": get_bic_from_sort_code(to_sort_code),
            "amount": float(amount),
            "msg_id": f"CHAPS-{uuid.uuid4().hex[:8].upper()}",
            "receiver_sort_code": format_sort_code(to_sort_code),
        }
        return self._post("/v1/payments/chaps", payload)


class FpsClient(UKPSClient):
    def __init__(self):
        super().__init__(8081, "fps")

    def send_payment(
        self,
        from_sort_code: str,
        from_account: str,
        to_sort_code: str,
        to_account: str,
        amount: Decimal,
    ) -> dict:
        payload = {
            "receiver_bic": get_bic_from_sort_code(to_sort_code),
            "amount": float(amount),
            "msg_id": f"FPS-{uuid.uuid4().hex[:8].upper()}",
            "receiver_sort_code": format_sort_code(to_sort_code),
        }
        return self._post("/v1/payments/fps", payload)


class BacsClient(UKPSClient):
    def __init__(self):
        super().__init__(8082, "bacs")
        self.su_code = os.getenv("UKPS_BACS_SU_CODE", "123456")

    def submit_batch(
        self,
        from_sort_code: str,
        from_account: str,
        to_sort_code: str,
        to_account: str,
        amount: Decimal,
    ) -> dict:
        std18 = build_bacs_std18_file(to_sort_code, to_account, amount, self.su_code)
        return self._post("/v1/payments/bacs/submit", std18, is_json=False)
