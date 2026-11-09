"""Saved destination pins, public trip discovery, and low-volume place search."""
import hashlib
import html
import json
import math
import os
import threading
import time
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

SEARCH_URL = os.environ.get('SERENITY_PHOTON_URL', 'https://photon.komoot.io/api/')
TILE_URL = os.environ.get('SERENITY_MAP_TILE_URL', 'https://tile.openstreetmap.org/{z}/{x}/{y}.png')
SEARCH_LOCK = threading.Lock()
LAST_SEARCH = 0.0


def init(connection):
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS trip_locations (
      feed_id INTEGER PRIMARY KEY REFERENCES user_feeds(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      lat REAL NOT NULL, lng REAL NOT NULL, label TEXT NOT NULL,
      provider TEXT NOT NULL, place_id TEXT NOT NULL, source TEXT NOT NULL,
      updated_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS trip_location_bounds ON trip_locations(lat,lng);
    CREATE TABLE IF NOT EXISTS place_search_cache (
      cache_key TEXT PRIMARY KEY, results TEXT NOT NULL, expires_at INTEGER NOT NULL
    );
    ''')


def normalize(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError('Choose a destination pin on the map.')
    for key, low, high in (('lat', -90, 90), ('lng', -180, 180)):
        number = value.get(key)
        if type(number) not in (int, float) or not math.isfinite(number) or not low <= number <= high:
            raise ValueError('Destination coordinates are invalid.')
    label = value.get('label')
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 240:
        raise ValueError('Give the destination a place name (up to 240 characters).')
    provider, source, place_id = value.get('provider', 'manual'), value.get('source', 'pin'), value.get('place_id', '')
    if provider not in ('manual', 'photon') or source not in ('pin', 'place') or not isinstance(place_id, str) or len(place_id) > 120:
        raise ValueError('Invalid destination reference.')
    return {'lat': round(value['lat'], 7), 'lng': round(value['lng'], 7), 'label': label.strip(),
            'provider': provider, 'source': source, 'place_id': place_id}


def location(connection, feed_id):
    row = connection.execute('SELECT lat,lng,label,provider,source,place_id FROM trip_locations WHERE feed_id=?', (feed_id,)).fetchone()
    return dict(row) if row else None


def save(connection, user_id, feed_id, value):
    if value is None:
        connection.execute('DELETE FROM trip_locations WHERE feed_id=? AND user_id=?', (feed_id, user_id))
    else:
        connection.execute('''INSERT INTO trip_locations(feed_id,user_id,lat,lng,label,provider,place_id,source,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(feed_id) DO UPDATE SET lat=excluded.lat,lng=excluded.lng,
            label=excluded.label,provider=excluded.provider,place_id=excluded.place_id,source=excluded.source,updated_at=excluded.updated_at''',
            (feed_id, user_id, value['lat'], value['lng'], value['label'], value['provider'], value['place_id'], value['source'], int(time.time())))


def public_trips(connection, query):
    where, args = ['p.is_public=1'], []
    search = query.get('q', [''])[0].strip()
    if len(search) > 120:
        raise ValueError('Search must be 120 characters or fewer.')
    if search:
        term = '%' + search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        where.append("(f.name LIKE ? ESCAPE '\\' OR l.label LIKE ? ESCAPE '\\' OR EXISTS (SELECT 1 FROM posts ps JOIN clips cs ON cs.id=ps.clip_id WHERE cs.feed_id=f.id AND ps.is_public=1 AND ps.caption LIKE ? ESCAPE '\\'))")
        args.extend([term] * 3)
    if query.get('trip'):
        value = query['trip'][0]
        if not value.isdigit() or not 1 <= int(value) <= 9223372036854775807:
            raise ValueError('Invalid trip.')
        where.append('f.id=?'); args.append(int(value))
    if query.get('bbox'):
        try:
            west, south, east, north = [float(item) for item in query['bbox'][0].split(',')]
        except (ValueError, TypeError):
            raise ValueError('Invalid map bounds.')
        if not all(math.isfinite(x) for x in (west, south, east, north)) or not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError('Invalid map bounds.')
        where.append('l.lat BETWEEN ? AND ?'); args.extend([south, north])
        where.append('(l.lng>=? OR l.lng<=?)' if west > east else 'l.lng BETWEEN ? AND ?')
        args.extend([west, east])
    rows = connection.execute(f'''SELECT f.id,f.name,l.lat,l.lng,l.label,l.source,
        u.name AS creator_name,u.username AS creator_username,u.public_id AS creator_public_id,
        COUNT(p.id) AS video_count,MAX(p.created_at) AS published_at,
        (SELECT p2.id FROM posts p2 JOIN clips c2 ON c2.id=p2.clip_id
          WHERE c2.feed_id=f.id AND p2.is_public=1 ORDER BY c2.created_at,c2.rowid LIMIT 1) AS preview_post_id,
        (SELECT p3.caption FROM posts p3 JOIN clips c3 ON c3.id=p3.clip_id
          WHERE c3.feed_id=f.id AND p3.is_public=1 ORDER BY c3.created_at,c3.rowid LIMIT 1) AS summary
        FROM trip_locations l JOIN user_feeds f ON f.id=l.feed_id AND f.user_id=l.user_id
        JOIN users u ON u.id=f.user_id JOIN clips c ON c.feed_id=f.id AND c.user_id=f.user_id
        JOIN posts p ON p.clip_id=c.id AND p.user_id=f.user_id
        WHERE {' AND '.join(where)} GROUP BY f.id ORDER BY published_at DESC,f.id DESC LIMIT 201''', args).fetchall()
    return {'trips': [dict(row) for row in rows[:200]], 'has_more': len(rows) > 200}


def photon_results(payload):
    results = []
    if not isinstance(payload, dict) or not isinstance(payload.get('features'), list):
        raise ValueError('Invalid place-search response.')
    for item in payload['features'][:6]:
        try:
            lng, lat = item['geometry']['coordinates']
            props = item['properties']
            parts = [props.get(key) for key in ('name', 'city', 'state', 'country')]
            label = ', '.join(dict.fromkeys(str(x) for x in parts if x))[:240]
            place = normalize({'lat': lat, 'lng': lng, 'label': label, 'provider': 'photon', 'source': 'place',
                               'place_id': f"{props.get('osm_type', '')}:{props.get('osm_id', '')}"})
            results.append({**place, 'kind': str(props.get('osm_value', 'place'))[:60]})
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
    return results


def search_places(handler, db, query):
    global LAST_SEARCH
    if not handler.require_user():
        return
    text = query.get('q', [''])[0].strip()
    if not 2 <= len(text) <= 120 or any(ord(x) < 32 for x in text):
        return handler.respond(400, {'error': 'Enter a public place name, 2–120 characters.'})
    endpoint = urlparse(SEARCH_URL)
    if endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.query or endpoint.fragment:
        return handler.respond(503, {'error': 'Place search is not configured. Drop a pin or enter coordinates instead.'})
    cache_key = hashlib.sha256((SEARCH_URL + ':places-v2:' + text.casefold()).encode()).hexdigest()
    with db() as connection:
        cached = connection.execute('SELECT results FROM place_search_cache WHERE cache_key=? AND expires_at>?', (cache_key, int(time.time()))).fetchone()
    if cached:
        return handler.respond(200, {'places': json.loads(cached['results']), 'attribution': '© OpenStreetMap contributors · Photon', 'cached': True})
    if not SEARCH_LOCK.acquire(blocking=False):
        return handler.respond(429, {'error': 'Place search is busy. Try again in a moment, or drop a pin.'}, {'Retry-After': '2'})
    try:
        if time.monotonic() - LAST_SEARCH < 1.1:
            return handler.respond(429, {'error': 'Please wait a moment before another place search.'}, {'Retry-After': '2'})
        LAST_SEARCH = time.monotonic()
        request = Request(SEARCH_URL + '?' + urlencode({'q': text, 'limit': 6, 'lang': 'en'}),
                          headers={'User-Agent': 'SerenityTravelLocal/1.0 (local travel discovery prototype)', 'Accept': 'application/json'})
        with urlopen(request, timeout=8) as response:
            data = response.read(256 * 1024 + 1)
            if len(data) > 256 * 1024:
                raise ValueError('Place search returned too much data.')
            results = photon_results(json.loads(data))
        with db() as connection:
            connection.execute('DELETE FROM place_search_cache WHERE expires_at<?', (int(time.time()),))
            connection.execute('INSERT OR REPLACE INTO place_search_cache VALUES (?,?,?)', (cache_key, json.dumps(results), int(time.time()) + 30 * 86400))
            connection.execute('DELETE FROM place_search_cache WHERE cache_key NOT IN (SELECT cache_key FROM place_search_cache ORDER BY expires_at DESC LIMIT 1000)')
        return handler.respond(200, {'places': results, 'attribution': '© OpenStreetMap contributors · Photon', 'cached': False})
    except (URLError, TimeoutError, OSError, ValueError, TypeError):
        return handler.respond(503, {'error': 'Place search is unavailable. You can still drop a pin or enter coordinates.'})
    finally:
        SEARCH_LOCK.release()


def get(handler, db):
    parsed = urlparse(handler.path)
    query = parse_qs(parsed.query)
    if parsed.path == '/api/map/config':
        return handler.respond(200, {'tile_url': TILE_URL, 'attribution': html.escape(os.environ.get('SERENITY_MAP_ATTRIBUTION', '© OpenStreetMap contributors'))})
    if parsed.path == '/api/map/trips':
        try:
            with db() as connection:
                result = public_trips(connection, query)
            return handler.respond(200, result)
        except ValueError as error:
            return handler.respond(400, {'error': str(error)})
    if parsed.path == '/api/places/search':
        return search_places(handler, db, query)
    return False
