from fastapi import Depends, Header, Request

from app.auth.firebase import FirebaseAuthError
from app.db.models import User
from app.errors import ErrorCode, SurgeAPIError


async def get_current_user_optional(request: Request, authorization: str | None = Header(default=None)) -> User | None:
    """Real auth, but optional: an anonymous caller still gets full demo-mode access (unchanged
    behavior), while a caller carrying a valid Firebase ID token gets a real, persistent identity."""
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        raise SurgeAPIError(ErrorCode.AUTH_FAILED, "Authorization header must be 'Bearer <firebase-id-token>'", http_status=401)
    token = authorization.removeprefix("Bearer ").strip()
    services = request.app.state.services
    try:
        claims = await services.firebase.verify(token)
    except FirebaseAuthError as exc:
        raise SurgeAPIError(ErrorCode.AUTH_FAILED, str(exc), http_status=401) from exc
    return services.users.upsert_from_claims(claims)


async def require_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise SurgeAPIError(ErrorCode.AUTH_FAILED, "Sign in required for this endpoint", http_status=401)
    return user
