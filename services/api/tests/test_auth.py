from dataclasses import replace

from starlette.requests import Request

from clearcut_api import auth as auth_module
from clearcut_api.config import settings


def test_bearer_token_parser_rejects_malformed_values() -> None:
    assert auth_module.bearer_token(None) is None
    assert auth_module.bearer_token("Basic abc") is None
    assert auth_module.bearer_token("Bearer ") is None
    assert auth_module.bearer_token("Bearer signed-token") == "signed-token"


def test_identity_claims_require_expected_firebase_issuer() -> None:
    identity_settings = replace(
        settings,
        auth_mode="identity_platform",
        google_cloud_project="clearcut-test",
    )
    claims = {
        "sub": "user-123",
        "email": "producer@example.com",
        "name": "Producer",
        "iss": "https://securetoken.google.com/another-project",
    }

    try:
        auth_module._identity_from_claims(claims, identity_settings)
    except Exception as error:
        assert getattr(error, "status_code", None) == 401
    else:  # pragma: no cover - the assertion above is the expected branch
        raise AssertionError("wrong token issuer was accepted")


def test_real_auth_requires_bearer_and_ignores_actor_header(monkeypatch) -> None:
    identity_settings = replace(
        settings,
        auth_mode="identity_platform",
        google_cloud_project="clearcut-test",
    )

    request = Request({"type": "http", "headers": []})
    try:
        auth_module.authenticate_request(request, None, None, identity_settings)
    except Exception as error:
        assert getattr(error, "status_code", None) == 401
    else:  # pragma: no cover - the assertion above is the expected branch
        raise AssertionError("missing bearer token was accepted")

    monkeypatch.setattr(
        auth_module,
        "verify_identity_token",
        lambda token, current_settings: auth_module.AuthenticatedIdentity(
            actor_id="user-123",
            email="producer@example.com",
            display_name="Producer",
            claims={"sub": "user-123"},
        ),
    )
    authenticated_request = Request(
        {"type": "http", "headers": [(b"authorization", b"Bearer signed-token")]}
    )
    identity = auth_module.authenticate_request(
        authenticated_request,
        "Bearer signed-token",
        "demo-producer",
        identity_settings,
    )
    assert identity.actor_id == "user-123"
