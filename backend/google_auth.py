"""Sign in with Google for the local Serenity backend.

The browser gets a Google ID token from Google Identity Services and posts it
to /api/auth/google. This module checks that token with Google's tokeninfo
endpoint (standard library only, no extra dependencies), then confirms it was
issued for this server's OAuth client.

Configuration: set ROAM_GOOGLE_CLIENT_ID to the OAuth 2.0 *Web application*
client ID from Google Cloud Console. Without it, Google sign-in stays off.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def client_id():
    return os.environ.get("ROAM_GOOGLE_CLIENT_ID", "").strip()


class GoogleAuthError(ValueError):
    pass


def fetch_tokeninfo(credential):
    """Ask Google to validate the ID token signature and return its claims."""
    url = f"{TOKENINFO_URL}?{urllib.parse.urlencode({'id_token': credential})}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError:
        raise GoogleAuthError("Google could not confirm this sign-in. Please try again.")
    except (urllib.error.URLError, TimeoutError, OSError):
        raise GoogleAuthError("The server could not reach Google to confirm your sign-in. Try again shortly.")
    except json.JSONDecodeError:
        raise GoogleAuthError("Google returned an unexpected response. Please try again.")


def verify(credential, fetch=None):
    """Return {sub, email, name, picture} for a valid Google ID token, else raise."""
    expected = client_id()
    if not expected:
        raise GoogleAuthError("Google sign-in is not set up on this server yet.")
    if not isinstance(credential, str) or not 20 <= len(credential) <= 4096 or credential.count(".") != 2:
        raise GoogleAuthError("Google sign-in did not return a valid credential.")
    claims = (fetch or fetch_tokeninfo)(credential)
    if not isinstance(claims, dict):
        raise GoogleAuthError("Google could not confirm this sign-in. Please try again.")
    if claims.get("aud") != expected:
        raise GoogleAuthError("This Google sign-in was issued for a different app.")
    if claims.get("iss") not in ISSUERS:
        raise GoogleAuthError("This sign-in did not come from Google.")
    try:
        if int(claims.get("exp", 0)) <= time.time():
            raise GoogleAuthError("This Google sign-in has expired. Please try again.")
    except (TypeError, ValueError):
        raise GoogleAuthError("Google could not confirm this sign-in. Please try again.")
    if str(claims.get("email_verified", "")).lower() != "true":
        raise GoogleAuthError("Your Google email address must be verified to sign in.")
    sub = str(claims.get("sub", ""))
    email = str(claims.get("email", "")).strip().lower()
    if not sub or not email:
        raise GoogleAuthError("Google did not share the details needed to sign in.")
    name = str(claims.get("name") or claims.get("given_name") or email.split("@")[0]).strip()[:80] or "Traveller"
    return {"sub": sub, "email": email, "name": name}
