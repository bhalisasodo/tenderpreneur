#!/usr/bin/env python3
"""Verify public health and the contractor/supplier dashboard API logins."""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(url: str, method: str = "GET", payload: dict | None = None, token: str | None = None):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"{method} {url} returned HTTP {error.code}.") from None
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not reach {url}: {type(error).__name__}.") from None
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{method} {url} returned invalid JSON.") from error


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value.strip():
        raise RuntimeError(f"Required environment variable {name} is not set.")
    return value


def verify_identity(api_url: str, identity: str, expected_type: str) -> None:
    email = require_env(f"BOQPRO_SMOKE_{identity}_EMAIL")
    password = require_env(f"BOQPRO_SMOKE_{identity}_PASSWORD")
    status_code, session = request_json(
        f"{api_url}/auth/login",
        method="POST",
        payload={"email": email, "password": password},
    )
    if status_code != 200 or not session.get("access_token"):
        raise RuntimeError(f"{identity.lower()} login did not return an authenticated session.")
    if session.get("organisation", {}).get("type") != expected_type:
        raise RuntimeError(f"{identity.lower()} credentials are not for a {expected_type} account.")
    if expected_type == "contractor" and session.get("user", {}).get("role") == "platform_operator":
        raise RuntimeError("Contractor smoke credentials must not use a platform operator account.")
    if expected_type == "supplier" and session.get("supplier_approval_status") != "approved":
        raise RuntimeError("Supplier smoke account must be approved for marketplace access.")

    token = session["access_token"]
    _, profile = request_json(f"{api_url}/auth/me", token=token)
    if profile.get("organisation", {}).get("type") != expected_type:
        raise RuntimeError(f"{identity.lower()} session profile has the wrong organisation type.")

    dashboard_path = "/boqs" if expected_type == "contractor" else "/suppliers/quote-requests"
    request_json(f"{api_url}{dashboard_path}", token=token)
    print(f"PASS: {identity.lower()} login, session profile, and dashboard API")


def main() -> int:
    try:
        api_url = require_env("BOQPRO_SMOKE_API_URL").strip().rstrip("/")
        health_status, health = request_json(f"{api_url}/health/ready")
        if health_status != 200 or health.get("status") != "ready":
            raise RuntimeError("API readiness endpoint did not return status=ready.")
        print("PASS: API readiness")
        verify_identity(api_url, "CONTRACTOR", "contractor")
        verify_identity(api_url, "SUPPLIER", "supplier")
    except RuntimeError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
