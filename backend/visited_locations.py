"""Private, explicitly saved travel history; never part of public trip discovery."""
from datetime import date
import re
import time
from urllib.parse import parse_qs, urlparse

import trip_locations

PATH = '/api/map/visits'
VISIT_PATH = re.compile(r'/api/map/visits/([1-9]\d{0,17})')


def init(connection):
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS visited_locations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      lat REAL NOT NULL, lng REAL NOT NULL, label TEXT NOT NULL,
      provider TEXT NOT NULL, source TEXT NOT NULL, place_id TEXT NOT NULL,
      lat_key INTEGER NOT NULL, lng_key INTEGER NOT NULL,
      visited_on TEXT NOT NULL, note TEXT NOT NULL, saved_at INTEGER NOT NULL,
      UNIQUE(user_id, lat_key, lng_key)
    );
    CREATE INDEX IF NOT EXISTS visits_by_owner ON visited_locations(user_id, saved_at DESC, id DESC);
    ''')


def count(connection, user_id):
    return connection.execute('SELECT COUNT(*) FROM visited_locations WHERE user_id=?', (user_id,)).fetchone()[0]


def serialize(row):
    return {key: row[key] for key in ('id', 'lat', 'lng', 'label', 'provider', 'source', 'place_id', 'visited_on', 'note', 'saved_at')}


def get(handler, db):
    user = handler.require_user()
    if not user:
        return
    query = parse_qs(urlparse(handler.path).query)
    try:
        offset = int(query.get('offset', ['0'])[0])
        if not 0 <= offset <= 1_000_000:
            raise ValueError()
    except (ValueError, TypeError):
        return handler.respond(400, {'error': 'Invalid travel-history offset.'})
    with db() as connection:
        rows = connection.execute('''SELECT * FROM visited_locations WHERE user_id=?
            ORDER BY saved_at DESC, id DESC LIMIT 100 OFFSET ?''', (user['id'], offset)).fetchall()
        total = count(connection, user['id'])
    return handler.respond(200, {'locations': [serialize(row) for row in rows], 'total': total, 'has_more': offset + len(rows) < total})


def put(handler, db):
    user = handler.require_user()
    if not user:
        return
    try:
        data = handler.json_body()
        location = trip_locations.normalize(data.get('location'))
        if location is None:
            raise ValueError('Choose a place before marking it visited.')
        visited_on, note = data.get('visited_on', ''), data.get('note', '')
        if not isinstance(visited_on, str) or (visited_on and (len(visited_on) != 10 or date.fromisoformat(visited_on).isoformat() != visited_on)):
            raise ValueError('Enter a valid visit date (YYYY-MM-DD).')
        if not isinstance(note, str) or len(note) > 1000:
            raise ValueError('Keep travel notes to 1,000 characters.')
        # A saved place represents one coordinate cell (~11 m at the equator).
        # Names/provider IDs are deliberately not used as identity: renaming a
        # pin or saving it from another creator must not inflate the count.
        lat_key = round(location['lat'] * 10000)
        lng_key = round(location['lng'] * 10000)
        if abs(lat_key) == 900000:
            lng_key = 0
        elif lng_key == 1800000:
            lng_key = -1800000
        with db() as connection:
            cursor = connection.execute('''INSERT INTO visited_locations
                (user_id,lat,lng,label,provider,source,place_id,lat_key,lng_key,visited_on,note,saved_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,lat_key,lng_key) DO NOTHING''',
                (user['id'], location['lat'], location['lng'], location['label'], location['provider'], location['source'],
                 location['place_id'], lat_key, lng_key, visited_on, note.strip(), int(time.time())))
            created = cursor.rowcount == 1
            row = connection.execute('SELECT * FROM visited_locations WHERE user_id=? AND lat_key=? AND lng_key=?',
                                     (user['id'], lat_key, lng_key)).fetchone()
            total = count(connection, user['id'])
        return handler.respond(201 if created else 200, {'location': serialize(row), 'total': total, 'created': created})
    except (ValueError, TypeError) as error:
        return handler.respond(400, {'error': str(error)})


def delete(handler, db, visit_id):
    user = handler.require_user()
    if not user:
        return
    with db() as connection:
        cursor = connection.execute('DELETE FROM visited_locations WHERE id=? AND user_id=?', (visit_id, user['id']))
        total = count(connection, user['id'])
    if not cursor.rowcount:
        return handler.respond(404, {'error': 'Saved place not found.'})
    return handler.respond(200, {'ok': True, 'total': total})
