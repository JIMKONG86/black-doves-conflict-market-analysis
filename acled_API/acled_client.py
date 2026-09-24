"""Small ACLED OAuth client with cursor-based pagination.

Credentials are read by the calling script and are never written by this module.
Official API documentation: https://acleddata.com/acled-api-documentation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import requests


TOKEN_URL = "https://acleddata.com/oauth/token"
EVENTS_URL = "https://acleddata.com/api/acled/read"


class AcledApiError(RuntimeError):
    """Raised when authentication or an ACLED API request fails."""


@dataclass
class AcledCredentials:
    username: str | None = None
    password: str | None = None
    access_token: str | None = None

    def validate(self) -> None:
        if self.access_token:
            return
        if self.username and self.password:
            return
        raise ValueError(
            "Set ACLED_ACCESS_TOKEN or both ACLED_USERNAME and ACLED_PASSWORD in .env."
        )


class AcledClient:
    """Authenticate with ACLED and retrieve event records."""

    def __init__(
        self,
        credentials: AcledCredentials,
        session: requests.Session | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        credentials.validate()
        self.credentials = credentials
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.access_token = credentials.access_token
        self.refresh_token: str | None = None

    def authenticate(self) -> str:
        """Return an access token, requesting one when necessary."""
        if self.access_token:
            return self.access_token

        response = self.session.post(
            TOKEN_URL,
            data={
                "username": self.credentials.username,
                "password": self.credentials.password,
                "grant_type": "password",
                "client_id": "acled",
                "scope": "authenticated",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout_seconds,
        )
        self._raise_for_http_error(response, "ACLED authentication")
        payload = response.json()
        self.access_token = payload.get("access_token")
        self.refresh_token = payload.get("refresh_token")
        if not self.access_token:
            raise AcledApiError("ACLED authentication returned no access token.")
        return self.access_token

    def _refresh(self) -> bool:
        if not self.refresh_token:
            self.access_token = None
            return False

        response = self.session.post(
            TOKEN_URL,
            data={
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
                "client_id": "acled",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            self.access_token = None
            self.refresh_token = None
            return False
        payload = response.json()
        self.access_token = payload.get("access_token")
        self.refresh_token = payload.get("refresh_token", self.refresh_token)
        return bool(self.access_token)

    def get_events(self, params: dict[str, Any]) -> dict[str, Any]:
        """Retrieve one JSON response page from the ACLED event endpoint."""
        response = self._get(params)
        if response.status_code == 401:
            if not self._refresh():
                self.authenticate()
            response = self._get(params)

        self._raise_for_http_error(response, "ACLED event request")
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("success") is False:
            raise AcledApiError(f"ACLED returned an unsuccessful response: {payload}")
        return payload

    def iter_events(
        self,
        params: dict[str, Any],
        *,
        page_size: int = 5_000,
        max_rows: int | None = None,
    ) -> Iterable[dict[str, Any]]:
        """Yield all matching records using ACLED cursor-based pagination."""
        cursor: str | int | None = 0
        yielded = 0

        while cursor is not None:
            page_params = {
                **params,
                "_format": "json",
                "limit": page_size,
                "cursor": cursor,
            }
            payload = self.get_events(page_params)
            rows = payload.get("data") or []
            if not isinstance(rows, list):
                raise AcledApiError("ACLED response field 'data' is not a list.")

            for row in rows:
                if max_rows is not None and yielded >= max_rows:
                    return
                yield row
                yielded += 1

            next_cursor = payload.get("next_cursor")
            if next_cursor in (None, "", cursor) or not rows:
                return
            cursor = next_cursor

    def _get(self, params: dict[str, Any]) -> requests.Response:
        token = self.authenticate()
        return self.session.get(
            EVENTS_URL,
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=self.timeout_seconds,
        )

    @staticmethod
    def _raise_for_http_error(response: requests.Response, operation: str) -> None:
        if response.status_code < 400:
            return
        try:
            details = response.json()
        except ValueError:
            details = response.text[:500]
        raise AcledApiError(f"{operation} failed ({response.status_code}): {details}")
