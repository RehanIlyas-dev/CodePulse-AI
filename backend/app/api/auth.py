import os
from urllib.parse import urlencode
import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    make_signed_state,
    verify_signed_state,
    get_current_user,
    decode_token,
)
from app.models.user import User

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174")
API_PUBLIC_BASE = os.getenv("API_PUBLIC_BASE", "http://localhost:8000/api/v1")
REFRESH_COOKIE = "cp_refresh"

PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "openid email profile",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "extra_authorize_params": {"access_type": "online", "prompt": "select_account"},
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scope": "read:user user:email",
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
        "extra_authorize_params": {},
    },
}


def _credentials(provider: str) -> tuple[str, str]:
    cfg = PROVIDERS[provider]
    client_id = os.getenv(cfg["client_id_env"], "")
    client_secret = os.getenv(cfg["client_secret_env"], "")
    if not client_id or not client_secret:
        raise HTTPException(status_code=501, detail=f"{provider} OAuth is not configured.")
    return client_id, client_secret


def _redirect_uri(provider: str) -> str:
    return f"{API_PUBLIC_BASE}/auth/callback/{provider}"

# --> OAuth login endpoint: Redirects user to the provider's authorization URL.
@router.get("/login/{provider}")
async def oauth_login(provider: str):
    # --> Redirect user to the provider's OAuth authorization URL
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    client_id, _ = _credentials(provider)
    cfg = PROVIDERS[provider]
    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": make_signed_state(provider),
        **cfg["extra_authorize_params"],
    }
    return RedirectResponse(f"{cfg['authorize_url']}?{urlencode(params)}")

# --> OAuth callback endpoint: Handles the provider's redirect after user authorization.
@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    # --> Handle the OAuth callback, exchange code for token, fetch user profile, and upsert user in DB
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    if error or not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/?auth_error=denied")
    if not verify_signed_state(state, provider):
        return RedirectResponse(f"{FRONTEND_URL}/?auth_error=bad_state")

    client_id, client_secret = _credentials(provider)
    cfg = PROVIDERS[provider]

    async with httpx.AsyncClient(timeout=15) as hc:
        # 1) Exchange code -> access token
        token_resp = await hc.post(
            cfg["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _redirect_uri(provider),
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse(f"{FRONTEND_URL}/?auth_error=token_exchange")

        headers = {"Authorization": f"Bearer {access_token}"}

        # 2) Fetch profile
        if provider == "google":
            info = (await hc.get("https://openidconnect.googleapis.com/v1/userinfo", headers=headers)).json()
            profile = {
                "provider_id": str(info.get("sub")),
                "email": info.get("email"),
                "name": info.get("name"),
                "avatar_url": info.get("picture"),
            }
        else:  # github
            info = (await hc.get("https://api.github.com/user", headers={**headers, "User-Agent": "codepulse-ai"})).json()
            email = info.get("email")
            if not email:
                emails_resp = await hc.get("https://api.github.com/user/emails", headers={**headers, "User-Agent": "codepulse-ai"})
                primary = next((e for e in emails_resp.json() if e.get("primary")), None)
                email = primary.get("email") if primary else None
            profile = {
                "provider_id": str(info.get("id")),
                "email": email,
                "name": info.get("name") or info.get("login"),
                "avatar_url": info.get("avatar_url"),
            }

    if not profile.get("email"):
        return RedirectResponse(f"{FRONTEND_URL}/?auth_error=no_email")

    # 3) Upsert: merge by email first (same human, any provider), else by provider identity
    result = await db.execute(select(User).filter(User.email == profile["email"]))
    user = result.scalars().first()
    if user is None:
        result = await db.execute(
            select(User).filter(User.provider == provider, User.provider_id == profile["provider_id"])
        )
        user = result.scalars().first()

    if user is None:
        user = User(
            email=profile["email"],
            name=profile.get("name"),
            avatar_url=profile.get("avatar_url"),
            provider=provider,
            provider_id=profile["provider_id"],
        )
        db.add(user)
    else:
        user.provider = provider
        user.provider_id = profile["provider_id"]
        user.name = profile.get("name") or user.name
        user.avatar_url = profile.get("avatar_url") or user.avatar_url

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user)
    return RedirectResponse(f"{FRONTEND_URL}/#token={token}")


@router.get("/me")
async def auth_me(user: User = Depends(get_current_user)):
    # --> Return the authenticated user's profile information
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "provider": user.provider,
    }
