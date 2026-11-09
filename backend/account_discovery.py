"""Public-profile account discovery, with authenticated access and no email lookup."""
from urllib.parse import parse_qs, urlparse

PAGE_SIZE = 12


def init(connection):
    if 'is_demo' not in {row[1] for row in connection.execute('PRAGMA table_info(users)')}:
        connection.execute('ALTER TABLE users ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0')


def find(connection, viewer, query='', offset=0):
    term = query.strip().lstrip('@')
    if len(term) > 80 or '\x00' in term or len(term) == 1:
        raise ValueError('Use at least two characters to search by name, username, or destination.')
    if not 0 <= offset <= 10000:
        raise ValueError('Invalid directory page.')
    escaped = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    contains, prefix = '%' + escaped + '%', escaped + '%'
    rows = connection.execute("""SELECT u.public_id,u.username,u.name,u.bio,u.is_demo,
        COUNT(p.id) AS video_count, COUNT(DISTINCT c.feed_id) AS trip_count,
        MAX(p.created_at) AS published_at,
        (SELECT destination FROM posts WHERE user_id=u.id AND is_public=1 ORDER BY created_at DESC,id DESC LIMIT 1) AS destination,
        (SELECT id FROM posts WHERE user_id=u.id AND is_public=1 ORDER BY created_at DESC,id DESC LIMIT 1) AS preview_post_id
        FROM users u LEFT JOIN posts p ON p.user_id=u.id AND p.is_public=1
        LEFT JOIN clips c ON c.id=p.clip_id
        WHERE u.id<>? AND NOT EXISTS(SELECT 1 FROM dm_threads d
            WHERE ((d.user_low=? AND d.user_high=u.id) OR (d.user_high=? AND d.user_low=u.id))
            AND (d.blocked_low=1 OR d.blocked_high=1))
        AND ((?='' AND EXISTS(SELECT 1 FROM posts WHERE user_id=u.id AND is_public=1))
          OR (?<>'' AND (u.username LIKE ? ESCAPE '\\' OR u.name LIKE ? ESCAPE '\\'
            OR EXISTS(SELECT 1 FROM posts WHERE user_id=u.id AND is_public=1 AND destination LIKE ? ESCAPE '\\'))))
        GROUP BY u.id ORDER BY
          CASE WHEN u.username=? COLLATE NOCASE THEN 0 WHEN u.username LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,
          published_at DESC, u.username COLLATE NOCASE, u.public_id LIMIT ? OFFSET ?""",
        (viewer, viewer, viewer, term, term, contains, contains, contains, term, prefix, PAGE_SIZE+1, offset)).fetchall()
    return {'accounts': [dict(row) for row in rows[:PAGE_SIZE]], 'has_more': len(rows) > PAGE_SIZE,
            'next_offset': offset+PAGE_SIZE if len(rows) > PAGE_SIZE else None}


def get(handler, db):
    user = handler.require_user()
    if not user:
        return
    query = parse_qs(urlparse(handler.path).query)
    try:
        offset = int(query.get('offset', ['0'])[0])
        with db() as connection:
            result = find(connection, user['id'], query.get('q', [''])[0], offset)
        return handler.respond(200, result)
    except ValueError as error:
        return handler.respond(400, {'error': str(error)})
