"""Public travel posts, kept separate from private clips and trip details."""
import re
import secrets
import time
from urllib.parse import parse_qs, urlparse
import trip_locations


POST_ID = re.compile(r"/api/posts/([0-9a-f]{32})(?:/(video|like|save|comments|context))?")


def post_context(db, post_id):
    """Only published fields may cross this boundary; never read private trip notes/GPS."""
    with db() as connection:
        post = connection.execute("""SELECT p.*, c.feed_id, u.public_id, u.username, u.name
            FROM posts p JOIN clips c ON c.id=p.clip_id JOIN users u ON u.id=p.user_id
            WHERE p.id=? AND p.is_public=1""", (post_id,)).fetchone()
        if not post:
            return None
        location = trip_locations.location(connection, post['feed_id'])
        rows = connection.execute("""SELECT p.id, p.destination, p.created_at, c.feed_id, f.name
            FROM posts p JOIN clips c ON c.id=p.clip_id JOIN user_feeds f ON f.id=c.feed_id
            WHERE p.user_id=? AND c.feed_id<>? AND p.created_at<=? AND p.is_public=1
            ORDER BY p.created_at DESC, p.id DESC""", (post["user_id"], post["feed_id"], post["created_at"])).fetchall()
    trips = {}
    for row in rows:
        trip = trips.setdefault(row["feed_id"], {
            "id": row["feed_id"], "name": row["name"], "destination": row["destination"],
            "preview_post_id": row["id"], "published_at": row["created_at"], "video_count": 0,
            "same_destination": row["destination"].strip().casefold() == post["destination"].strip().casefold(),
        })
        trip["video_count"] += 1
    related = sorted(trips.values(), key=lambda trip: (trip["same_destination"], trip["published_at"]), reverse=True)
    return {
        "post_id": post_id,
        "creator": {"public_id": post["public_id"], "username": post["username"], "name": post["name"]},
        "travel": {"destination": post["destination"], "summary": post["caption"], "tip": post["tip"], "location": location, "feed_id": post['feed_id'],
                   "location_source": "creator", "approximate_location": None,
                   "flights_status": "not_connected", "itinerary_status": "not_connected"},
        "related_trips": related[:12],
    }


def init(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS posts (
      id TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      clip_id TEXT NOT NULL UNIQUE REFERENCES clips(id) ON DELETE CASCADE,
      destination TEXT NOT NULL,
      caption TEXT NOT NULL,
      tip TEXT NOT NULL,
      created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS post_likes (
      post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      PRIMARY KEY (post_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS post_saves (
      post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      PRIMARY KEY (post_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS post_comments (
      id INTEGER PRIMARY KEY,
      post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      body TEXT NOT NULL,
      created_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS posts_recent ON posts(created_at DESC, id DESC);
    CREATE INDEX IF NOT EXISTS comments_by_post ON post_comments(post_id, id);
    """)
    if 'is_public' not in {row[1] for row in connection.execute('PRAGMA table_info(posts)')}:
        connection.execute('ALTER TABLE posts ADD COLUMN is_public INTEGER NOT NULL DEFAULT 1')


def public_profile(db, identifier):
    with db() as connection:
        if re.fullmatch(r"[0-9a-f]{16}", identifier):
            user = connection.execute("""SELECT id, public_id, username, name, bio, is_demo, created_at
                FROM users WHERE public_id=?""", (identifier,)).fetchone()
        else:
            user = connection.execute("""SELECT id, public_id, username, name, bio, is_demo, created_at
                FROM users WHERE username=? COLLATE NOCASE""", (identifier,)).fetchone()
        if not user:
            return None
        rows = connection.execute("""SELECT c.feed_id AS id, f.name, p.id AS post_id,
            p.destination, p.caption, p.tip, p.created_at, c.original_name AS clip_name
            FROM posts p JOIN clips c ON c.id=p.clip_id
            LEFT JOIN user_feeds f ON f.id=c.feed_id
            WHERE p.user_id=? AND p.is_public=1 ORDER BY c.created_at ASC, c.rowid ASC""", (user["id"],)).fetchall()
    trips = {}
    for row in rows:
        trip_id = row["id"]
        trip = trips.setdefault(trip_id, {
            "id": trip_id,
            "name": row["name"] or "Published trip",
            "destination": row["destination"],
            "posts": [],
            "published_at": row["created_at"]
        })
        trip["posts"].append({
            "id": row["post_id"],
            "destination": row["destination"],
            "caption": row["caption"],
            "tip": row["tip"],
            "clip_name": row["clip_name"],
            "created_at": row["created_at"]
        })
        trip["published_at"] = max(trip["published_at"], row["created_at"])
    return {
        "public_id": user["public_id"],
        "username": user["username"],
        "name": user["name"],
        "bio": user["bio"],
        "is_demo": bool(user["is_demo"]),
        "created_at": user["created_at"],
        "trip_count": len(trips),
        "video_count": sum(len(trip["posts"]) for trip in trips.values()),
        "trips": sorted(trips.values(), key=lambda trip: trip["published_at"], reverse=True)
    }


def get(handler, db, uploads):
    parsed = urlparse(handler.path)
    path = parsed.path
    if path == "/api/posts":
        query = parse_qs(parsed.query)
        sort = query.get("sort", ["recent"])[0]
        search = query.get("q", [""])[0].strip()
        feed_value = query.get("feed", [""])[0]
        try:
            feed = int(feed_value) if feed_value else None
        except ValueError:
            feed = -1
        try:
            offset = int(query.get("offset", ["0"])[0])
        except ValueError:
            offset = -1
        if sort not in ("recent", "popular", "saved", "mine") or len(search) > 120 or not 0 <= offset <= 10000 or (feed is not None and not 1 <= feed <= 9223372036854775807):
            return handler.respond(400, {"error": "Invalid feed filter."})
        user = handler.user()
        if sort in ("saved", "mine") and not user:
            return handler.respond(401, {"error": "Sign in to view your posts."})
        viewer = user["id"] if user else -1
        conditions = ['p.is_public=1']
        params = []
        if search:
            conditions.append("(p.destination LIKE ? ESCAPE '\\' OR p.caption LIKE ? ESCAPE '\\')")
            term = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            params.extend((term, term))
        if feed is not None:
            conditions.append("c.feed_id=?")
            params.append(feed)
        if sort == "saved":
            conditions.append("EXISTS (SELECT 1 FROM post_saves s WHERE s.post_id=p.id AND s.user_id=?)")
            params.append(viewer)
        elif sort == "mine":
            conditions.append("p.user_id=?")
            params.append(viewer)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        order = "likes_count DESC, p.created_at DESC, p.id DESC" if sort == "popular" else "p.created_at DESC, p.id DESC"
        with db() as connection:
            rows = connection.execute(f"""SELECT p.id, p.destination, p.caption, p.tip, p.created_at,
                c.feed_id, c.original_name AS clip_name, f.name AS feed_name,
                u.id AS author_id, u.public_id AS author_public_id, u.username AS author_username, u.name AS author_name,
                (SELECT COUNT(*) FROM post_likes l WHERE l.post_id=p.id) AS likes_count,
                (SELECT COUNT(*) FROM post_comments c WHERE c.post_id=p.id) AS comments_count,
                EXISTS(SELECT 1 FROM post_likes l WHERE l.post_id=p.id AND l.user_id=?) AS liked,
                EXISTS(SELECT 1 FROM post_saves s WHERE s.post_id=p.id AND s.user_id=?) AS saved,
                (p.user_id=?) AS is_mine
                FROM posts p JOIN users u ON u.id=p.user_id JOIN clips c ON c.id=p.clip_id
                LEFT JOIN user_feeds f ON f.id=c.feed_id {where}
                ORDER BY {order} LIMIT ? OFFSET ?""", tuple([viewer, viewer, viewer] + params + [21, offset])).fetchall()
            feed_ids = list(dict.fromkeys(row["feed_id"] for row in rows[:20] if row["feed_id"] is not None))
            trip_posts = {}
            if feed_ids:
                placeholders = ",".join("?" for _ in feed_ids)
                trip_rows = connection.execute(f"""SELECT p.id, p.destination, p.caption, p.tip, p.created_at,
                    c.feed_id, c.original_name AS clip_name,
                    (SELECT COUNT(*) FROM post_likes l WHERE l.post_id=p.id) AS likes_count,
                    (SELECT COUNT(*) FROM post_comments cm WHERE cm.post_id=p.id) AS comments_count,
                    EXISTS(SELECT 1 FROM post_likes l WHERE l.post_id=p.id AND l.user_id=?) AS liked,
                    EXISTS(SELECT 1 FROM post_saves s WHERE s.post_id=p.id AND s.user_id=?) AS saved,
                    (p.user_id=?) AS is_mine
                    FROM posts p JOIN clips c ON c.id=p.clip_id
                    WHERE c.feed_id IN ({placeholders}) AND p.is_public=1
                    ORDER BY c.feed_id, c.created_at, c.rowid""",
                    tuple([viewer, viewer, viewer] + feed_ids)).fetchall()
                for trip_post in trip_rows:
                    trip_posts.setdefault(str(trip_post["feed_id"]), []).append(dict(trip_post))
        return handler.respond(200, {
            "posts": [dict(row) for row in rows[:20]],
            "trip_posts": trip_posts,
            "has_more": len(rows) > 20,
        })
    match = POST_ID.fullmatch(path)
    if not match:
        return False
    post_id, action = match.groups()
    if action == "context":
        context = post_context(db, post_id)
        return handler.respond(200, {"context": context}) if context else handler.respond(404, {"error": "Post not found."})
    if action == "comments":
        with db() as connection:
            if not connection.execute("SELECT 1 FROM posts WHERE id=? AND is_public=1", (post_id,)).fetchone():
                return handler.respond(404, {"error": "Post not found."})
            rows = connection.execute("""SELECT c.id, c.body, c.created_at, u.name AS author_name, u.username AS author_username, u.public_id AS author_public_id
                FROM post_comments c JOIN users u ON u.id=c.user_id WHERE c.post_id=? ORDER BY c.id LIMIT 100""", (post_id,)).fetchall()
        return handler.respond(200, {"comments": [dict(row) for row in rows]})
    if action == "video":
        with db() as connection:
            clip = connection.execute("""SELECT c.id, c.mime FROM posts p JOIN clips c ON c.id=p.clip_id
                WHERE p.id=? AND p.is_public=1""", (post_id,)).fetchone()
        if not clip:
            return handler.respond(404, {"error": "Post not found."})
        video = uploads / clip["id"]
        if not video.is_file():
            return handler.respond(404, {"error": "Video is unavailable."})
        size = video.stat().st_size
        range_header = handler.headers.get("Range", "")
        byte_range = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
        start, end = (int(byte_range.group(1)), int(byte_range.group(2)) if byte_range.group(2) else size - 1) if byte_range else (0, size - 1)
        if start >= size or end < start or end >= size:
            return handler.respond(416, {"error": "Invalid video range."})
        handler.send_response(206 if byte_range else 200)
        handler.send_header("Content-Type", clip["mime"])
        handler.send_header("Content-Length", str(end - start + 1))
        handler.send_header("Accept-Ranges", "bytes")
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Content-Type-Options", "nosniff")
        if byte_range:
            handler.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        handler.end_headers()
        with video.open("rb") as source:
            source.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    break
                handler.wfile.write(chunk)
                remaining -= len(chunk)
        return True
    return False


def post(handler, db):
    path = urlparse(handler.path).path
    if path == "/api/posts":
        user = handler.require_user()
        if not user:
            return True
        try:
            data = handler.json_body()
            clip_id = data.get("clip_id")
            destination = data.get("destination")
            caption = data.get("caption")
            tip = data.get("tip", "")
            if not isinstance(clip_id, str) or not re.fullmatch(r"[0-9a-f]{32}", clip_id):
                raise ValueError("Choose a saved clip to publish.")
            if not isinstance(destination, str) or not 1 <= len(destination.strip()) <= 120:
                raise ValueError("Add a destination (up to 120 characters).")
            if not isinstance(caption, str) or not 1 <= len(caption.strip()) <= 1000:
                raise ValueError("Add a caption (up to 1000 characters).")
            if not isinstance(tip, str) or len(tip.strip()) > 500:
                raise ValueError("Travel tip must be 500 characters or less.")
            with db() as connection:
                connection.execute('BEGIN IMMEDIATE')
                clip = connection.execute("SELECT feed_id FROM clips WHERE id=? AND user_id=?", (clip_id, user["id"])).fetchone()
                if not clip:
                    return handler.respond(404, {"error": "Saved clip not found."})
                if clip["feed_id"] is None:
                    raise ValueError("Assign this clip to a trip before publishing so it appears on that trip page.")
                existing = connection.execute("SELECT id,is_public FROM posts WHERE clip_id=?", (clip_id,)).fetchone()
                if existing and existing['is_public']:
                    return handler.respond(409, {"error": "This clip is already published."})
                if existing:
                    post_id = existing['id']
                    connection.execute('UPDATE posts SET is_public=1,destination=?,caption=?,tip=? WHERE id=? AND user_id=?', (destination.strip(), caption.strip(), tip.strip(), post_id, user['id']))
                else:
                    post_id = secrets.token_hex(16)
                    connection.execute("INSERT INTO posts(id,user_id,clip_id,destination,caption,tip,created_at) VALUES (?,?,?,?,?,?,?)", (post_id, user["id"], clip_id, destination.strip(), caption.strip(), tip.strip(), int(time.time())))
            return handler.respond(201, {"post": {"id": post_id}})
        except ValueError as error:
            return handler.respond(400, {"error": str(error)})
    match = POST_ID.fullmatch(path)
    if not match or match.group(2) not in ("like", "save", "comments"):
        return False
    user = handler.require_user()
    if not user:
        return True
    post_id, action = match.groups()
    with db() as connection:
        connection.execute('BEGIN IMMEDIATE')
        if not connection.execute("SELECT 1 FROM posts WHERE id=? AND is_public=1", (post_id,)).fetchone():
            return handler.respond(404, {"error": "Post not found."})
        if action in ("like", "save"):
            table = "post_likes" if action == "like" else "post_saves"
            existing = connection.execute(f"SELECT 1 FROM {table} WHERE post_id=? AND user_id=?", (post_id, user["id"])).fetchone()
            if existing:
                connection.execute(f"DELETE FROM {table} WHERE post_id=? AND user_id=?", (post_id, user["id"]))
            else:
                connection.execute(f"INSERT INTO {table}(post_id,user_id) VALUES (?,?)", (post_id, user["id"]))
            count = connection.execute(f"SELECT COUNT(*) FROM {table} WHERE post_id=?", (post_id,)).fetchone()[0]
            return handler.respond(200, {"active": not bool(existing), "count": count})
        try:
            body = handler.json_body().get("body")
            if not isinstance(body, str) or not 1 <= len(body.strip()) <= 500:
                raise ValueError("Comment must be 1 to 500 characters.")
            cursor = connection.execute("INSERT INTO post_comments(post_id,user_id,body,created_at) VALUES (?,?,?,?)", (post_id, user["id"], body.strip(), int(time.time())))
            return handler.respond(201, {"comment": {"id": cursor.lastrowid, "body": body.strip(), "author_name": user["name"], "author_public_id": user["public_id"], "author_username": user["username"]}})
        except ValueError as error:
            return handler.respond(400, {"error": str(error)})


def delete(handler, db):
    match = POST_ID.fullmatch(urlparse(handler.path).path)
    if not match or match.group(2):
        return False
    user = handler.require_user()
    if not user:
        return True
    with db() as connection:
        cursor = connection.execute("DELETE FROM posts WHERE id=? AND user_id=?", (match.group(1), user["id"]))
    if not cursor.rowcount:
        return handler.respond(404, {"error": "Post not found."})
    return handler.respond(200, {"ok": True})
