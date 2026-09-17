import base64
import hashlib
import logging
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

from app.db.models import ANONYMOUS_USER_ID, ConnectorCredential
from app.db.session import Database

logger = logging.getLogger("surge.credentials")


class CredentialStore:
    """Server-side, encrypted provider tokens. Tokens never leave this module in API responses."""

    def __init__(self, db: Database, secret_key: str):
        self.db = db
        if secret_key:
            key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())
            self.persistent = True
        else:
            key = Fernet.generate_key()
            self.persistent = False
            logger.warning(
                "SURGE_SECRET_KEY not set: using an ephemeral key; stored OAuth tokens will not survive restart"
            )
        self._fernet = Fernet(key)

    def _enc(self, value: str | None) -> str | None:
        return self._fernet.encrypt(value.encode()).decode() if value else None

    def _dec(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            return None

    def save(
        self,
        app: str,
        access_token: str,
        *,
        user_id: str = ANONYMOUS_USER_ID,
        refresh_token: str | None = None,
        account_label: str | None = None,
        scopes: str | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        with self.db.session() as s:
            row = s.get(ConnectorCredential, (user_id, app)) or ConnectorCredential(
                user_id=user_id, app=app, encrypted_access_token=""
            )
            row.encrypted_access_token = self._enc(access_token)
            if refresh_token:
                row.encrypted_refresh_token = self._enc(refresh_token)
            row.account_label = account_label
            row.scopes = scopes
            row.expires_at = expires_at
            s.merge(row)

    def get(self, app: str, user_id: str = ANONYMOUS_USER_ID) -> dict | None:
        with self.db.session() as s:
            row = s.get(ConnectorCredential, (user_id, app))
            if row is None:
                return None
            access = self._dec(row.encrypted_access_token)
            if access is None:
                return None
            return {
                "access_token": access,
                "refresh_token": self._dec(row.encrypted_refresh_token),
                "account_label": row.account_label,
                "scopes": row.scopes,
                "expires_at": row.expires_at,
            }

    def delete(self, app: str, user_id: str = ANONYMOUS_USER_ID) -> bool:
        with self.db.session() as s:
            row = s.get(ConnectorCredential, (user_id, app))
            if row is None:
                return False
            s.delete(row)
            return True
