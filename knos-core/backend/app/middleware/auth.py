# backend/app/middleware/auth.py
import time
from typing import Optional
import httpx
import structlog
from fastapi import HTTPException, Request
from functools import lru_cache

logger = structlog.get_logger()

_jwks_cache: dict = {}
_jwks_cached_at: float = 0
JWKS_TTL = 3600  # 1時間


async def get_jwks(team_domain: str) -> dict:
    global _jwks_cache, _jwks_cached_at

    now = time.monotonic()
    if _jwks_cache and now - _jwks_cached_at < JWKS_TTL:
        return _jwks_cache

    url = f"https://{team_domain}/cdn-cgi/access/certs"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cached_at = now
        logger.info("jwks_refreshed", team_domain=team_domain)
        return _jwks_cache


async def verify_cf_access_token(request: Request) -> Optional[str]:
    """Cloudflare Access JWTを検証してメールアドレスを返す"""
    from ..config import get_settings
    settings = get_settings()

    if settings.debug:
        # 開発環境では認証スキップ
        return "dev@localhost"

    token = request.headers.get("Cf-Access-Jwt-Assertion")
    if not token:
        raise HTTPException(status_code=401, detail="Missing CF-Access-JWT-Assertion header")

    if not settings.cf_team_domain or not settings.cf_aud:
        # Cloudflare未設定の場合はスキップ（localhost用）
        return "local@localhost"

    try:
        from jose import jwt, JWTError
        jwks = await get_jwks(settings.cf_team_domain)
        public_keys = jwks.get("keys", [])

        for key_data in public_keys:
            try:
                payload = jwt.decode(
                    token,
                    key_data,
                    algorithms=["RS256"],
                    audience=settings.cf_aud,
                )
                email = payload.get("email")
                return email
            except JWTError:
                continue

        raise HTTPException(status_code=401, detail="Invalid CF-Access token")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("cf_access_verify_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed")
