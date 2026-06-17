"""
Refresh-token cookie helpers.

Security model:
- Access token: short-lived, returned in JSON body only, held in memory on the
  frontend (never written to localStorage/sessionStorage).
- Refresh token: long-lived, set as an httpOnly cookie. JavaScript cannot read
  it, so XSS cannot exfiltrate it. SameSite=Lax blocks it being sent on
  cross-site form posts/script-initiated requests, mitigating CSRF for the
  refresh endpoint without requiring a CSRF token round-trip for that route.
"""

from __future__ import annotations

from django.conf import settings

REFRESH_COOKIE_NAME = "efs_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth/"


def _cookie_samesite() -> str:
    return getattr(settings, "REFRESH_COOKIE_SAMESITE", "Lax")


def set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=REFRESH_COOKIE_PATH,
        secure=not settings.DEBUG,
        httponly=True,
        samesite=_cookie_samesite(),
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
