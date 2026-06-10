import os
import requests
import uuid
from decimal import Decimal

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
        "102030": "UKBKGB01XXX"
    }
    return mapping.get(sc_clean, "BARCGB2L") # Domyślnie Barclays

class UKPSClient:
    """Bazowy klient dla usług UK Payment Systems z auto-rejestracją."""
    def __init__(self, port: int, scheme: str):
        self.scheme = scheme
        self.port = port
        self.env_url = os.getenv(f"UKPS_{scheme.upper()}_URL", "")
        self.base_url = self._resolve_base_url()
        self.api_key = os.getenv(f"UKPS_{scheme.upper()}_API_KEY", "")
        self.registration_data = None

    def _resolve_base_url(self) -> str:
        if self.env_url:
            return self.env_url.rstrip("/")
        candidates = [
            f"http://{self.scheme}-app:{self.port}",
            f"http://host.docker.internal:{self.port}",
            f"http://172.17.0.1:{self.port}",
            f"http://172.18.0.1:{self.port}",
            f"http://localhost:{self.port}"
        ]
        for c in candidates:
            try:
                if requests.get(f"{c}/v1/healthz", timeout=1.0).status_code == 200:
                    return c
            except requests.RequestException:
                continue
        return f"http://host.docker.internal:{self.port}"

    def register(self, name: str, bic: str, sort_code: str, initial_balance: float, **kwargs):
        """Rejestruje bank w UKPS aby uzyskać i zapisać w pamięci klucz API."""
        self.registration_data = {
            "name": name,
            "bic": bic,
            "sort_code": format_sort_code(sort_code),
            "balance": initial_balance
        }
        self.registration_data.update(kwargs)
        self._try_register()

    def _try_register(self) -> str | None:
        """Próbuje zarejestrować bank. Zwraca None w przypadku sukcesu lub komunikat błędu."""
        if self.api_key or not self.registration_data:
            return None

        # Spróbuj ponownie znaleźć adres (symulator mógł wystartować później)
        self.base_url = self._resolve_base_url()

        url = f"{self.base_url}/v1/participants/register"
        try:
            resp = requests.post(url, json=self.registration_data, timeout=5)
            if resp.status_code in (200, 201):
                self.api_key = resp.json().get("api_key")
                print(f"[UKPS] ✅ Zarejestrowano w {self.scheme.upper()}. API Key: {self.api_key[:8]}...")
                return None
            elif resp.status_code == 409:
                msg = f"Bank już zarejestrowany w {self.scheme.upper()}, ale klucz API nie jest znany. Zresetuj bazę UKPS (`docker compose down -v`)."
                print(f"[UKPS] ⚠️ {msg}")
                return msg
            else:
                msg = f"Błąd rejestracji w {self.scheme.upper()}: {resp.status_code} {resp.text}"
                print(f"[UKPS] ❌ {msg}")
                return msg
        except Exception as e:
            msg = f"System {self.scheme.upper()} niedostępny pod adresem {self.base_url} ({e})"
            print(f"[UKPS] ❌ {msg}")
            return msg

    def _post(self, path: str, payload, is_json: bool = True) -> dict:
        registration_error = None
        if not self.api_key:
            registration_error = self._try_register()

        if not self.api_key:
            error_detail = registration_error or "Nieznany błąd rejestracji."
            raise ConnectionError(f"Brak klucza API dla {self.scheme.upper()}. Próba rejestracji nie powiodła się: {error_detail}")
            
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
            if getattr(e, 'response', None) is not None:
                try:
                    err_msg = e.response.json().get("error", err_msg)
                except:
                    err_msg = e.response.text or err_msg
            raise ConnectionError(f"Błąd systemu {self.scheme.upper()}: {err_msg}")

class ChapsClient(UKPSClient):
    def __init__(self):
        super().__init__(8080, "chaps")

    def send_payment(self, from_sort_code: str, from_account: str, to_sort_code: str, to_account: str, amount: Decimal) -> dict:
        payload = {
            "receiver_bic": get_bic_from_sort_code(to_sort_code),
            "amount": float(amount),
            "msg_id": f"CHAPS-{uuid.uuid4().hex[:8].upper()}",
            "receiver_sort_code": format_sort_code(to_sort_code)
        }
        return self._post("/v1/payments/chaps", payload)

class FpsClient(UKPSClient):
    def __init__(self):
        super().__init__(8081, "fps")

    def send_payment(self, from_sort_code: str, from_account: str, to_sort_code: str, to_account: str, amount: Decimal) -> dict:
        payload = {
            "receiver_bic": get_bic_from_sort_code(to_sort_code),
            "amount": float(amount),
            "msg_id": f"FPS-{uuid.uuid4().hex[:8].upper()}",
            "receiver_sort_code": format_sort_code(to_sort_code)
        }
        return self._post("/v1/payments/fps", payload)

class BacsClient(UKPSClient):
    def __init__(self):
        super().__init__(8082, "bacs")

    def submit_batch(self, from_sort_code: str, from_account: str, to_sort_code: str, to_account: str, amount: Decimal) -> dict:
        pence = int(amount * 100)
        target_sort = format_sort_code(to_sort_code).replace("-", "")
        if len(target_sort) != 6:
            target_sort = "300000"
        # Format Standard 18 (mock file do symulatora) - dopełnione do 80 znaków
        std18 = f"1{{SUCODE01  }}0000001UK BANK B           {target_sort}10000{pence}".ljust(80)
        return self._post("/v1/payments/bacs/submit", std18, is_json=False)