"""Verified bearer identity for memory and checkpoint ownership.

OIDC is the production mode. Development tokens require explicit configuration;
there is no fallback to client-supplied UUIDs when verification fails.
"""

import asyncio
from dataclasses import dataclass
from functools import lru_cache
import os
from uuid import UUID, NAMESPACE_URL, uuid5

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID


class TokenVerifier:
    def __init__(self, *, issuer: str, audience: str, jwks_url: str | None = None,
                 development_secret: str | None = None):
        if not issuer or not audience:
            raise ValueError("Authentication issuer and audience are required")
        if bool(jwks_url) == bool(development_secret):
            raise ValueError("Configure exactly one authentication mode")
        if jwks_url and not jwks_url.startswith("https://"):
            raise ValueError("OIDC signing keys must use HTTPS")
        if development_secret and len(development_secret.encode()) < 32:
            raise ValueError("Development signing secret must contain at least 32 bytes")
        self.issuer = issuer
        self.audience = audience
        self.secret = development_secret
        self.jwks = jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300, timeout=5) if jwks_url else None

    def verify(self, token: str) -> Principal:
        if len(token) > 16384:
            raise jwt.InvalidTokenError("Token exceeds size limit")
        key = self.secret if self.secret else self.jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["HS256"] if self.secret else ["RS256"],
            issuer=self.issuer, audience=self.audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]})
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject.strip():
            raise jwt.InvalidTokenError("Subject is missing")
        # Never trust an additional user_id claim supplied by a caller.
        if self.secret:
            try:
                user_id = UUID(subject)
            except ValueError as exc:
                raise jwt.InvalidTokenError("Development subject must be a UUID") from exc
        else:
            user_id = uuid5(NAMESPACE_URL, self.issuer + "#" + subject)
        return Principal(user_id=user_id)


@lru_cache(maxsize=1)
def get_verifier() -> TokenVerifier:
    mode = os.environ.get("TRAVEL_AUTH_MODE", "oidc")
    if mode == "development":
        if os.environ.get("APP_ENV") != "development":
            raise ValueError("Development tokens require APP_ENV=development")
        return TokenVerifier(issuer="trip-planner-development", audience="trip-planner",
                             development_secret=os.environ.get("TRAVEL_DEV_JWT_SECRET"))
    if mode != "oidc":
        raise ValueError("Unsupported authentication mode")
    return TokenVerifier(issuer=os.environ.get("TRAVEL_OIDC_ISSUER", ""),
                         audience=os.environ.get("TRAVEL_OIDC_AUDIENCE", ""),
                         jwks_url=os.environ.get("TRAVEL_OIDC_JWKS_URL"))


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        verifier = get_verifier()
    except ValueError:
        raise HTTPException(503, "Authentication is not configured") from None
    try:
        # JWKS refresh uses a bounded synchronous HTTP client; keep it off the event loop.
        return await asyncio.to_thread(verifier.verify, credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"}) from None
