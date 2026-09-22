from app.db.models import User
from app.db.session import Database


class UserStore:
    """Async methods (a*) are the migrated path and are used on every authenticated request via
    app/auth/deps.py - that makes them the highest-traffic call site in the whole app, so they
    were converted first. The sync methods remain for callers not yet migrated."""

    def __init__(self, db: Database):
        self.db = db

    # --- async (migrated) ---

    async def aupsert_from_claims(self, claims: dict) -> User:
        uid = claims["sub"]
        async with self.db.async_session() as s:
            user = await s.get(User, uid)
            if user is None:
                user = User(id=uid, email=claims.get("email"), display_name=claims.get("name"), picture_url=claims.get("picture"))
                s.add(user)
            else:
                user.email = claims.get("email") or user.email
                user.display_name = claims.get("name") or user.display_name
                user.picture_url = claims.get("picture") or user.picture_url
            await s.flush()
            s.expunge(user)
            return user

    async def aget(self, user_id: str) -> User | None:
        async with self.db.async_session() as s:
            user = await s.get(User, user_id)
            if user is not None:
                s.expunge(user)
            return user

    async def aupdate_profile(self, user_id: str, **fields) -> User:
        async with self.db.async_session() as s:
            user = await s.get(User, user_id)
            for key, value in fields.items():
                setattr(user, key, value)
            await s.flush()
            s.expunge(user)
            return user

    # --- sync (legacy path, being phased out) ---

    def upsert_from_claims(self, claims: dict) -> User:
        uid = claims["sub"]
        with self.db.session() as s:
            user = s.get(User, uid)
            if user is None:
                user = User(id=uid, email=claims.get("email"), display_name=claims.get("name"), picture_url=claims.get("picture"))
                s.add(user)
            else:
                user.email = claims.get("email") or user.email
                user.display_name = claims.get("name") or user.display_name
                user.picture_url = claims.get("picture") or user.picture_url
            s.flush()
            s.expunge(user)
            return user

    def get(self, user_id: str) -> User | None:
        with self.db.session() as s:
            user = s.get(User, user_id)
            if user is not None:
                s.expunge(user)
            return user

    def update_profile(self, user_id: str, **fields) -> User:
        with self.db.session() as s:
            user = s.get(User, user_id)
            for key, value in fields.items():
                setattr(user, key, value)
            s.flush()
            s.expunge(user)
            return user
