"""Account-to-account messaging. No public routes, external services, or private trip notes."""
import json
import re
import secrets
import time
from urllib.parse import parse_qs, urlparse

PUBLIC_ID = re.compile(r"[0-9a-f]{16}")
THREAD_ROUTE = re.compile(r"/api/messages/with/([0-9a-f]{16})")
ACTION_ROUTE = re.compile(r"/api/messages/([0-9a-f]{32})/(read|block)")
PAGE_SIZE = 40


def init(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS dm_threads (
      id TEXT PRIMARY KEY,
      user_low INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      user_high INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      read_low INTEGER NOT NULL DEFAULT 0, read_high INTEGER NOT NULL DEFAULT 0,
      blocked_low INTEGER NOT NULL DEFAULT 0, blocked_high INTEGER NOT NULL DEFAULT 0,
      last_message_id INTEGER NOT NULL DEFAULT 0,
      UNIQUE(user_low, user_high), CHECK(user_low < user_high)
    );
    CREATE TABLE IF NOT EXISTS dm_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      thread_id TEXT NOT NULL REFERENCES dm_threads(id) ON DELETE CASCADE,
      sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      body TEXT NOT NULL, client_key TEXT NOT NULL,
      post_id TEXT REFERENCES posts(id) ON DELETE SET NULL,
      has_context INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL,
      UNIQUE(sender_id, client_key)
    );
    CREATE INDEX IF NOT EXISTS dm_thread_messages ON dm_messages(thread_id, id);
    CREATE INDEX IF NOT EXISTS dm_sender_rate ON dm_messages(sender_id, created_at);
    CREATE INDEX IF NOT EXISTS dm_low_inbox ON dm_threads(user_low, last_message_id DESC);
    CREATE INDEX IF NOT EXISTS dm_high_inbox ON dm_threads(user_high, last_message_id DESC);
    """)


def person(row):
    return {key: row[key] for key in ('public_id', 'username', 'name')}


def public_context(connection, post_id):
    # Hiding/deleting a video revokes its attachment, including in an existing conversation.
    row = connection.execute("""SELECT p.id, p.destination, c.feed_id, f.name AS trip_name
        FROM posts p JOIN clips c ON c.id=p.clip_id LEFT JOIN user_feeds f ON f.id=c.feed_id
        WHERE p.id=? AND p.is_public=1""", (post_id,)).fetchone()
    return dict(row) if row else None


def message(connection, row, viewer):
    return {'id': row['id'], 'body': row['body'], 'created_at': row['created_at'],
            'is_mine': row['sender_id'] == viewer, 'has_context': bool(row['has_context']),
            'context': public_context(connection, row['post_id']) if row['has_context'] else None}


def thread_data(connection, row, viewer):
    side = 'low' if row['user_low'] == viewer else 'high'
    other = 'high' if side == 'low' else 'low'
    peer = connection.execute('SELECT public_id,username,name FROM users WHERE id=?', (row[f'user_{other}'],)).fetchone()
    unread = connection.execute('SELECT COUNT(*) FROM dm_messages WHERE thread_id=? AND sender_id<>? AND id>?',
                                (row['id'], viewer, row[f'read_{side}'])).fetchone()[0]
    return {'id': row['id'], 'participant': person(peer), 'unread_count': unread,
            'blocked': bool(row[f'blocked_{side}']),
            'can_send': not (row['blocked_low'] or row['blocked_high'])}


def cursor(query, name):
    value = query.get(name, ['0'])[0]
    if not re.fullmatch(r'\d{1,18}', value):
        raise ValueError('Invalid message cursor.')
    return int(value)


def get(handler, db):
    user = handler.require_user()
    if not user:
        return
    parsed = urlparse(handler.path)
    query = parse_qs(parsed.query)
    try:
        with db() as connection:
            if parsed.path == '/api/messages/users':
                term = query.get('q', [''])[0].strip().lstrip('@').lower()
                if not re.fullmatch(r'[a-z0-9_]{2,24}', term):
                    raise ValueError('Enter at least two username characters (letters, numbers, or underscores).')
                escaped = term.replace('_', '\\_') + '%'
                rows = connection.execute("""SELECT public_id,username,name FROM users
                    WHERE id<>? AND username LIKE ? ESCAPE '\\' ORDER BY username LIMIT 20""", (user['id'], escaped)).fetchall()
                return handler.respond(200, {'users': [person(row) for row in rows]})
            if parsed.path == '/api/messages/inbox':
                before = cursor(query, 'before')
                rows = connection.execute("""SELECT * FROM dm_threads
                    WHERE (user_low=? OR user_high=?) AND last_message_id>0 AND (?=0 OR last_message_id<?)
                    ORDER BY last_message_id DESC LIMIT ?""", (user['id'], user['id'], before, before, PAGE_SIZE + 1)).fetchall()
                threads = []
                for row in rows[:PAGE_SIZE]:
                    item = thread_data(connection, row, user['id'])
                    last = connection.execute('SELECT * FROM dm_messages WHERE id=?', (row['last_message_id'],)).fetchone()
                    item['last_message'] = message(connection, last, user['id'])
                    threads.append(item)
                return handler.respond(200, {'threads': threads, 'next_before': rows[PAGE_SIZE - 1]['last_message_id'] if len(rows) > PAGE_SIZE else None})
            match = THREAD_ROUTE.fullmatch(parsed.path)
            if match:
                peer = connection.execute('SELECT id,public_id,username,name FROM users WHERE public_id=?', (match[1],)).fetchone()
                if not peer:
                    return handler.respond(404, {'error': 'Account not found.'})
                if peer['id'] == user['id']:
                    raise ValueError('Choose another account to message.')
                low, high = sorted((user['id'], peer['id']))
                row = connection.execute('SELECT * FROM dm_threads WHERE user_low=? AND user_high=?', (low, high)).fetchone()
                before, after = cursor(query, 'before'), cursor(query, 'after')
                if before and after:
                    raise ValueError('Use one message cursor at a time.')
                if not row:
                    return handler.respond(200, {'participant': person(peer), 'thread': None, 'messages': [], 'has_more': False})
                order = 'ASC' if after else 'DESC'
                rows = connection.execute(f"""SELECT * FROM dm_messages WHERE thread_id=?
                    AND (?=0 OR id<?) AND (?=0 OR id>?) ORDER BY id {order} LIMIT ?""",
                    (row['id'], before, before, after, after, PAGE_SIZE + 1)).fetchall()
                page = rows[:PAGE_SIZE] if after else list(reversed(rows[:PAGE_SIZE]))
                return handler.respond(200, {'participant': person(peer), 'thread': thread_data(connection, row, user['id']),
                                            'messages': [message(connection, item, user['id']) for item in page], 'has_more': len(rows) > PAGE_SIZE})
        return handler.respond(404, {'error': 'Not found.'})
    except ValueError as error:
        return handler.respond(400, {'error': str(error)})


def post(handler, db):
    user = handler.require_user()
    if not user:
        return
    path = urlparse(handler.path).path
    try:
        # Unicode can exceed the usual 8 KiB body limit even at 2,000 characters.
        data = json.loads(handler.body(32768))
        if not isinstance(data, dict):
            raise ValueError('Expected an object.')
        with db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            if path == '/api/messages/send':
                recipient, body, key = data.get('recipient'), data.get('body'), data.get('client_key')
                post_id = data.get('post_id')
                if not isinstance(recipient, str) or not PUBLIC_ID.fullmatch(recipient):
                    raise ValueError('Choose a valid account.')
                if not isinstance(body, str) or not 1 <= len(body.strip()) <= 2000 or '\x00' in body:
                    raise ValueError('Messages must contain 1 to 2,000 characters.')
                if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z0-9-]{16,100}', key):
                    raise ValueError('Invalid message receipt. Reload and try again.')
                if post_id is not None and (not isinstance(post_id, str) or not re.fullmatch(r'[0-9a-f]{32}', post_id)):
                    raise ValueError('Invalid video reference.')
                peer = connection.execute('SELECT id FROM users WHERE public_id=?', (recipient,)).fetchone()
                if not peer:
                    return handler.respond(404, {'error': 'Account not found.'})
                if peer['id'] == user['id']:
                    raise ValueError('Choose another account to message.')
                low, high = sorted((user['id'], peer['id']))
                previous = connection.execute('SELECT * FROM dm_messages WHERE sender_id=? AND client_key=?', (user['id'], key)).fetchone()
                if previous:
                    row = connection.execute('SELECT * FROM dm_threads WHERE id=?', (previous['thread_id'],)).fetchone()
                    if (row['user_low'], row['user_high']) != (low, high) or previous['body'] != body.strip() or previous['post_id'] != post_id:
                        return handler.respond(409, {'error': 'This receipt belongs to a different message.'})
                    return handler.respond(200, {'thread': thread_data(connection, row, user['id']), 'message': message(connection, previous, user['id'])})
                row = connection.execute('SELECT * FROM dm_threads WHERE user_low=? AND user_high=?', (low, high)).fetchone()
                if row and (row['blocked_low'] or row['blocked_high']):
                    return handler.respond(403, {'error': 'Messaging is unavailable for this conversation.'})
                if post_id and not connection.execute('SELECT 1 FROM posts WHERE id=? AND user_id=? AND is_public=1', (post_id, peer['id'])).fetchone():
                    return handler.respond(404, {'error': 'That video is no longer public or does not belong to this creator. Remove the video reference to send a direct message.'})
                now = int(time.time())
                if connection.execute('SELECT COUNT(*) FROM dm_messages WHERE sender_id=? AND created_at>?', (user['id'], now - 60)).fetchone()[0] >= 30:
                    return handler.respond(429, {'error': 'You’re sending messages quickly. Please wait a minute.'})
                if not row:
                    recent = connection.execute('SELECT COUNT(DISTINCT thread_id) FROM dm_messages WHERE sender_id=? AND created_at>?', (user['id'], now - 600)).fetchone()[0]
                    if recent >= 10:
                        return handler.respond(429, {'error': 'Please wait before starting more new conversations.'})
                    thread_id = secrets.token_hex(16)
                    connection.execute('INSERT INTO dm_threads(id,user_low,user_high) VALUES (?,?,?)', (thread_id, low, high))
                else:
                    thread_id = row['id']
                result = connection.execute('''INSERT INTO dm_messages(thread_id,sender_id,body,client_key,post_id,has_context,created_at)
                    VALUES (?,?,?,?,?,?,?)''', (thread_id, user['id'], body.strip(), key, post_id, bool(post_id), now))
                connection.execute('UPDATE dm_threads SET last_message_id=? WHERE id=?', (result.lastrowid, thread_id))
                row = connection.execute('SELECT * FROM dm_threads WHERE id=?', (thread_id,)).fetchone()
                saved = connection.execute('SELECT * FROM dm_messages WHERE id=?', (result.lastrowid,)).fetchone()
                payload = {'thread': thread_data(connection, row, user['id']), 'message': message(connection, saved, user['id'])}
            else:
                match = ACTION_ROUTE.fullmatch(path)
                if not match:
                    return handler.respond(404, {'error': 'Not found.'})
                row = connection.execute('SELECT * FROM dm_threads WHERE id=? AND (user_low=? OR user_high=?)', (match[1], user['id'], user['id'])).fetchone()
                if not row:
                    return handler.respond(404, {'error': 'Conversation not found.'})
                side = 'low' if row['user_low'] == user['id'] else 'high'
                if match[2] == 'read':
                    through = data.get('through')
                    if type(through) is not int or not 0 < through <= 9223372036854775807:
                        raise ValueError('Invalid read position.')
                    if not connection.execute('SELECT 1 FROM dm_messages WHERE id=? AND thread_id=?', (through, row['id'])).fetchone():
                        raise ValueError('Read position is not in this conversation.')
                    connection.execute(f'UPDATE dm_threads SET read_{side}=MAX(read_{side},?) WHERE id=?', (through, row['id']))
                else:
                    if type(data.get('blocked')) is not bool:
                        raise ValueError('Choose block or unblock.')
                    connection.execute(f'UPDATE dm_threads SET blocked_{side}=? WHERE id=?', (data['blocked'], row['id']))
                row = connection.execute('SELECT * FROM dm_threads WHERE id=?', (row['id'],)).fetchone()
                payload = {'thread': thread_data(connection, row, user['id'])}
        # Commit before acknowledging so another account immediately sees the change.
        return handler.respond(201 if path == '/api/messages/send' else 200, payload)
    except (ValueError, UnicodeDecodeError) as error:
        return handler.respond(400, {'error': str(error)})
