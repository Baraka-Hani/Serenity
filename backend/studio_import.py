"""Atomic, idempotent creation of private trips from a reviewed video collection."""
import hashlib
import json
import re
import time
import trip_locations


def init(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS studio_imports (
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      batch_key TEXT NOT NULL, manifest_hash TEXT NOT NULL, response TEXT NOT NULL,
      created_at INTEGER NOT NULL, PRIMARY KEY(user_id,batch_key)
    );
    CREATE TABLE IF NOT EXISTS upload_receipts (
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      upload_key TEXT NOT NULL, clip_id TEXT NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
      PRIMARY KEY(user_id,upload_key)
    );
    """)


def create(handler, db):
    user = handler.require_user()
    if not user:
        return
    try:
        data = json.loads(handler.body(256 * 1024))
        if not isinstance(data, dict):
            raise ValueError('Invalid import.')
        key, groups = data.get('batch_key'), data.get('groups')
        if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z0-9-]{16,80}', key):
            raise ValueError('Invalid import key.')
        if not isinstance(groups, list) or not 1 <= len(groups) <= 100:
            raise ValueError('An import must contain 1 to 100 trips.')
        cleaned = []
        seen = set()
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError('Invalid trip group.')
            entry = {}
            for field, limit in {'key': 80, 'name': 60, 'destination': 120, 'summary': 1000}.items():
                value = group.get(field, '')
                if not isinstance(value, str) or len(value.strip()) > limit:
                    raise ValueError('Trip details are invalid or too long.')
                entry[field] = value.strip()
            entry['location'] = trip_locations.normalize(group.get('location'))
            if entry['location']:
                entry['destination'] = entry['location']['label'][:120]
            if not entry['name'] or not re.fullmatch(r'[a-zA-Z0-9-]{1,80}', entry['key']) or entry['key'] in seen:
                raise ValueError('Each suggested trip needs a name and a unique group key.')
            seen.add(entry['key'])
            cleaned.append(entry)
        digest = hashlib.sha256(json.dumps(cleaned, sort_keys=True).encode()).hexdigest()
        with db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            previous = connection.execute('SELECT * FROM studio_imports WHERE user_id=? AND batch_key=?', (user['id'], key)).fetchone()
            if previous:
                if previous['manifest_hash'] != digest:
                    return handler.respond(409, {'error': 'This import already started with different groups. Start a new collection to change it.'})
                return handler.respond(200, json.loads(previous['response']))
            created = []
            now = int(time.time())
            for group in cleaned:
                cursor = connection.execute('INSERT INTO user_feeds(user_id,name,created_at) VALUES (?,?,?)', (user['id'], group['name'], now))
                feed_id = cursor.lastrowid
                connection.execute('INSERT INTO feed_details(user_id,feed_id,destination,dates,summary,highlights,updated_at) VALUES (?,?,?,?,?,?,?)', (user['id'], feed_id, group['destination'], '', group['summary'], '', now))
                trip_locations.save(connection, user['id'], feed_id, group['location'])
                created.append({'key': group['key'], 'id': feed_id, 'name': group['name']})
            result = {'groups': created}
            connection.execute('INSERT INTO studio_imports VALUES (?,?,?,?,?)', (user['id'], key, digest, json.dumps(result), now))
        return handler.respond(201, result)
    except (ValueError, UnicodeDecodeError) as error:
        return handler.respond(400, {'error': str(error)})
