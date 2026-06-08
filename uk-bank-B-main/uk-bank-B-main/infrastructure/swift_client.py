import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from xml.sax.saxutils import escape

import requests


class SwiftMiddlewareClient:
    """Klient sieci SWIFT (middleware Jkwasnyy) – OAuth2 token + pacs.008 ISO 20022.

    UK Bank B występuje jako bank o BIC `UKBKGB01XXX`.
    """

    PACS008_NS = "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"

    def __init__(
        self,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        bank_bic: str | None = None,
    ):
        self.client_id = client_id or os.getenv("SWIFT_CLIENT_ID", "test-client")
        self.client_secret = client_secret or os.getenv("SWIFT_CLIENT_SECRET", "test-secret")
        self.bank_bic = bank_bic or os.getenv("SWIFT_BANK_BIC", "UKBKGB01XXX")
        self.sender_iban = os.getenv("SWIFT_SENDER_IBAN", "GB29NWBK60161331926819")
        self.base_url = self._resolve_base_url(base_url)
        self._token: str | None = None
        self._token_banks: list[str] = []

    # ----- połączenie -----
    def _candidates(self) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for u in (
            self.base_url if hasattr(self, "base_url") else "",
            os.getenv("SWIFT_MIDDLEWARE_URL", ""),
            "http://swift-app:3000",
            "http://host.docker.internal:3000",
            "http://localhost:3000",
        ):
            u = (u or "").strip().rstrip("/")
            if u and u not in seen:
                seen.add(u)
                urls.append(u)
        return urls

    def _resolve_base_url(self, base_url: str | None) -> str:
        if base_url:
            return base_url.rstrip("/")
        env_url = os.getenv("SWIFT_MIDDLEWARE_URL", "").strip()
        if env_url:
            return env_url.rstrip("/")
        for candidate in (
            "http://swift-app:3000",
            "http://host.docker.internal:3000",
            "http://localhost:3000",
        ):
            try:
                r = requests.get(f"{candidate}/api/openapi.json", timeout=2)
                if r.status_code == 200:
                    return candidate
            except requests.RequestException:
                continue
        return "http://localhost:3000"

    def health_check(self) -> dict[str, Any]:
        last_error = "unreachable"
        for candidate in self._candidates():
            try:
                r = requests.get(f"{candidate}/api/openapi.json", timeout=4)
                if r.status_code == 200:
                    self.base_url = candidate
                    return {"ok": True, "url": candidate, "status_code": 200}
            except requests.RequestException as exc:
                last_error = str(exc)
        return {"ok": False, "url": self.base_url, "error": last_error}

    # ----- auth -----
    def get_token(self, force: bool = False) -> str:
        if self._token and not force:
            return self._token
        resp = requests.post(
            f"{self.base_url}/auth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=10,
        )
        if not resp.ok:
            raise RuntimeError(f"SWIFT auth failed: {resp.status_code} {resp.text}")
        data = resp.json()
        self._token = data.get("access_token")
        self._token_banks = data.get("banks", [])
        if not self._token:
            raise RuntimeError("SWIFT auth: brak access_token w odpowiedzi")
        return self._token

    # ----- budowa komunikatu pacs.008 -----
    def build_pacs008_xml(
        self,
        *,
        amount: str,
        currency: str,
        receiver_bic: str,
        receiver_account: str,
        receiver_name: str = "Beneficiary",
        sender_name: str = "UK Bank B Customer",
        charge_bearer: str = "SHAR",
        remittance_info: str = "",
        sender_account: str | None = None,
        uetr: str | None = None,
        message_id: str | None = None,
        instruction_id: str | None = None,
    ) -> tuple[str, dict[str, str]]:
        now = datetime.now(timezone.utc)
        uetr = uetr or str(uuid.uuid4())
        stamp = now.strftime("%Y%m%d-%H%M%S")
        message_id = message_id or f"MSG-{stamp}-{uetr[:8]}"
        instruction_id = instruction_id or f"INST-{stamp}-{uetr[:8]}"
        settlement_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        sender_account = sender_account or self.sender_iban

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="{self.PACS008_NS}">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>{escape(message_id)}</MsgId>
      <CreDtTm>{now.strftime("%Y-%m-%dT%H:%M:%SZ")}</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <SttlmInf>
        <SttlmMtd>INDA</SttlmMtd>
      </SttlmInf>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <InstrId>{escape(instruction_id)}</InstrId>
        <EndToEndId>NOTPROVIDED</EndToEndId>
        <UETR>{escape(uetr)}</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="{escape(currency)}">{escape(amount)}</IntrBkSttlmAmt>
      <IntrBkSttlmDt>{settlement_date}</IntrBkSttlmDt>
      <InstdAmt Ccy="{escape(currency)}">{escape(amount)}</InstdAmt>
      <ChrgBr>{escape(charge_bearer)}</ChrgBr>
      <InstgAgt>
        <FinInstnId>
          <BICFI>{escape(self.bank_bic)}</BICFI>
        </FinInstnId>
      </InstgAgt>
      <InstdAgt>
        <FinInstnId>
          <BICFI>{escape(receiver_bic)}</BICFI>
        </FinInstnId>
      </InstdAgt>
      <Dbtr>
        <Nm>{escape(sender_name)}</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id>
          <IBAN>{escape(sender_account)}</IBAN>
        </Id>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId>
          <BICFI>{escape(self.bank_bic)}</BICFI>
        </FinInstnId>
      </DbtrAgt>
      <CdtrAgt>
        <FinInstnId>
          <BICFI>{escape(receiver_bic)}</BICFI>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr>
        <Nm>{escape(receiver_name)}</Nm>
      </Cdtr>
      <CdtrAcct>
        <Id>
          <Othr>
            <Id>{escape(receiver_account)}</Id>
          </Othr>
        </Id>
      </CdtrAcct>
      <RmtInf>
        <Ustrd>{escape(remittance_info or "Payment")}</Ustrd>
      </RmtInf>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""
        meta = {
            "uetr": uetr,
            "message_id": message_id,
            "instruction_id": instruction_id,
            "settlement_date": settlement_date,
            "sender_bic": self.bank_bic,
            "sender_account": sender_account,
        }
        return xml, meta

    # ----- wysyłka -----
    def send_message(self, xml: str) -> tuple[int, dict[str, Any]]:
        token = self.get_token()
        resp = requests.post(
            f"{self.base_url}/swift/message",
            data=xml.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/xml",
            },
            timeout=15,
        )
        # token mógł wygasnąć
        if resp.status_code == 401:
            token = self.get_token(force=True)
            resp = requests.post(
                f"{self.base_url}/swift/message",
                data=xml.encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/xml",
                },
                timeout=15,
            )
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        return resp.status_code, body

    def send_now(self, uetr: str) -> tuple[int, dict[str, Any]]:
        """Wyzwala forward z inboxu middleware (operator dashboard: /api/send/{uetr})."""
        resp = requests.post(f"{self.base_url}/api/send/{uetr}", timeout=10)
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        return resp.status_code, body

    def cancel(self, uetr: str) -> tuple[int, dict[str, Any]]:
        resp = requests.post(f"{self.base_url}/api/cancel/{uetr}", timeout=10)
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        return resp.status_code, body
