import os
from datetime import datetime, timedelta, timezone
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from app.models.user import User

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET missing from environment")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MINUTES = 30
REFRESH_TOKEN_TTL_DAYS = 30

_bearer_scheme = HTTPBearer(auto_error=False)


def _token(payload: dict) -> str:
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "provider": user.provider,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)).timestamp()),
    }
    return _token(payload)


def create_refresh_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "typ": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=REFRESH_TOKEN_TTL_DAYS)).timestamp()),
    }
    return _token(payload)


def decode_token(token: str, expected_typ: str = "access") -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")
    if payload.get("typ") != expected_typ:
        raise HTTPException(status_code=401, detail=f"Wrong token type (expected {expected_typ}).")
    return payload


def make_signed_state(provider: str) -> str:
   # --> Create a signed state parameter for OAuth flow.
    now = datetime.now(timezone.utc)
    payload = {
        "p": provider,
        "n": os.urandom(8).hex(),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# --> Verify the signed state parameter from OAuth callback.
def verify_signed_state(state: str, provider: str) -> bool:
    try:
        payload = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        return False
    return payload.get("p") == provider


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: resolves the User from a Bearer JWT."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated. Sign in to continue.")
    payload = decode_token(credentials.credentials)
    result = await db.execute(select(User).filter(User.id == payload["sub"]))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    # --> Optional User
    if credentials is None or not JWT_SECRET:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except HTTPException:
        return None
    result = await db.execute(select(User).filter(User.id == payload["sub"]))
    return result.scalars().first()
