"""Authentication helpers for organization-scoped API access."""

from __future__ import annotations

import hmac
import json
import os
from typing import Annotated

from fastapi import Header, HTTPException, status


def _environment() -> str:
    return os.environ.get("ANNEAL_ENV", "development").strip().lower()


def _default_org() -> str:
    return os.environ.get("ANNEAL_ORG_ID", "org_demo").strip() or "org_demo"


def _api_keys() -> dict[str, str]:
    raw = os.environ.get("ANNEAL_API_KEYS_JSON", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("ANNEAL_API_KEYS_JSON must be a JSON object") from exc
        if not isinstance(parsed, dict) or not all(
            isinstance(org, str) and isinstance(key, str) and org and key for org, key in parsed.items()
        ):
            raise RuntimeError("ANNEAL_API_KEYS_JSON must map organization ids to non-empty keys")
        return parsed

    single_key = os.environ.get("ANNEAL_API_KEY", "").strip()
    return {_default_org(): single_key} if single_key else {}


def validate_auth_configuration() -> None:
    if _environment() == "production" and not _api_keys():
        raise RuntimeError(
            "Production API authentication is not configured. Set ANNEAL_API_KEY or ANNEAL_API_KEYS_JSON."
        )


def require_organization(
    x_anneal_org: Annotated[str | None, Header(alias="X-Anneal-Org")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Authenticate a request and return its organization id.

    Development remains zero-config for the offline demo. Production fails
    closed unless an API key is configured for the requested organization.
    """

    organization_id = (x_anneal_org or _default_org()).strip()
    if not organization_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing organization id")

    keys = _api_keys()
    if not keys:
        if _environment() == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API authentication is not configured",
            )
        return organization_id

    expected = keys.get(organization_id)
    if expected is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown organization")

    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return organization_id
