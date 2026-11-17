"""Optional GitHub-backed durable company checkpoint (single allowlisted ref/path).

The API client has separate read and write methods. ALL WRITE REQUESTS are
disabled unless an eligible repository owner enables a narrowly scoped GitHub
App installation and an explicit per-run activation flag. This module does not
provision the state branch, secrets, billing, cron jobs or workers.
"""
import base64
import hashlib
import json
import os
import re
from urllib import parse, request, error

from company.checkpoint_store import (
    CheckpointBlocked, validate_ledger, _bytes, MAX_SNAPSHOT_BYTES,
)

REPO = "Baraka-Hani/Serenity"
STATE_BRANCH = "serenity-company-state"
STATE_PATH = "state/company-ledger.json"
API_URL = f"https://api.github.com/repos/{REPO}/contents/{STATE_PATH}"
READ_URL = API_URL + "?ref=" + STATE_BRANCH
MAX_RESPONSE = 450000


class RemoteStateBlocked(RuntimeError):
    pass


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GithubCheckpointStore:
    def __init__(self, *, token="", transport=None):
        self.token = token
        self.transport = transport if transport is not None else request.build_opener(NoRedirect())

    def _query(self, url, *, method="GET", data=None):
        if url not in (READ_URL, API_URL) or method not in ("GET", "PUT"):
            raise RemoteStateBlocked("destination outside fixed GitHub checkpoint allowlist")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Serenity-company-ledger-v1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            if not isinstance(self.token, str) or "\r" in self.token or "\n" in self.token:
                raise RemoteStateBlocked("invalid authentication token")
            headers["Authorization"] = "Bearer " + self.token
        try:
            req = request.Request(
                url, data=None if data is None else json.dumps(data).encode("utf-8"),
                headers={**headers, **({"Content-Type": "application/json"} if data is not None else {})},
                method=method,
            )
            with self.transport.open(req, timeout=12) as response:
                if response.geturl() != url:
                    raise RemoteStateBlocked("redirects outside the approved path are forbidden")
                blob = response.read(MAX_RESPONSE+1)
                if len(blob) > MAX_RESPONSE:
                    raise RemoteStateBlocked("remote checkpoint response too large")
                result = json.loads(blob.decode("utf-8"))
                if not isinstance(result, dict):
                    raise RemoteStateBlocked("invalid GitHub state response")
                return result
        except error.HTTPError as exc:
            if exc.code in (409, 412, 422):
                raise RemoteStateBlocked("checkpoint conflict; refresh, never overwrite blindly") from None
            if exc.code == 404:
                raise RemoteStateBlocked("state branch/file missing; initial setup not authorized") from None
            if exc.code in (401, 403):
                raise RemoteStateBlocked("GitHub credential or permission refused") from None
            raise RemoteStateBlocked("GitHub API status " + str(exc.code)) from None
        except (error.URLError, TimeoutError):
            raise RemoteStateBlocked("GitHub unavailable; no automatic mutation retry") from None
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
            raise RemoteStateBlocked("malformed GitHub response") from None

    def read(self):
        result = self._query(READ_URL)
        if (result.get("type") != "file" or result.get("path") != STATE_PATH
                or result.get("encoding") != "base64"
                or not isinstance(result.get("sha"), str)
                or not re.fullmatch(r"[a-f0-9]{40}", result["sha"])
                or not isinstance(result.get("content"), str)):
            raise RemoteStateBlocked("untrusted GitHub contents metadata")
        try:
            # GitHub's base64 field can include line breaks; allow whitespace
            # only, then require strict base64 syntax and a valid Git blob SHA.
            encoded = "".join(result["content"].split())
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > MAX_SNAPSHOT_BYTES:
                raise RemoteStateBlocked("remote checkpoint too large")
            if "size" in result and (type(result["size"]) is not int
                                     or result["size"] != len(raw)):
                raise RemoteStateBlocked("GitHub content length does not match metadata")
            blob_sha = hashlib.sha1(
                b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw
            ).hexdigest()
            if blob_sha != result["sha"]:
                raise RemoteStateBlocked("checkpoint Git blob hash mismatch")
            ledger = validate_ledger(json.loads(raw.decode("utf-8")))
        except (ValueError, UnicodeError, CheckpointBlocked, base64.binascii.Error) as exc:
            raise RemoteStateBlocked("remote ledger content invalid") from exc
        return {"ledger": ledger, "remote_git_blob_sha": blob_sha,
                "source": "github_contents_read_only", "branch": STATE_BRANCH}

    def write_once(self, ledger, *, expected_git_blob_sha,
                   owner_setup_approved=False, spending_approved_no_overages=False):
        """One optimistic concurrency write, NEVER used by normal CI.

        Caller should be an explicitly activated, serialized GitHub Actions
        job after owner approves initial state branch + narrow credential.
        This does NOT authorize any agent source-code commit.
        """
        validate_ledger(ledger)
        if (os.environ.get("SERENITY_REMOTE_STATE_WRITE") != "true"
                or owner_setup_approved is not True
                or spending_approved_no_overages is not True):
            raise RemoteStateBlocked("remote writes disabled without owner-authorized setup")
        if not isinstance(self.token, str) or not self.token.strip():
            raise RemoteStateBlocked("required scoped credential missing")
        if (not isinstance(expected_git_blob_sha, str)
                or len(expected_git_blob_sha) != 40
                or any(ch not in "0123456789abcdef" for ch in expected_git_blob_sha)):
            raise RemoteStateBlocked("expected Git blob SHA required; no blind create/overwrite")
        payload = {
            "message": "company-state: checkpoint approved task-event ledger",
            "branch": STATE_BRANCH,
            "sha": expected_git_blob_sha,
            "content": base64.b64encode(_bytes(ledger)).decode("ascii"),
        }
        result = self._query(API_URL, method="PUT", data=payload)
        commit = result.get("commit")
        if not isinstance(commit, dict) or not isinstance(commit.get("sha"), str):
            raise RemoteStateBlocked("GitHub checkpoint acknowledgement unverified")
        return {"remote_write_completed": True, "branch": STATE_BRANCH,
                "path": STATE_PATH, "commit_sha": commit["sha"],
                "last_hash": ledger["last_hash"]}
