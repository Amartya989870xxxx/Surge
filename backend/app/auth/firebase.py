"""Verifies Firebase Authentication ID tokens without the Firebase Admin SDK.

A Firebase ID token is a standard RS256 JWT signed by Google's `securetoken` service. We fetch
Google's public JWKS ourselves (over the app's own async httpx client, so verification never blocks
the event loop), cache keys by kid, and check signature plus the standard claims (aud, iss, exp) —
this is exactly what the Admin SDK does internally, without the extra dependency weight."""

import base64
import time

import httpx
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"


class FirebaseAuthError(Exception):
    pass


def _b64url_to_int(segment: str) -> int:
    padded = segment + "=" * (-len(segment) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(padded), "big")


class FirebaseVerifier:
    def __init__(self, project_id: str, http: httpx.AsyncClient, *, jwks_url: str = JWKS_URL, cache_ttl_s: float = 3600):
        self.project_id = project_id
        self.http = http
        self._jwks_url = jwks_url
        self._cache_ttl_s = cache_ttl_s
        self._keys: dict[str, object] = {}
        self._fetched_at = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.project_id)

    async def _get_key(self, kid: str):
        now = time.monotonic()
        if kid not in self._keys or now - self._fetched_at > self._cache_ttl_s:
            try:
                resp = await self.http.get(self._jwks_url, timeout=10)
                resp.raise_for_status()
                jwks = resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise FirebaseAuthError(f"Could not fetch Google's signing keys: {exc}") from exc
            self._keys = {
                jwk["kid"]: RSAPublicNumbers(_b64url_to_int(jwk["e"]), _b64url_to_int(jwk["n"])).public_key(default_backend())
                for jwk in jwks.get("keys", [])
                if jwk.get("kty") == "RSA"
            }
            self._fetched_at = now
        key = self._keys.get(kid)
        if key is None:
            raise FirebaseAuthError("Token was signed with an unrecognized key (unknown kid)")
        return key

    async def verify(self, token: str) -> dict:
        if not self.configured:
            raise FirebaseAuthError("Firebase project id is not configured on the server (SURGE_FIREBASE_PROJECT_ID)")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise FirebaseAuthError(f"Malformed token: {exc}") from exc
        kid = header.get("kid")
        if not kid:
            raise FirebaseAuthError("Token header is missing 'kid'")
        key = await self._get_key(kid)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.project_id,
                issuer=f"https://securetoken.google.com/{self.project_id}",
                options={"require": ["exp", "iat", "sub", "auth_time"]},
            )
        except jwt.PyJWTError as exc:
            raise FirebaseAuthError(f"Invalid Firebase ID token: {exc}") from exc
        if not claims.get("sub"):
            raise FirebaseAuthError("Token has no subject")
        return claims
