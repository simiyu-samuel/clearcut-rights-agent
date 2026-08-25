from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

from .config import Settings


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """The trusted identity contract used by the API authorization layer."""

    actor_id: str
    email: str | None
    display_name: str
    claims: Mapping[str, Any]


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def _identity_from_claims(claims: Mapping[str, Any], settings: Settings) -> AuthenticatedIdentity:
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_subject_missing")

    issuer = str(claims.get("iss") or "")
    project_id = settings.google_cloud_project
    expected_issuer = f"https://securetoken.google.com/{project_id}" if project_id else None
    if expected_issuer and issuer != expected_issuer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_issuer_invalid")

    email = str(claims.get("email") or "").strip() or None
    display_name = str(
        claims.get("name") or claims.get("display_name") or email or subject
    ).strip()
    return AuthenticatedIdentity(
        actor_id=subject,
        email=email,
        display_name=display_name,
        claims=claims,
    )


def verify_identity_token(token: str, settings: Settings) -> AuthenticatedIdentity:
    audience = settings.auth_audience or settings.google_cloud_project
    if not audience:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identity_platform_not_configured",
        )
    try:
        claims = id_token.verify_firebase_token(
            token,
            GoogleRequest(),
            audience=audience,
            clock_skew_in_seconds=30,
        )
        return _identity_from_claims(claims, settings)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - provider failures are environment-dependent
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_invalid",
        ) from exc


def authenticate_request(
    request: Request,
    authorization: str | None,
    actor_header: str | None,
    settings: Settings,
) -> AuthenticatedIdentity:
    cached = getattr(request.state, "clearcut_identity", None)
    if cached is not None:
        return cached

    if settings.auth_mode == "demo":
        identity = AuthenticatedIdentity(
            actor_id=actor_header or "demo-user",
            email=None,
            display_name=actor_header or "Demo user",
            claims={"demo": True},
        )
        request.state.clearcut_identity = identity
        return identity

    token = bearer_token(authorization)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bearer_token_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    identity = verify_identity_token(token, settings)
    request.state.clearcut_identity = identity
    return identity
