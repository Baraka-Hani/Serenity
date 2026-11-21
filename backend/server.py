"""Local, zero-service-cost backend for Serenity. Run: python3 backend/server.py"""
from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import threading
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

import social
import studio_import
import trip_visibility
import trip_locations
import visited_locations
import messaging
import account_discovery
import video_stream
import google_auth

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("ROAM_DATA_DIR", Path(__file__).resolve().parent / "data"))
UPLOADS = DATA / "uploads"
DB = DATA / "roam.sqlite3"
HOST = os.environ.get("ROAM_HOST", "127.0.0.1").strip()
if not HOST:
    raise ValueError("ROAM_HOST must be a non-empty interface address.")
PORT = int(os.environ.get("ROAM_PORT", "8765"))
PUBLIC_ORIGIN = os.environ.get("ROAM_PUBLIC_ORIGIN", "").rstrip("/")
if PUBLIC_ORIGIN and (urlparse(PUBLIC_ORIGIN).scheme != "https" or not urlparse(PUBLIC_ORIGIN).hostname or urlparse(PUBLIC_ORIGIN).path):
    raise ValueError("ROAM_PUBLIC_ORIGIN must be an HTTPS origin without a path.")
MAX_VIDEO = 50 * 1024 * 1024
MAX_CLIPS_PER_FEED = 500
SESSION_AGE = 90 * 24 * 60 * 60  # stay signed in for 90 days after the last visit
SESSION_RENEW_AFTER = 24 * 60 * 60  # slide the expiry forward at most once a day
PASSWORD_MIN, PASSWORD_MAX = 8, 128
# Public "pitch preview": anyone can watch, explore the map and play Engage,
# but every change (accounts, posting, likes, messages, uploads) is refused.
GUEST_PREVIEW = os.environ.get("ROAM_GUEST_PREVIEW", "").strip().lower() in {"1", "true", "yes", "on"}
GUEST_PREVIEW_MESSAGE = "This is a guest preview. Watch videos, explore the map and try the games. Accounts, posting and uploads are switched off."
LOGIN_WINDOW, LOGIN_MAX_FAILURES = 15 * 60, 8
_login_failures = {}
_login_lock = threading.Lock()
STATIC = {"/": "test.html", "/test.html": "test.html", "/app.html": "app.html", "/feed.html": "feed.html", "/my-clips.html": "my-clips.html", "/my-clips.css": "my-clips.css", "/my-clips.js": "my-clips.js", "/account.html": "account.html", "/account.css": "account.css", "/account.js": "account.js", "/profile.html": "profile.html", "/profile.css": "profile.css", "/profile.js": "profile.js", "/auth.html": "auth.html", "/search.html": "search.html", "/serenity-logo.svg": "serenity-logo.svg", "/serenity-icon-192.png": "serenity-icon-192.png", "/serenity-icon-512.png": "serenity-icon-512.png", "/shared-theme.js": "shared-theme.js", "/auth-client.js": "auth-client.js", "/app-client.js": "app-client.js", "/app-studio.js": "app-studio.js", "/social-feed.js": "social-feed.js", "/social-feed.css": "social-feed.css", "/header-feed-picker.js": "header-feed-picker.js", "/liquid-toolbar.css": "liquid-toolbar.css", "/liquid-toolbar.js": "liquid-toolbar.js", "/trip-sidebar.css": "trip-sidebar.css", "/trip-sidebar.js": "trip-sidebar.js", "/feed-view.css": "feed-view.css", "/feed-view.js": "feed-view.js", **{f"/tile-{number:02}.html": f"tile-{number:02}.html" for number in range(1, 6)}}
STATIC.update({f'/{name}': name for name in ('home.html', 'home.css', 'app-shell.css', 'engage.html', 'engage.css', 'engage.js', 'studio.html', 'studio.css')})
STATIC.update({"/manifest.webmanifest": "manifest.webmanifest", "/service-worker.js": "service-worker.js", "/app-pwa.js": "app-pwa.js"})
VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov", "video/x-m4v": ".m4v"}
STATIC.update({"/feed-hub.js": "feed-hub.js", "/feed-hub.css": "feed-hub.css"})
STATIC.update({f'/{name}': name for name in ('studio-import.js', 'studio-import.css', 'studio-grouping.js', 'studio-video-analysis.js', 'studio-vision-worker.js')})
STATIC.update({f'/{name}': name for name in ('studio-publication.js', 'studio-publication.css')})
STATIC.update({f'/{name}': name for name in ('map.html', 'map-core.js', 'travel-map.js', 'travel-map.css', 'destination-picker.js', 'destination-picker.css')})
STATIC.update({f'/{name}': name for name in ('map-world.js',)})
STATIC.update({f'/{name}': name for name in ('messages-client.js', 'messages.js', 'messages.css')})
STATIC.update({f'/{name}': name for name in ('account-discovery.js', 'account-discovery.css')})
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def db():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def username_base(name):
    base = re.sub(r"[^a-z0-9_]", "", re.sub(r"[\s.-]+", "_", name.lower())).strip("_")[:20] or "traveller"
    return base if len(base) >= 3 else f"{base}_user"


def init():
    DATA.mkdir(parents=True, exist_ok=True)
    UPLOADS.mkdir(parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    os.chmod(UPLOADS, 0o700)
    with db() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
          salt BLOB NOT NULL, password_hash BLOB NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          expires_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clips (
          id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          original_name TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL,
          created_at INTEGER NOT NULL, feed_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS feed_notes (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          feed_id INTEGER NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feed_details (
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          feed_id INTEGER NOT NULL, destination TEXT NOT NULL, dates TEXT NOT NULL,
          summary TEXT NOT NULL, highlights TEXT NOT NULL, updated_at INTEGER NOT NULL,
          PRIMARY KEY (user_id, feed_id)
        );
        CREATE TABLE IF NOT EXISTS feed_names (
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          feed_id INTEGER NOT NULL, name TEXT NOT NULL,
          PRIMARY KEY (user_id, feed_id)
        );
        CREATE TABLE IF NOT EXISTS user_feeds (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS feeds_by_user ON user_feeds(user_id, id);
        CREATE TABLE IF NOT EXISTS app_migrations (
          name TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS themes (
          user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          accent TEXT NOT NULL, soft TEXT NOT NULL, paper TEXT NOT NULL, ink TEXT NOT NULL,
          energy INTEGER NOT NULL
        );
        """)
        user_columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if "public_id" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN public_id TEXT")
        if "username" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "bio" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN bio TEXT NOT NULL DEFAULT ''")
        if "google_sub" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_google_sub ON users(google_sub) WHERE google_sub IS NOT NULL")
        session_columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
        if "created_at" not in session_columns:
            connection.execute("ALTER TABLE sessions ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0")
        connection.execute("CREATE INDEX IF NOT EXISTS sessions_by_user ON sessions(user_id)")
        connection.execute("DELETE FROM sessions WHERE expires_at<=?", (int(time.time()),))
        existing_users = connection.execute("SELECT id, name, username, public_id FROM users ORDER BY id").fetchall()
        for existing in existing_users:
            public_id = existing["public_id"] or secrets.token_hex(8)
            username = existing["username"]
            if not username:
                base = username_base(existing["name"])
                username = base
                suffix = 2
                while connection.execute("SELECT 1 FROM users WHERE username=? AND id<>?", (username, existing["id"])).fetchone():
                    username = f"{base[:20-len(str(suffix))]}{suffix}"
                    suffix += 1
            connection.execute("UPDATE users SET public_id=?, username=? WHERE id=?", (public_id, username, existing["id"]))
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_public_id ON users(public_id)")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_username ON users(username COLLATE NOCASE)")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(clips)")}
        if "feed_id" not in columns:
            connection.execute("ALTER TABLE clips ADD COLUMN feed_id INTEGER")
        social.init(connection)
        studio_import.init(connection)
        trip_locations.init(connection)
        visited_locations.init(connection)
        messaging.init(connection)
        account_discovery.init(connection)
        if not connection.execute("SELECT 1 FROM app_migrations WHERE name='global-user-feeds'").fetchone():
            users = connection.execute("SELECT id FROM users ORDER BY id").fetchall()
            for user in users:
                user_id = user["id"]
                for legacy_id in range(1, 6):
                    old_name = connection.execute("SELECT name FROM feed_names WHERE user_id=? AND feed_id=?", (user_id, legacy_id)).fetchone()
                    name = old_name["name"] if old_name else f"Feed {legacy_id:02d}"
                    cursor = connection.execute("INSERT INTO user_feeds(user_id,name,created_at) VALUES (?,?,?)", (user_id, name, int(time.time())))
                    feed_id = cursor.lastrowid
                    connection.execute("UPDATE clips SET feed_id=? WHERE user_id=? AND feed_id=?", (feed_id, user_id, legacy_id))
                    connection.execute("UPDATE feed_notes SET feed_id=? WHERE user_id=? AND feed_id=?", (feed_id, user_id, legacy_id))
                    connection.execute("UPDATE feed_details SET feed_id=? WHERE user_id=? AND feed_id=?", (feed_id, user_id, legacy_id))
                    connection.execute("UPDATE feed_names SET feed_id=? WHERE user_id=? AND feed_id=?", (feed_id, user_id, legacy_id))
            connection.execute("INSERT INTO app_migrations(name) VALUES ('global-user-feeds')")
    os.chmod(DB, 0o600)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310000)


USER_FIELDS = ("id", "public_id", "username", "email", "name", "bio")


def create_user(connection, email, name, password=None, google_sub=None):
    """Insert a new account. Accounts made with Google have no usable password."""
    base = username_base(name)
    username = base
    suffix = 2
    while connection.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone():
        username = f"{base[:20-len(str(suffix))]}{suffix}"
        suffix += 1
    public_id = secrets.token_hex(8)
    salt = secrets.token_bytes(16)
    password_hash = hash_password(password, salt) if password is not None else b""
    cursor = connection.execute("INSERT INTO users(email,name,salt,password_hash,created_at,public_id,username,bio,google_sub) VALUES (?,?,?,?,?,?,?,?,?)", (email, name, salt, password_hash, int(time.time()), public_id, username, "", google_sub))
    user = {"id": cursor.lastrowid, "public_id": public_id, "username": username, "email": email, "name": name, "bio": ""}
    for feed_number in range(1, 6):
        connection.execute("INSERT INTO user_feeds(user_id,name,created_at) VALUES (?,?,?)", (user["id"], f"Feed {feed_number:02d}", int(time.time())))
    return user


def password_matches(user, password):
    if not user["password_hash"] or len(password) > PASSWORD_MAX:
        return False
    return hmac.compare_digest(hash_password(password, user["salt"]), user["password_hash"])


def login_blocked(key):
    now = time.time()
    with _login_lock:
        recent = [moment for moment in _login_failures.get(key, []) if now - moment < LOGIN_WINDOW]
        if recent: _login_failures[key] = recent
        else: _login_failures.pop(key, None)
        return len(recent) >= LOGIN_MAX_FAILURES


def record_login_failure(key):
    with _login_lock:
        _login_failures.setdefault(key, []).append(time.time())


def clear_login_failures(key):
    with _login_lock:
        _login_failures.pop(key, None)


def session_cookie(token, max_age):
    cookie = f"roam_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={max_age}"
    return cookie + "; Secure" if PUBLIC_ORIGIN else cookie


class Handler(BaseHTTPRequestHandler):
    server_version = "Serenity/1.0"
    # Keep-alive lets a video's many small range requests reuse one connection.
    protocol_version = "HTTP/1.1"
    timeout = 30  # drop idle keep-alive sockets so threads are not held forever

    def parse_request(self):
        if not super().parse_request():
            return False
        # Write handlers may reply before reading the whole request body; closing
        # afterwards keeps unread bytes from corrupting the next request.
        if self.command not in ("GET", "HEAD"):
            self.close_connection = True
        return True

    def end_headers(self):
        if self.close_connection and self.request_version == "HTTP/1.1":
            self.send_header("Connection", "close")
        super().end_headers()

    def valid_host(self):
        allowed = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        if PUBLIC_ORIGIN:
            allowed.add(urlparse(PUBLIC_ORIGIN).netloc)
        if self.headers.get("Host") not in allowed:
            self.respond(403, {"error": "Host is not allowed."})
            return False
        return True

    def respond(self, code, payload, extra_headers=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body)),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff"
        }
        refreshed = getattr(self, "_refreshed_cookie", None)
        if refreshed and "Set-Cookie" not in (extra_headers or {}):
            headers["Set-Cookie"] = refreshed
        self._refreshed_cookie = None
        headers.update(extra_headers or {})
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def body(self, limit=8192):
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid request size")
        if size < 1 or size > limit:
            raise ValueError("Request is empty or too large")
        return self.rfile.read(size)

    def json_body(self):
        try:
            value = json.loads(self.body())
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Invalid JSON")
        if not isinstance(value, dict):
            raise ValueError("Expected an object")
        return value

    def user(self):
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
            token = jar["roam_session"].value
        except (KeyError, cookies.CookieError):
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        now = int(time.time())
        with db() as connection:
            user = connection.execute("""SELECT users.id, users.public_id, users.username, users.email, users.name, users.bio, sessions.expires_at FROM sessions
                JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires_at>?""", (digest, now)).fetchone()
            if user and user["expires_at"] < now + SESSION_AGE - SESSION_RENEW_AFTER:
                # Keep active travellers signed in: slide the 90-day window forward.
                connection.execute("UPDATE sessions SET expires_at=? WHERE token_hash=?", (now + SESSION_AGE, digest))
                self._refreshed_cookie = session_cookie(token, SESSION_AGE)
        if not user:
            return None
        return {key: user[key] for key in USER_FIELDS}

    def require_user(self):
        user = self.user()
        if not user:
            self.respond(401, {"error": "Sign in to continue."})
        return user

    def guest_preview_blocks_write(self):
        if GUEST_PREVIEW:
            self.respond(403, {"error": GUEST_PREVIEW_MESSAGE, "guest_preview": True})
            return True
        return False

    def same_origin(self):
        if not self.valid_host(): return False
        origin = self.headers.get("Origin")
        expected = PUBLIC_ORIGIN or f"http://{self.headers.get('Host', '')}"
        if origin != expected:
            self.respond(403, {"error": "Request origin is not allowed."})
            return False
        return True

    def session(self, user):
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with db() as connection:
            connection.execute("INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES (?, ?, ?, ?)", (digest, user["id"], int(time.time()) + SESSION_AGE, int(time.time())))
        self.respond(200, {"user": {key: user[key] for key in USER_FIELDS}}, {"Set-Cookie": session_cookie(token, SESSION_AGE)})

    def session_digest(self):
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
            return hashlib.sha256(jar["roam_session"].value.encode()).hexdigest()
        except (KeyError, cookies.CookieError):
            return None

    def google_sign_in(self):
        data = self.json_body()
        try:
            profile = google_auth.verify(data.get("credential"))
        except google_auth.GoogleAuthError as error:
            return self.respond(401, {"error": str(error)})
        with db() as connection:
            user = connection.execute("SELECT * FROM users WHERE google_sub=?", (profile["sub"],)).fetchone()
            if not user:
                existing = connection.execute("SELECT * FROM users WHERE email=?", (profile["email"],)).fetchone()
                if existing and existing["google_sub"]:
                    return self.respond(409, {"error": "This email is already connected to a different Google account."})
                if existing and existing["password_hash"]:
                    # Emails are not verified at sign-up, so prove ownership of the existing
                    # Serenity account once before connecting Google to it.
                    password = str(data.get("password", ""))
                    if not password:
                        return self.respond(409, {"error": "You already have a Serenity account with this email. Enter its password once to connect Google.", "link_required": True, "email": profile["email"]})
                    key = f"{self.client_address[0]}|{profile['email']}"
                    if login_blocked(key):
                        return self.respond(429, {"error": "Too many attempts. Wait 15 minutes, then try again."})
                    if not password_matches(existing, password):
                        record_login_failure(key)
                        return self.respond(401, {"error": "That password is incorrect.", "link_required": True, "email": profile["email"]})
                    clear_login_failures(key)
                if existing:
                    connection.execute("UPDATE users SET google_sub=? WHERE id=?", (profile["sub"], existing["id"]))
                    user = existing
                else:
                    user = create_user(connection, profile["email"], profile["name"], google_sub=profile["sub"])
        return self.session({key: user[key] for key in USER_FIELDS})

    def do_GET(self):
        if not self.valid_host(): return
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.respond(200, {"status": "ok", "service": "serenity"})
        if path == '/api/accounts':
            return account_discovery.get(self, db)
        if path.startswith('/api/messages/'):
            return messaging.get(self, db)
        if path in ('/api/map/config', '/api/map/trips', '/api/places/search'):
            return trip_locations.get(self, db)
        if path == visited_locations.PATH:
            return visited_locations.get(self, db)
        if path == "/api/auth/config":
            return self.respond(200, {"google_client_id": None if GUEST_PREVIEW else google_auth.client_id() or None, "password_min": PASSWORD_MIN, "password_max": PASSWORD_MAX, "guest_preview": GUEST_PREVIEW, "guest_message": GUEST_PREVIEW_MESSAGE if GUEST_PREVIEW else None})
        if path == "/api/me":
            user = self.user()
            return self.respond(200, {"user": dict(user) if user else None})
        profile_match = re.fullmatch(r"/api/profiles/([a-z0-9_]{3,24}|[0-9a-f]{16})", path)
        if profile_match:
            profile = social.public_profile(db, profile_match.group(1))
            if not profile:
                return self.respond(404, {"error": "Profile not found."}, {"Cache-Control": "public, max-age=30"})
            return self.respond(200, {"profile": profile}, {"Cache-Control": "no-store"})
        if path == "/api/posts" or social.POST_ID.fullmatch(path):
            result = social.get(self, db, UPLOADS)
            return self.respond(404, {"error": "Not found."}) if result is False else result
        if path == "/api/clips":
            user = self.require_user()
            if not user: return
            feed = urlparse(self.path).query
            match = re.fullmatch(r"feed=([1-9]\d{0,17})", feed) if feed else None
            if feed and not match: return self.respond(400, {"error": "Invalid feed."})
            with db() as connection:
                if match:
                    rows = connection.execute("""SELECT c.id, c.original_name, c.mime, c.size, c.created_at, c.feed_id,
                        EXISTS(SELECT 1 FROM posts p WHERE p.clip_id=c.id AND p.is_public=1) AS is_published
                        FROM clips c WHERE c.user_id=? AND c.feed_id=? ORDER BY c.created_at, c.rowid""", (user["id"], int(match.group(1)))).fetchall()
                else:
                    rows = connection.execute("""SELECT c.id, c.original_name, c.mime, c.size, c.created_at, c.feed_id,
                        EXISTS(SELECT 1 FROM posts p WHERE p.clip_id=c.id AND p.is_public=1) AS is_published
                        FROM clips c WHERE c.user_id=? ORDER BY c.created_at, c.rowid""", (user["id"],)).fetchall()
            return self.respond(200, {"clips": [dict(row) for row in rows]})
        if path == "/api/feeds":
            user = self.require_user()
            if not user: return
            with db() as connection:
                rows = connection.execute("SELECT id, name FROM user_feeds WHERE user_id=? ORDER BY id", (user["id"],)).fetchall()
            return self.respond(200, {"feeds": {str(row["id"]): row["name"] for row in rows}})
        public_feed = re.fullmatch(r"/api/public-feeds/([1-9]\d{0,17})", path)
        if public_feed:
            with db() as connection:
                row = connection.execute("""SELECT f.id, f.name, u.name AS creator_name
                    FROM user_feeds f JOIN users u ON u.id=f.user_id
                    WHERE f.id=? AND EXISTS(SELECT 1 FROM posts p JOIN clips c ON c.id=p.clip_id WHERE c.feed_id=f.id AND p.is_public=1)""",
                    (int(public_feed.group(1)),)).fetchone()
            return self.respond(200, {"feed": dict(row) if row else None})
        note_feed = re.fullmatch(r"/api/feeds/([1-9]\d{0,17})/notes", path)
        if note_feed:
            user = self.require_user()
            if not user: return
            with db() as connection:
                if not connection.execute("SELECT 1 FROM user_feeds WHERE id=? AND user_id=?", (int(note_feed.group(1)), user["id"])).fetchone():
                    return self.respond(404, {"error": "Trip not found."})
                rows = connection.execute("SELECT id, body, created_at FROM feed_notes WHERE user_id=? AND feed_id=? ORDER BY id", (user["id"], int(note_feed.group(1)))).fetchall()
            return self.respond(200, {"notes": [dict(row) for row in rows]})
        detail_feed = re.fullmatch(r"/api/feeds/([1-9]\d{0,17})/details", path)
        if detail_feed:
            user = self.require_user()
            if not user: return
            with db() as connection:
                if not connection.execute("SELECT 1 FROM user_feeds WHERE id=? AND user_id=?", (int(detail_feed.group(1)), user["id"])).fetchone():
                    return self.respond(404, {"error": "Trip not found."})
                row = connection.execute("SELECT destination, summary, updated_at FROM feed_details WHERE user_id=? AND feed_id=?", (user["id"], int(detail_feed.group(1)))).fetchone()
                location = trip_locations.location(connection, int(detail_feed.group(1)))
            return self.respond(200, {"details": {**(dict(row) if row else {"destination": "", "summary": "", "updated_at": None}), "location": location}})
        if path == "/api/theme":
            user = self.require_user()
            if not user: return
            with db() as connection:
                row = connection.execute("SELECT accent, soft, paper, ink, energy FROM themes WHERE user_id=?", (user["id"],)).fetchone()
            return self.respond(200, {"theme": dict(row) if row else None})
        if path.startswith("/api/clips/") and path.endswith("/video"):
            user = self.require_user()
            if not user: return
            clip_id = path.split("/")[3]
            with db() as connection:
                clip = connection.execute("SELECT mime FROM clips WHERE id=? AND user_id=?", (clip_id, user["id"])).fetchone()
            if not clip: return self.respond(404, {"error": "Clip not found."})
            video = UPLOADS / clip_id
            if not video.is_file(): return self.respond(404, {"error": "Clip file is missing."})
            video_stream.send(self, video, clip["mime"], "private, no-store")
            return
        filename = STATIC.get(path)
        if not filename: return self.respond(404, {"error": "Not found."})
        file = ROOT / filename
        data = file.read_bytes()
        self.send_response(200)
        content_type = "application/manifest+json" if filename.endswith(".webmanifest") else mimetypes.guess_type(filename)[0] or "application/octet-stream"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if not self.same_origin(): return
        if self.guest_preview_blocks_write(): return
        path = urlparse(self.path).path
        if path.startswith('/api/messages/'):
            return messaging.post(self, db)
        if path == '/api/studio/import':
            return studio_import.create(self, db)
        if path == "/api/posts" or social.POST_ID.fullmatch(path):
            result = social.post(self, db)
            return self.respond(404, {"error": "Not found."}) if result is False else result
        try:
            if path == "/api/register":
                data = self.json_body()
                email = str(data.get("email", "")).strip().lower()
                name = str(data.get("name", "")).strip()
                password = str(data.get("password", ""))
                if not EMAIL.fullmatch(email) or len(email) > 254 or not 1 <= len(name) <= 80 or not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
                    raise ValueError(f"Enter a name, valid email, and a password of at least {PASSWORD_MIN} characters.")
                try:
                    with db() as connection:
                        user = create_user(connection, email, name, password=password)
                except sqlite3.IntegrityError:
                    return self.respond(409, {"error": "An account with this email already exists. Sign in instead."})
                return self.session(user)
            if path == "/api/login":
                data = self.json_body()
                email = str(data.get("email", "")).strip().lower()
                password = str(data.get("password", ""))
                key = f"{self.client_address[0]}|{email}"
                if login_blocked(key):
                    return self.respond(429, {"error": "Too many sign-in attempts. Wait 15 minutes, then try again."})
                with db() as connection:
                    user = connection.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                if user and not user["password_hash"] and user["google_sub"]:
                    return self.respond(401, {"error": "This account signs in with Google. Use Continue with Google.", "google_only": True})
                if not user or not password_matches(user, password):
                    record_login_failure(key)
                    return self.respond(401, {"error": "Email or password is incorrect."})
                clear_login_failures(key)
                return self.session({key: user[key] for key in USER_FIELDS})
            if path == "/api/auth/google":
                return self.google_sign_in()
            if path == "/api/logout":
                digest = self.session_digest()
                if digest:
                    with db() as connection: connection.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))
                return self.respond(200, {"ok": True}, {"Set-Cookie": session_cookie("", 0)})
            if path == "/api/logout-all":
                user = self.require_user()
                if not user: return
                with db() as connection: connection.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
                return self.respond(200, {"ok": True}, {"Set-Cookie": session_cookie("", 0)})
            if path == "/api/feeds":
                user = self.require_user()
                if not user: return
                name = self.json_body().get("name")
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
                    raise ValueError("Feed name must be 1 to 60 characters.")
                with db() as connection:
                    cursor = connection.execute("INSERT INTO user_feeds(user_id,name,created_at) VALUES (?,?,?)", (user["id"], name.strip(), int(time.time())))
                return self.respond(201, {"feed": {"id": cursor.lastrowid, "name": name.strip()}})
            if path == "/api/clips":
                user = self.require_user()
                if not user: return
                mime = self.headers.get("Content-Type", "").split(";")[0].lower()
                if mime not in VIDEO_TYPES: return self.respond(415, {"error": "Use MP4, WebM, MOV, or M4V video."})
                filename = self.headers.get("X-Filename", "video")
                if self.headers.get('X-Filename-Encoded') == '1': filename = unquote(filename)
                filename = filename[:160]
                filename = Path(filename).name.replace("\\", "_")
                feed_header = self.headers.get("X-Feed", "")
                if feed_header and not re.fullmatch(r"[1-9]\d{0,17}", feed_header):
                    return self.respond(400, {"error": "Invalid feed."})
                feed_id = int(feed_header) if feed_header else None
                upload_key = self.headers.get('X-Upload-Key', '')
                if upload_key and not re.fullmatch(r'[a-zA-Z0-9-]{16,140}', upload_key):
                    return self.respond(400, {'error': 'Invalid upload key.'})
                data = self.body(MAX_VIDEO)
                clip_id = secrets.token_hex(16)
                target = UPLOADS / clip_id
                created_file = False
                try:
                    with db() as connection:
                        # Serialize the receipt and capacity checks, including simultaneous retries.
                        # Read the network body first so slow uploads never hold the database lock.
                        connection.execute('BEGIN IMMEDIATE')
                        if upload_key:
                            saved = connection.execute('SELECT c.id,c.original_name,c.mime,c.size,c.feed_id FROM upload_receipts r JOIN clips c ON c.id=r.clip_id WHERE r.user_id=? AND r.upload_key=?', (user['id'], upload_key)).fetchone()
                            if saved:
                                if saved['feed_id'] != feed_id:
                                    return self.respond(409, {'error': 'This upload was already saved to a different trip.'})
                                return self.respond(200, {'clip': dict(saved)})
                        if feed_id is not None and not connection.execute("SELECT 1 FROM user_feeds WHERE id=? AND user_id=?", (feed_id, user["id"])).fetchone():
                            return self.respond(404, {"error": "Trip not found."})
                        count = connection.execute("SELECT COUNT(*) FROM clips WHERE user_id=? AND feed_id IS ?", (user["id"], feed_id)).fetchone()[0]
                        if count >= MAX_CLIPS_PER_FEED: return self.respond(409, {"error": f"This trip has reached the {MAX_CLIPS_PER_FEED}-video limit."})
                        with target.open("xb") as output:
                            created_file = True
                            output.write(data)
                        os.chmod(target, 0o600)
                        connection.execute("INSERT INTO clips(id,user_id,original_name,mime,size,created_at,feed_id) VALUES (?,?,?,?,?,?,?)", (clip_id, user["id"], filename, mime, len(data), int(time.time()), feed_id))
                        if upload_key:
                            connection.execute('INSERT INTO upload_receipts VALUES (?,?,?)', (user['id'], upload_key, clip_id))
                except Exception:
                    if created_file: target.unlink(missing_ok=True)
                    raise
                return self.respond(201, {"clip": {"id": clip_id, "original_name": filename, "mime": mime, "size": len(data), "feed_id": feed_id}})
            note_feed = re.fullmatch(r"/api/feeds/([1-9]\d{0,17})/notes", path)
            if note_feed:
                user = self.require_user()
                if not user: return
                note = str(self.json_body().get("body", "")).strip()
                if not 1 <= len(note) <= 1000: raise ValueError("Note must be 1 to 1000 characters.")
                with db() as connection:
                    if not connection.execute("SELECT 1 FROM user_feeds WHERE id=? AND user_id=?", (int(note_feed.group(1)), user["id"])).fetchone():
                        return self.respond(404, {"error": "Trip not found."})
                    cursor = connection.execute("INSERT INTO feed_notes(user_id,feed_id,body,created_at) VALUES (?,?,?,?)", (user["id"], int(note_feed.group(1)), note, int(time.time())))
                return self.respond(201, {"note": {"id": cursor.lastrowid, "body": note}})
        except ValueError as error:
            return self.respond(400, {"error": str(error)})
        return self.respond(404, {"error": "Not found."})

    def do_PUT(self):
        if not self.same_origin(): return
        if self.guest_preview_blocks_write(): return
        path = urlparse(self.path).path
        if path == visited_locations.PATH:
            return visited_locations.put(self, db)
        visibility_feed = re.fullmatch(r'/api/feeds/([1-9]\d{0,17})/visibility', path)
        if visibility_feed:
            return trip_visibility.update(self, db, int(visibility_feed.group(1)))
        if path == "/api/profile":
            user = self.require_user()
            if not user: return
            try:
                data = self.json_body()
                name = data.get("name")
                username = data.get("username")
                bio = data.get("bio")
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
                    raise ValueError("Display name must be 1 to 80 characters.")
                if not isinstance(username, str) or not re.fullmatch(r"[a-z0-9_]{3,24}", username.strip().lower()):
                    raise ValueError("Username must be 3 to 24 characters using lowercase letters, numbers, and underscores.")
                if not isinstance(bio, str) or len(bio.strip()) > 240:
                    raise ValueError("Profile bio must be 240 characters or fewer.")
                name, username, bio = name.strip(), username.strip().lower(), bio.strip()
                with db() as connection:
                    connection.execute("UPDATE users SET name=?, username=?, bio=? WHERE id=?", (name, username, bio, user["id"]))
                    profile = connection.execute("SELECT id, public_id, username, email, name, bio FROM users WHERE id=?", (user["id"],)).fetchone()
                return self.respond(200, {"user": dict(profile)})
            except sqlite3.IntegrityError:
                return self.respond(409, {"error": "That username is already taken."})
            except ValueError as error:
                return self.respond(400, {"error": str(error)})
        name_feed = re.fullmatch(r"/api/feeds/([1-9]\d{0,17})/name", path)
        if name_feed:
            user = self.require_user()
            if not user: return
            try:
                name = self.json_body().get("name")
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
                    raise ValueError("Feed name must be 1 to 60 characters.")
                name = name.strip()
                with db() as connection:
                    cursor = connection.execute("UPDATE user_feeds SET name=? WHERE id=? AND user_id=?", (name, int(name_feed.group(1)), user["id"]))
                    if not cursor.rowcount: return self.respond(404, {"error": "Trip not found."})
                return self.respond(200, {"name": name})
            except ValueError as error:
                return self.respond(400, {"error": str(error)})
        detail_feed = re.fullmatch(r"/api/feeds/([1-9]\d{0,17})/details", path)
        if detail_feed:
            user = self.require_user()
            if not user: return
            try:
                data = self.json_body()
                limits = {"destination": 120, "summary": 1000}
                if any(key not in data or not isinstance(data[key], str) or len(data[key].strip()) > limit for key, limit in limits.items()):
                    raise ValueError("Trip details are missing or too long.")
                details = {key: data[key].strip() for key in limits}
                location = trip_locations.normalize(data.get('location')) if 'location' in data else None
                updated_at = int(time.time())
                with db() as connection:
                    connection.execute('BEGIN IMMEDIATE')
                    if not connection.execute("SELECT 1 FROM user_feeds WHERE id=? AND user_id=?", (int(detail_feed.group(1)), user["id"])).fetchone():
                        return self.respond(404, {"error": "Trip not found."})
                    if 'location' not in data:
                        location = trip_locations.location(connection, int(detail_feed.group(1)))
                    if location:
                        details['destination'] = location['label'][:120]
                    connection.execute("""INSERT INTO feed_details(user_id,feed_id,destination,dates,summary,highlights,updated_at)
                        VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_id,feed_id) DO UPDATE SET
                        destination=excluded.destination, dates=excluded.dates, summary=excluded.summary,
                        highlights=excluded.highlights, updated_at=excluded.updated_at""",
                        (user["id"], int(detail_feed.group(1)), details["destination"], '', details["summary"], '', updated_at))
                    trip_locations.save(connection, user['id'], int(detail_feed.group(1)), location)
                    connection.execute('UPDATE posts SET destination=? WHERE clip_id IN (SELECT id FROM clips WHERE feed_id=? AND user_id=?) AND user_id=?', (details['destination'] or 'Location not specified', int(detail_feed.group(1)), user['id'], user['id']))
                return self.respond(200, {"details": {**details, "location": location, "updated_at": updated_at}})
            except ValueError as error:
                return self.respond(400, {"error": str(error)})
        assign = re.fullmatch(r"/api/clips/([0-9a-f]{32})/feed", path)
        if assign:
            user = self.require_user()
            if not user: return
            try:
                feed = self.json_body().get("feed_id")
                if feed is not None and (type(feed) is not int or feed < 1):
                    raise ValueError("Choose a valid trip.")
                with db() as connection:
                    if feed is not None:
                        if not connection.execute("SELECT 1 FROM user_feeds WHERE id=? AND user_id=?", (feed, user["id"])).fetchone():
                            return self.respond(404, {"error": "Trip not found."})
                        count = connection.execute("SELECT COUNT(*) FROM clips WHERE user_id=? AND feed_id=? AND id<>?", (user["id"], feed, assign.group(1))).fetchone()[0]
                        if count >= MAX_CLIPS_PER_FEED: return self.respond(409, {"error": f"This trip has reached the {MAX_CLIPS_PER_FEED}-video limit."})
                    cursor = connection.execute("UPDATE clips SET feed_id=? WHERE id=? AND user_id=?", (feed, assign.group(1), user["id"]))
                if not cursor.rowcount: return self.respond(404, {"error": "Clip not found."})
                return self.respond(200, {"feed_id": feed})
            except ValueError as error:
                return self.respond(400, {"error": str(error)})
        if path != "/api/theme": return self.respond(404, {"error": "Not found."})
        user = self.require_user()
        if not user: return
        try:
            theme = self.json_body()
            if not all(HEX.fullmatch(str(theme.get(key, ""))) for key in ("accent", "soft", "paper", "ink")) or type(theme.get("energy")) is not int or not 0 <= theme["energy"] <= 100:
                raise ValueError("Invalid theme.")
            with db() as connection:
                connection.execute("INSERT INTO themes VALUES (?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET accent=excluded.accent, soft=excluded.soft, paper=excluded.paper, ink=excluded.ink, energy=excluded.energy", (user["id"], theme["accent"], theme["soft"], theme["paper"], theme["ink"], theme["energy"]))
            return self.respond(200, {"theme": theme})
        except ValueError as error:
            return self.respond(400, {"error": str(error)})

    def do_DELETE(self):
        if not self.same_origin(): return
        if self.guest_preview_blocks_write(): return
        visit_match = visited_locations.VISIT_PATH.fullmatch(urlparse(self.path).path)
        if visit_match:
            return visited_locations.delete(self, db, int(visit_match.group(1)))
        user = self.require_user()
        if not user: return
        path = urlparse(self.path).path
        if social.POST_ID.fullmatch(path):
            result = social.delete(self, db)
            return self.respond(404, {"error": "Not found."}) if result is False else result
        if not path.startswith("/api/clips/"): return self.respond(404, {"error": "Not found."})
        clip_id = path.split("/")[3]
        with db() as connection:
            cursor = connection.execute("DELETE FROM clips WHERE id=? AND user_id=?", (clip_id, user["id"]))
        if not cursor.rowcount: return self.respond(404, {"error": "Clip not found."})
        (UPLOADS / clip_id).unlink(missing_ok=True)
        return self.respond(200, {"ok": True})


if __name__ == "__main__":
    init()
    print(f"Serenity listening on {HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
