"""Integration test against an isolated temporary database and loopback server."""
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import server
import trip_locations


class BackendFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        server.DATA = Path(cls.temp.name)
        server.UPLOADS = server.DATA / "uploads"
        server.DB = server.DATA / "test.sqlite3"
        server.init()
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        server.PORT = cls.http.server_port
        cls.base = f"http://127.0.0.1:{server.PORT}"
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.temp.cleanup()

    def setUp(self):
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def test_server_host_defaults_to_loopback_and_can_bind_in_container(self):
        self.assertEqual(server.HOST, "127.0.0.1")
        environment = dict(os.environ, ROAM_HOST="0.0.0.0")
        result = subprocess.run(
            [sys.executable, "-c", "import server; print(server.HOST)"],
            cwd=Path(__file__).resolve().parent,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "0.0.0.0")

    def call(self, path, method="GET", payload=None, content_type="application/json", headers=None, client=None):
        body = json.dumps(payload).encode() if isinstance(payload, dict) else payload
        request_headers = dict(headers or {})
        if method != "GET": request_headers["Origin"] = self.base
        if body is not None: request_headers["Content-Type"] = content_type
        request = urllib.request.Request(self.base + path, data=body, method=method, headers=request_headers)
        try:
            response = (client or self.client).open(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read()
            return response.status, json.loads(data) if response.headers.get_content_type() == "application/json" else data

    def test_health_endpoint_is_public_minimal_and_not_cached(self):
        request = urllib.request.Request(self.base + "/api/health")
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "application/json")
            self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertEqual(payload, {"status": "ok", "service": "serenity"})

    def test_account_clip_and_theme_are_private(self):
        email = "traveller@example.test"
        status, data = self.call("/api/register", "POST", {"name": "Traveller", "email": email, "password": "tripPass123"})
        self.assertEqual(status, 200)
        self.assertEqual(data["user"]["email"], email)
        self.assertEqual(self.call("/api/me")[1]["user"]["name"], "Traveller")
        theme = {"accent": "#112233", "soft": "#445566", "paper": "#eeeeee", "ink": "#111111", "energy": 58}
        self.assertEqual(self.call("/api/theme", "PUT", theme)[0], 200)
        self.assertEqual(self.call("/api/theme")[1]["theme"], theme)
        status, clip = self.call("/api/clips", "POST", b"test-video-bytes", "video/mp4", {"X-Filename": "trip.mp4"})
        self.assertEqual(status, 201)
        clip_id = clip["clip"]["id"]
        self.assertEqual(len(self.call("/api/clips")[1]["clips"]), 1)
        self.assertEqual(self.call(f"/api/clips/{clip_id}/video")[1], b"test-video-bytes")
        stranger = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.assertEqual(self.call("/api/clips", client=stranger)[0], 401)
        self.assertEqual(self.call(f"/api/clips/{clip_id}/video", client=stranger)[0], 401)
        self.assertEqual(self.call("/api/logout", "POST")[0], 200)
        self.assertIsNone(self.call("/api/me")[1]["user"])
        self.assertEqual(self.call("/api/login", "POST", {"email": email, "password": "tripPass123"})[0], 200)
        self.assertEqual(len(self.call("/api/clips")[1]["clips"]), 1)
        self.assertEqual(self.call(f"/api/clips/{clip_id}", "DELETE")[0], 200)

    def test_new_password_length_boundaries(self):
        for length in (7, 17):
            status, _ = self.call("/api/register", "POST", {"name": "Boundary", "email": f"length{length}@example.test", "password": "p" * length})
            self.assertEqual(status, 400)
        for length in (8, 16):
            status, _ = self.call("/api/register", "POST", {"name": "Boundary", "email": f"length{length}@example.test", "password": "p" * length})
            self.assertEqual(status, 200)

    def test_collection_import_is_private_idempotent_and_supports_large_groups(self):
        self.call('/api/register', 'POST', {'name': 'Importer', 'email': 'importer@example.test', 'password': 'tripPass123'})
        body = {'batch_key': 'import-test-batch-0001', 'groups': [
            {'key': 'coast', 'name': 'Coast collection', 'destination': '', 'summary': 'Coastal moments'},
            {'key': 'nature', 'name': 'Garden collection', 'destination': '', 'summary': 'Garden moments'},
        ]}
        status, created = self.call('/api/studio/import', 'POST', body)
        self.assertEqual(status, 201)
        self.assertEqual(len(created['groups']), 2)
        status, retried = self.call('/api/studio/import', 'POST', body)
        self.assertEqual(status, 200)
        self.assertEqual(created, retried)
        changed = {**body, 'groups': [{'key': 'coast', 'name': 'Changed'}]}
        self.assertEqual(self.call('/api/studio/import', 'POST', changed)[0], 409)
        feed_id = created['groups'][0]['id']
        for index in range(7):
            status, clip = self.call('/api/clips', 'POST', b'collection-video', 'video/mp4', {'X-Filename': 'garden.mp4', 'X-Feed': str(feed_id), 'X-Upload-Key': f'import-upload-key-{index:04}'})
            self.assertEqual(status, 201)
        first_id = self.call(f'/api/clips?feed={feed_id}')[1]['clips'][0]['id']
        status, repeated = self.call('/api/clips', 'POST', b'collection-video', 'video/mp4', {'X-Filename': 'garden.mp4', 'X-Feed': str(feed_id), 'X-Upload-Key': 'import-upload-key-0000'})
        self.assertEqual(status, 200)
        self.assertEqual(repeated['clip']['id'], first_id)
        self.assertEqual(len(self.call(f'/api/clips?feed={feed_id}')[1]['clips']), 7)
        concurrent_headers = {'X-Filename': 'Garden%20%F0%9F%8C%BC.mp4', 'X-Filename-Encoded': '1', 'X-Feed': str(feed_id), 'X-Upload-Key': 'concurrent-upload-key-0001'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.call('/api/clips', 'POST', b'concurrent-video', 'video/mp4', concurrent_headers), range(2)))
        self.assertEqual(sorted(status for status, _ in results), [200, 201])
        self.assertEqual(results[0][1]['clip']['id'], results[1][1]['clip']['id'])
        self.assertEqual(results[0][1]['clip']['original_name'], 'Garden 🌼.mp4')
        self.assertEqual(len(self.call(f'/api/clips?feed={feed_id}')[1]['clips']), 8)
        self.assertEqual(self.call('/api/clips', 'POST', b'concurrent-video', 'video/mp4', {**concurrent_headers, 'X-Feed': str(created['groups'][1]['id'])})[0], 409)
        self.assertEqual(self.call(f'/api/posts?feed={feed_id}')[1]['posts'], [])
        self.assertIsNone(self.call(f'/api/public-feeds/{feed_id}')[1]['feed'])
        anonymous = urllib.request.build_opener()
        self.assertEqual(self.call('/api/studio/import', 'POST', body, client=anonymous)[0], 401)
        self.assertEqual(self.call(f'/api/clips/{first_id}/video', client=anonymous)[0], 401)
        invalid = {'batch_key': 'invalid-import-key-0001', 'groups': [{'key': 'dupe', 'name': 'One'}, {'key': 'dupe', 'name': 'Two'}]}
        self.assertEqual(self.call('/api/studio/import', 'POST', invalid)[0], 400)

    def test_video_context_correlates_only_creators_past_published_trips(self):
        self.call('/api/register', 'POST', {'name': 'Context Creator', 'email': 'context@example.test', 'password': 'tripPass123'})
        ids = []
        for index, destination in enumerate(('Lisbon', 'Osaka', 'Lisbon', 'Private place', 'Future place')):
            _, feed = self.call('/api/feeds', 'POST', {'name': f'Context journey {index}'})
            feed_id = feed['feed']['id']
            _, clip = self.call('/api/clips', 'POST', b'context-video', 'video/mp4', {'X-Filename': 'context.mp4', 'X-Feed': str(feed_id)})
            if index == 3:
                self.call(f'/api/feeds/{feed_id}/details', 'PUT', {'destination': 'SECRET LOCATION', 'dates': 'SECRET DATES', 'summary': 'SECRET STORY', 'highlights': 'SECRET HIGHLIGHTS'})
                continue
            _, result = self.call('/api/posts', 'POST', {'clip_id': clip['clip']['id'], 'destination': destination, 'caption': 'Published story', 'tip': 'Published tip'})
            post_id = result['post']['id']
            ids.append(post_id)
            with server.db() as connection:
                connection.execute('UPDATE posts SET created_at=? WHERE id=?', ([1000, 2000, 3000, 0, 4000][index], post_id))
        visitor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.call('/api/register', 'POST', {'name': 'Other Creator', 'email': 'context-other@example.test', 'password': 'tripPass123'}, client=visitor)
        _, feed = self.call('/api/feeds', 'POST', {'name': 'Other creator journey'}, client=visitor)
        _, clip = self.call('/api/clips', 'POST', b'other-video', 'video/mp4', {'X-Filename': 'other.mp4', 'X-Feed': str(feed['feed']['id'])}, client=visitor)
        self.call('/api/posts', 'POST', {'clip_id': clip['clip']['id'], 'destination': 'Lisbon', 'caption': 'Other creator story'}, client=visitor)
        anonymous = urllib.request.build_opener()
        status, result = self.call(f'/api/posts/{ids[2]}/context', client=anonymous)
        self.assertEqual(status, 200)
        context = result['context']
        self.assertEqual(context['travel']['destination'], 'Lisbon')
        self.assertEqual(context['travel']['location_source'], 'creator')
        self.assertIsNone(context['travel']['approximate_location'])
        self.assertEqual(context['creator']['name'], 'Context Creator')
        self.assertEqual([trip['preview_post_id'] for trip in context['related_trips']], ids[:2])
        self.assertTrue(context['related_trips'][0]['same_destination'])
        self.assertNotIn('SECRET', json.dumps(context))
        self.assertNotIn('context@example.test', json.dumps(context))
        self.assertEqual(self.call('/api/posts/' + '0' * 32 + '/context')[0], 404)

    def test_trip_preview_visibility_is_reversible_private_and_idempotent(self):
        _, account = self.call('/api/register', 'POST', {'name': 'Visibility Owner', 'email': 'visibility@example.test', 'password': 'tripPass123'})
        _, imported = self.call('/api/studio/import', 'POST', {'batch_key': 'visibility-import-0001', 'groups': [{'key': 'garden', 'name': 'Garden moments'}]})
        feed = imported['groups'][0]['id']
        ids = []
        for index in range(2):
            status, clip = self.call('/api/clips', 'POST', b'visibility-video', 'video/mp4', {'X-Feed': str(feed), 'X-Filename': f'garden-{index}.mp4'})
            self.assertEqual(status, 201)
            ids.append(clip['clip']['id'])
        path = f'/api/feeds/{feed}/visibility'
        visitor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        anonymous = urllib.request.build_opener()
        self.assertEqual(self.call(path, 'PUT', {'visibility': 'public'}, client=anonymous)[0], 401)
        self.call('/api/register', 'POST', {'name': 'Visibility Visitor', 'email': 'visibility-visitor@example.test', 'password': 'tripPass123'}, client=visitor)
        self.assertEqual(self.call(path, 'PUT', {'visibility': 'public'}, client=visitor)[0], 404)
        self.assertEqual(self.call(path, 'PUT', {'visibility': 'public', 'clip_ids': [ids[0], '0' * 32]})[0], 404)
        self.assertEqual(self.call(f'/api/posts?feed={feed}')[1]['posts'], [])
        status, public = self.call(path, 'PUT', {'visibility': 'public'})
        self.assertEqual(status, 200)
        self.assertEqual((public['visibility'], public['published'], public['changed']), ('public', 2, 2))
        result = self.call(f'/api/posts?feed={feed}', client=anonymous)[1]
        self.assertEqual(len(result['trip_posts'][str(feed)]), 2)
        self.assertTrue(all(post['destination'] == 'Location not specified' for post in result['posts']))
        self.assertTrue(all(post['caption'] == 'Garden moments' for post in result['posts']))
        by_clip = {post['clip_name']: post['id'] for post in result['posts']}
        post_id = by_clip['garden-0.mp4']
        self.assertEqual(self.call(path, 'PUT', {'visibility': 'public'})[1]['changed'], 0)
        self.assertEqual(self.call(f'/api/posts/{post_id}/like', 'POST', client=visitor)[0], 200)
        self.assertEqual(self.call(f'/api/posts/{post_id}/save', 'POST', client=visitor)[0], 200)
        self.assertEqual(self.call(f'/api/posts/{post_id}/comments', 'POST', {'body': 'A beautiful garden'}, client=visitor)[0], 201)
        status, mixed = self.call(path, 'PUT', {'visibility': 'private', 'clip_ids': [ids[0]]})
        self.assertEqual(status, 200)
        self.assertEqual((mixed['visibility'], mixed['published'], mixed['private']), ('mixed', 1, 1))
        clips = self.call(f'/api/clips?feed={feed}')[1]['clips']
        self.assertEqual([clip['is_published'] for clip in clips], [0, 1])
        for suffix in ('video', 'comments', 'context'):
            self.assertEqual(self.call(f'/api/posts/{post_id}/{suffix}', client=anonymous)[0], 404)
        for action in ('like', 'save', 'comments'):
            self.assertEqual(self.call(f'/api/posts/{post_id}/{action}', 'POST', {'body': 'Not allowed'}, client=visitor)[0], 404)
        self.assertEqual(self.call(f'/api/clips/{ids[0]}/video')[0], 200)
        self.assertEqual(self.call(f'/api/clips/{ids[0]}/video', client=visitor)[0], 404)
        self.assertEqual(self.call('/api/posts?sort=saved', client=visitor)[1]['posts'], [])
        self.assertEqual(self.call(path, 'PUT', {'visibility': 'private'})[1]['visibility'], 'private')
        self.assertEqual(self.call(f'/api/posts?feed={feed}', client=anonymous)[1]['posts'], [])
        self.assertIsNone(self.call(f'/api/public-feeds/{feed}', client=anonymous)[1]['feed'])
        public_profile = self.call(f"/api/profiles/{account['user']['public_id']}", client=anonymous)[1]['profile']
        self.assertEqual(public_profile['video_count'], 0)
        self.assertEqual(self.call(path, 'PUT', {'visibility': 'public', 'clip_ids': [ids[0]]})[1]['visibility'], 'mixed')
        restored = self.call(f'/api/posts?feed={feed}', client=anonymous)[1]['posts']
        self.assertEqual(len(restored), 1)
        self.assertEqual((restored[0]['id'], restored[0]['likes_count'], restored[0]['comments_count']), (post_id, 1, 1))
        self.assertEqual(self.call(f'/api/posts/{post_id}/comments', client=anonymous)[1]['comments'][0]['body'], 'A beautiful garden')
        self.assertEqual(self.call(f'/api/posts/{post_id}/video', client=anonymous)[0], 200)
        for invalid in ({'visibility': 'friends'}, {'visibility': 'public', 'clip_ids': []}, {'visibility': 'public', 'clip_ids': [ids[0], ids[0]]}):
            self.assertEqual(self.call(path, 'PUT', invalid)[0], 400)
        _, empty = self.call('/api/feeds', 'POST', {'name': 'Empty trip'})
        self.assertEqual(self.call(f"/api/feeds/{empty['feed']['id']}/visibility", 'PUT', {'visibility': 'public'})[0], 409)
        with server.db() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM posts WHERE user_id=?', (account['user']['id'],)).fetchone()[0], 2)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM clips WHERE user_id=?', (account['user']['id'],)).fetchone()[0], 2)

    def test_visibility_assets_are_served_and_categorization_has_direct_post_action(self):
        for asset in ('studio-publication.js', 'studio-publication.css'):
            self.assertEqual(self.call('/' + asset)[0], 200)
            self.assertIn(asset, self.call('/app.html')[1].decode())
            self.assertIn(asset, self.call('/service-worker.js')[1].decode())
        source = self.call('/studio-import.js')[1].decode()
        self.assertIn('Post trips to Home feed', source)
        self.assertIn("saveCollection(true)", source)
        self.assertIn("setTripVisibility(feed.id, 'public'", source)
        self.assertNotIn('Add a destination and story to every selected trip before publishing.', source)

    def test_full_collection_can_be_published_atomically(self):
        _, account = self.call('/api/register', 'POST', {'name': 'Large Publication', 'email': 'large-publication@example.test', 'password': 'tripPass123'})
        _, created = self.call('/api/feeds', 'POST', {'name': '500 moments'})
        feed = created['feed']['id']
        ids = [f'ab{index:030x}' for index in range(500)]
        # Metadata-only fixture: this checks the 500-ID request boundary, not playback.
        with server.db() as connection:
            connection.executemany('INSERT INTO clips(id,user_id,original_name,mime,size,created_at,feed_id) VALUES (?,?,?,?,?,?,?)',
                                   [(clip_id, account['user']['id'], 'large.mp4', 'video/mp4', 1, 1, feed) for clip_id in ids])
        path = f'/api/feeds/{feed}/visibility'
        status, result = self.call(path, 'PUT', {'visibility': 'public', 'clip_ids': ids})
        self.assertEqual(status, 200)
        self.assertEqual((result['published'], result['changed']), (500, 500))
        self.assertEqual(self.call(path, 'PUT', {'visibility': 'public', 'clip_ids': ids})[1]['changed'], 0)
        self.assertEqual(self.call(path, 'PUT', {'visibility': 'private'})[1]['private'], 500)

    def test_map_pins_are_saved_and_only_published_trips_are_discoverable(self):
        self.call('/api/register', 'POST', {'name': 'Map Creator', 'email': 'map-creator@example.test', 'password': 'tripPass123'})
        pin = {'lat': 38.7071, 'lng': -9.1355, 'label': 'Praça do Comércio, Lisbon, Portugal', 'provider': 'manual', 'source': 'pin', 'place_id': ''}
        _, created = self.call('/api/studio/import', 'POST', {'batch_key': 'map-import-batch-0001', 'groups': [
            {'key': 'lisbon', 'name': 'Lisbon waterfront', 'summary': 'Walk the waterfront.', 'location': pin},
            {'key': 'secret', 'name': 'Private map place', 'location': {**pin, 'lat': 0, 'lng': 0, 'label': 'PRIVATE PIN'}},
            {'key': 'unlocated', 'name': 'Without a destination'},
        ]})
        feeds = [group['id'] for group in created['groups']]
        for feed in feeds:
            self.assertEqual(self.call('/api/clips', 'POST', b'map-video', 'video/mp4', {'X-Feed': str(feed), 'X-Filename': 'map.mp4'})[0], 201)
        details = self.call(f'/api/feeds/{feeds[0]}/details')[1]['details']
        self.assertEqual(details['location'], pin)
        self.assertEqual(details['destination'], pin['label'])
        self.assertNotIn('dates', details); self.assertNotIn('highlights', details)
        anonymous = urllib.request.build_opener()
        self.assertEqual(self.call(f'/api/map/trips?trip={feeds[0]}', client=anonymous)[1]['trips'], [])
        for feed in (feeds[0], feeds[2]):
            self.assertEqual(self.call(f'/api/feeds/{feed}/visibility', 'PUT', {'visibility': 'public'})[0], 200)
        mapped = self.call('/api/map/trips?bbox=-10,38,-8,40', client=anonymous)[1]['trips']
        self.assertEqual([trip['id'] for trip in mapped], [feeds[0]])
        self.assertEqual((mapped[0]['lat'], mapped[0]['lng'], mapped[0]['summary']), (pin['lat'], pin['lng'], 'Walk the waterfront.'))
        self.assertNotIn('PRIVATE PIN', json.dumps(mapped)); self.assertNotIn('email', mapped[0])
        self.assertEqual(self.call('/api/map/trips?bbox=10,10,11,11', client=anonymous)[1]['trips'], [])
        self.assertEqual(self.call('/api/map/trips?q=Lisbon', client=anonymous)[1]['trips'][0]['id'], feeds[0])
        self.assertEqual(self.call('/api/map/trips?bbox=170,-90,-170,90', client=anonymous)[1]['trips'], [])
        post = self.call(f'/api/posts?feed={feeds[0]}')[1]['posts'][0]
        travel = self.call(f"/api/posts/{post['id']}/context", client=anonymous)[1]['context']['travel']
        self.assertEqual(travel['location'], pin)
        self.assertEqual(travel['feed_id'], feeds[0])
        stranger = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.call('/api/register', 'POST', {'name': 'Map Stranger', 'email': 'map-stranger@example.test', 'password': 'tripPass123'}, client=stranger)
        update = {'destination': pin['label'], 'summary': 'New experience', 'location': {**pin, 'lat': 41.15, 'lng': -8.61, 'label': 'Porto, Portugal'}, 'dates': 'RETIRED DATE', 'highlights': 'RETIRED HIGHLIGHT'}
        self.assertEqual(self.call(f'/api/feeds/{feeds[0]}/details', 'PUT', update, client=stranger)[0], 404)
        status, saved = self.call(f'/api/feeds/{feeds[0]}/details', 'PUT', update)
        self.assertEqual(status, 200)
        self.assertNotIn('dates', saved['details']); self.assertNotIn('highlights', saved['details'])
        self.assertEqual(self.call(f'/api/map/trips?trip={feeds[0]}', client=anonymous)[1]['trips'][0]['label'], 'Porto, Portugal')
        self.assertEqual(self.call(f'/api/posts?feed={feeds[0]}')[1]['posts'][0]['destination'], 'Porto, Portugal')
        for location in ({**pin, 'lat': 91}, {**pin, 'lng': float('nan')}, {**pin, 'lat': True}, {**pin, 'label': ''}):
            self.assertEqual(self.call(f'/api/feeds/{feeds[0]}/details', 'PUT', {**update, 'location': location})[0], 400)
        self.assertEqual(self.call('/api/map/trips?bbox=bad,bounds')[0], 400)
        self.assertEqual(self.call('/api/map/trips?bbox=-181,-90,180,90')[0], 400)
        self.call(f'/api/feeds/{feeds[0]}/visibility', 'PUT', {'visibility': 'private'})
        self.assertEqual(self.call(f'/api/map/trips?trip={feeds[0]}', client=anonymous)[1]['trips'], [])
        self.assertEqual(self.call(f'/api/feeds/{feeds[0]}/details')[1]['details']['location']['label'], 'Porto, Portugal')
        # Removing a pin also removes a still-public trip from Map, not Home feed.
        self.call(f'/api/feeds/{feeds[0]}/visibility', 'PUT', {'visibility': 'public'})
        self.call(f'/api/feeds/{feeds[0]}/details', 'PUT', {'destination': '', 'summary': '', 'location': None})
        self.assertEqual(self.call(f'/api/map/trips?trip={feeds[0]}', client=anonymous)[1]['trips'], [])
        self.assertTrue(self.call(f'/api/posts?feed={feeds[0]}', client=anonymous)[1]['posts'])

    def test_place_search_uses_explicit_queries_cache_rate_limits_and_safe_fallback(self):
        anonymous = urllib.request.build_opener()
        self.assertEqual(self.call('/api/places/search?q=Lisbon', client=anonymous)[0], 401)
        self.call('/api/register', 'POST', {'name': 'Place Searcher', 'email': 'place-searcher@example.test', 'password': 'tripPass123'})
        payload = {'features': [{'geometry': {'coordinates': [-9.1355, 38.7071]}, 'properties': {'name': 'Praça do Comércio', 'city': 'Lisbon', 'country': 'Portugal', 'osm_type': 'W', 'osm_id': 123}}]}
        response = MagicMock(); response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with patch.object(trip_locations, 'LAST_SEARCH', 0), patch.object(trip_locations, 'urlopen', return_value=response) as upstream:
            status, result = self.call('/api/places/search?q=Lisbon')
            self.assertEqual(status, 200); self.assertEqual(result['places'][0]['lat'], 38.7071)
            self.assertEqual(result['places'][0]['provider'], 'photon')
            self.assertFalse(result['cached'])
            self.assertEqual(self.call('/api/places/search?q=Lisbon')[1]['cached'], True)
            self.assertEqual(upstream.call_count, 1)
            self.assertIn('SerenityTravelLocal', upstream.call_args.args[0].get_header('User-agent'))
            self.assertEqual(self.call('/api/places/search?q=Porto')[0], 429)
        with patch.object(trip_locations, 'LAST_SEARCH', 0), patch.object(trip_locations, 'urlopen', side_effect=OSError('offline')):
            status, result = self.call('/api/places/search?q=Osaka')
            self.assertEqual(status, 503); self.assertIn('drop a pin', result['error'])
        self.assertEqual(self.call('/api/places/search?q=a')[0], 400)

    def test_map_assets_and_retired_fields(self):
        for asset in ('map.html', 'map-core.js', 'travel-map.js', 'travel-map.css', 'destination-picker.js', 'destination-picker.css'):
            self.assertEqual(self.call('/' + asset)[0], 200)
            self.assertIn(asset, self.call('/service-worker.js')[1].decode())
        for page in ('app.html', 'feed.html', *[f'tile-{n:02}.html' for n in range(1, 6)]):
            html = self.call('/' + page)[1].decode()
            self.assertNotIn('name="dates"', html); self.assertNotIn('name="highlights"', html)
            self.assertIn('map-core.js', html)
        self.assertIn("if (page === 'map.html') return 'map'", self.call('/liquid-toolbar.js')[1].decode())

    def test_landing_app_and_feeds_are_served(self):
        for path in ("/", "/app.html", "/feed.html", "/my-clips.html", "/my-clips.css", "/my-clips.js", "/account.html", "/account.css", "/account.js", "/profile.html", "/profile.css", "/profile.js", "/auth.html", "/search.html", "/messages-client.js", "/messages.js", "/messages.css", "/serenity-logo.svg", "/serenity-icon-192.png", "/serenity-icon-512.png", "/app-studio.js", "/social-feed.js", "/social-feed.css", "/header-feed-picker.js", "/liquid-toolbar.js", "/liquid-toolbar.css", "/trip-sidebar.js", "/trip-sidebar.css", "/feed-view.js", "/feed-view.css", "/manifest.webmanifest", "/service-worker.js", "/app-pwa.js", *[f"/tile-{number:02}.html" for number in range(1, 6)]):
            status, body = self.call(path)
            self.assertEqual(status, 200, path)
            self.assertTrue(body, path)
            if (path.endswith('.html') or path == '/') and path not in ('/', '/test.html', '/my-clips.html'):
                self.assertIn(b'liquid-toolbar.js', body, path)
                self.assertIn(b'liquid-toolbar.css', body, path)
            if path == "/app.html" or path.startswith('/tile-'):
                self.assertIn(b'trip-sidebar.js', body, path)
                self.assertIn(b'trip-sidebar.css', body, path)
        landing = self.call("/")[1].decode()
        home = self.call("/app.html")[1].decode()
        self.assertIn('href="app.html#home-feed">Open app ↗', landing)
        self.assertNotIn('liquid-toolbar.js', landing)
        self.assertNotIn('header-feed-picker.js', landing)
        self.assertNotIn('data-feed-choice="1"', home)
        self.assertIn('src="trip-sidebar.js"', home)
        self.assertIn('src="social-feed.js"', home)
        self.assertIn('id="postList"', home)
        self.assertIn('href="search.html">Chat ↗', home)
        self.assertNotIn('href="messages.html"', home)
        self.assertNotIn('data-post-sort=', home)
        self.assertNotIn('>Latest<', home)
        self.assertNotIn('>Popular<', home)
        feed_hub_css = self.call('/feed-hub.css')[1].decode()
        self.assertIn('body[data-app-view="home"] .liquid-toolbar', feed_hub_css)
        self.assertIn('object-fit:contain', feed_hub_css)
        self.assertIn('home-toolbar-icons .liquid-toolbar__link span:last-child', feed_hub_css)
        self.assertIn('.hub-tabs { position:relative;', feed_hub_css)
        self.assertIn('.hub-tab[aria-selected="true"]', feed_hub_css)
        self.assertNotIn('.hub-swipe-hint', feed_hub_css)
        feed_hub_js = self.call('/feed-hub.js')[1].decode()
        self.assertIn("'home-toolbar-icons'", feed_hub_js)
        self.assertNotIn('hub-swipe-hint', feed_hub_js)
        self.assertNotIn('Swipe left or right through this trip', feed_hub_js)
        self.assertIn('src="header-feed-picker.js"', home)
        self.assertIn('href="manifest.webmanifest"', home)
        self.assertIn('id="installAppButton"', home)
        self.assertIn('href="/">Website</a>', home)
        self.assertIn('src="app-pwa.js"', home)
        manifest_status, manifest_bytes = self.call('/manifest.webmanifest')
        self.assertEqual(manifest_status, 200)
        manifest = json.loads(manifest_bytes)
        self.assertEqual(manifest['start_url'], '/app.html#home-feed')
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(manifest['scope'], '/')
        self.assertLess(home.index('id="feeds"'), home.index('id="home-feed"'))
        self.assertNotIn('Put a place<br>on the map.', home)
        self.assertNotIn('01 / EXPLORE', home)
        self.assertIn('.clip-studio .feeds{display:block;columns:', home)
        studio = self.call('/app-studio.js')[1].decode()
        self.assertIn("$('#accountLink').href = 'account.html';", studio)
        self.assertIn('Create trip and save videos', home)
        self.assertIn('studio-gallery-next', studio)
        self.assertIn('Manage trip details and videos', studio)
        self.assertIn('Saving and publishing', studio)
        self.assertIn('Publish saved videos to Home feed', studio)
        self.assertIn('window.RoamApp.publishPost', studio)
        social_feed = self.call('/social-feed.js')[1].decode()
        self.assertIn('result.trip_posts?.[feedId]', social_feed)
        self.assertIn('Previous trip video', self.call('/feed-hub.js')[1].decode())
        self.assertIn('social-post__slides', self.call('/feed-hub.css')[1].decode())
        self.assertIn("preload = 'none'", social_feed)
        self.assertNotIn('postForm', self.call('/social-feed.js')[1].decode())
        self.assertIn('name="videos" type="file"', home)
        self.assertIn('window.RoamApp.upload(file, Number(feedId))', studio)
        account = self.call('/account.html')[1].decode()
        self.assertIn('Open Clip Studio', account)
        self.assertIn('id="accountTrips"', account)
        self.assertIn('id="savedTrips"', account)
        self.assertIn('id="savedMore"', account)
        self.assertIn('id="settingsDrawer"', account)
        self.assertIn('id="autoplayPreference"', account)
        self.assertIn('id="themeForm"', account)
        self.assertIn('name="accent" type="color"', account)
        self.assertIn('src="shared-theme.js"', account)
        self.assertIn('src="account.js"', account)
        self.assertIn('id="profileForm"', account)
        self.assertIn('id="publicProfileLink"', account)
        self.assertIn('href="account.html">Account ↗', home)
        auth_client = self.call('/auth-client.js')[1].decode()
        self.assertIn("location.replace('account.html')", auth_client)
        self.assertIn("next.get('next') === 'messages'", auth_client)
        self.assertIn("location.replace(`search.html${conversation.size", auth_client)
        account_client = self.call('/account.js')[1].decode()
        self.assertIn('window.RoamApp.saveTheme(theme)', account_client)
        self.assertIn('window.RoamApp.publicProfile(signedInUser.public_id)', account_client)
        self.assertIn("window.RoamApp.posts({ sort: 'saved', offset: savedOffset })", account_client)
        self.assertIn("window.RoamApp.togglePostAction(post.id, 'save')", account_client)
        self.assertIn('window.RoamApp.postVideoUrl(post.id)', account_client)
        self.assertIn("window.RoamApp.logout()", account_client)
        published_clips = self.call('/my-clips.html')[1].decode()
        self.assertIn("location.replace('account.html#published-trips')", published_clips)
        self.assertIn("serenity-autoplay", self.call('/feed-hub.js')[1].decode())
        for number in range(1, 6):
            tile = self.call(f'/tile-{number:02}.html')[1].decode()
            self.assertIn('Published trip videos', tile)
            self.assertNotIn('feedUploadButton', tile)
        toolbar = self.call('/liquid-toolbar.js')[1].decode()
        self.assertIn("link.setAttribute('aria-label', destination.label)", toolbar)
        self.assertIn("label: 'Home feed', icon: '⌂', href: 'app.html#home-feed'", toolbar)
        self.assertEqual(toolbar.count("key: '"), 5)
        self.assertIn("key: 'map', label: 'Map'", toolbar)
        self.assertIn("key: 'chat', label: 'Chat', icon: '◌', href: 'search.html'", toolbar)
        self.assertNotIn("key: 'search'", toolbar)
        self.assertNotIn("key: 'discover'", toolbar)
        self.assertNotIn("key: 'clips'", toolbar)
        self.assertEqual(re.findall(r"key: '([^']+)'", toolbar), ['home', 'chat', 'map', 'trips', 'account'])
        self.assertIn("href: 'search.html'", toolbar)
        self.assertIn("if (page === 'search.html') return 'chat'", toolbar)
        self.assertIn("key: 'account'", toolbar)
        self.assertIn("label: 'Clip Studio'", toolbar)
        sidebar = self.call('/trip-sidebar.js')[1].decode()
        self.assertIn("location.hash === '#feeds'", sidebar)
        self.assertIn('clip.is_published && clip.feed_id != null', sidebar)
        self.assertIn('publishedClips.filter(clip => String(clip.feed_id) === id)', sidebar)
        self.assertIn("empty.textContent = 'Your published trips will appear here.'", sidebar)
        feed_hub = self.call('/feed-hub.js')[1].decode()
        self.assertIn("searchInput.setAttribute('aria-label', 'Search trips, destinations, and creators in the Home feed')", feed_hub)
        self.assertIn("item.hidden = Boolean(query)", feed_hub)
        self.assertIn('.hub-search { position:absolute;', self.call('/feed-hub.css')[1].decode())
        chat = self.call('/search.html')[1].decode()
        self.assertIn('<title>Chat — Serenity</title>', chat)
        self.assertIn('id="messenger"', chat)
        self.assertIn('src="messages.js"', chat)
        self.assertNotIn('src="trip-sidebar.js"', chat)
        service_worker = self.call('/service-worker.js')[1].decode()
        self.assertIn('serenity-shell-v12-people-chat', service_worker)
        for asset in ('messages.css', 'messages-client.js', 'messages.js'):
            self.assertIn(f"'/{asset}'", service_worker)
        self.assertIn("toggle.setAttribute('aria-controls', sidebar.id)", sidebar)
        self.assertIn('toggle.onclick = () => setOpen(!isOpen, true)', sidebar)
        self.assertIn("setOpen(!mobile.matches)", sidebar)
        sidebar_css = self.call('/trip-sidebar.css')[1].decode()
        self.assertIn('top: 22px;', sidebar_css)
        self.assertIn('left: 14px;', sidebar_css)
        self.assertIn('transform: translateX(var(--trip-sidebar-width));', sidebar_css)

    def test_public_posts_keep_private_clips_private(self):
        self.assertEqual(self.call("/api/register", "POST", {"name": "Alex", "email": "alex@example.test", "password": "tripPass123"})[0], 200)
        feed_ids = list(self.call("/api/feeds")[1]["feeds"])
        first_feed = int(feed_ids[0])
        second_feed = int(feed_ids[1])
        status, clip = self.call("/api/clips", "POST", b"public-travel-video", "video/mp4", {"X-Filename": "lisbon.mp4", "X-Feed": str(first_feed)})
        self.assertEqual(status, 201)
        clip_id = clip["clip"]["id"]
        self.assertFalse(self.call(f"/api/clips?feed={first_feed}")[1]["clips"][0]["is_published"])
        other = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.assertEqual(self.call(f"/api/clips/{clip_id}/video", client=other)[0], 401)
        self.assertEqual(self.call("/api/posts", "POST", {"clip_id": clip_id, "destination": "Lisbon, Portugal", "caption": "The best afternoon on the waterfront.", "tip": "Take the tram early."}, client=other)[0], 401)
        status, created = self.call("/api/posts", "POST", {"clip_id": clip_id, "destination": "Lisbon, Portugal", "caption": "The best afternoon on the waterfront.", "tip": "Take the tram early."})
        self.assertEqual(status, 201)
        post_id = created["post"]["id"]
        _, second_trip_clip = self.call("/api/clips", "POST", b"second-trip-video", "video/mp4", {"X-Filename": "lisbon-evening.mp4", "X-Feed": str(first_feed)})
        self.assertEqual(self.call("/api/posts", "POST", {"clip_id": second_trip_clip["clip"]["id"], "destination": "Lisbon, Portugal", "caption": "The waterfront at sunset.", "tip": "Stay for the evening light."})[0], 201)
        self.call("/api/clips", "POST", b"unpublished-trip-video", "video/mp4", {"X-Filename": "private-lisbon.mp4", "X-Feed": str(first_feed)})
        self.assertTrue(self.call(f"/api/clips?feed={first_feed}")[1]["clips"][0]["is_published"])
        self.assertEqual(self.call("/api/posts", "POST", {"clip_id": clip_id, "destination": "Lisbon", "caption": "Duplicate"})[0], 409)
        status, feed = self.call("/api/posts?q=Lisbon", client=other)
        self.assertEqual(status, 200)
        self.assertEqual(feed["posts"][0]["author_name"], "Alex")
        self.assertEqual(feed["posts"][0]["author_username"], "alex")
        self.assertRegex(feed["posts"][0]["author_public_id"], r"^[0-9a-f]{16}$")
        self.assertEqual(feed["posts"][0]["destination"], "Lisbon, Portugal")
        self.assertEqual(feed["posts"][0]["feed_id"], first_feed)
        self.assertIn(feed["posts"][0]["clip_name"], ("lisbon.mp4", "lisbon-evening.mp4"))
        self.assertEqual(self.call(f"/api/public-feeds/{first_feed}")[1]["feed"]["name"], "Feed 01")
        trip_feed = self.call(f"/api/posts?feed={first_feed}", client=other)[1]
        self.assertEqual(len(trip_feed["posts"]), 2)
        self.assertEqual([clip["clip_name"] for clip in trip_feed["trip_posts"][str(first_feed)]], ["lisbon.mp4", "lisbon-evening.mp4"])
        self.assertNotIn("private-lisbon.mp4", [clip["clip_name"] for clip in trip_feed["trip_posts"][str(first_feed)]])
        self.assertEqual(self.call(f"/api/posts?feed={second_feed}", client=other)[1]["posts"], [])
        self.assertEqual(self.call("/api/posts?feed=0", client=other)[0], 400)
        status, unassigned = self.call("/api/clips", "POST", b"unassigned-video", "video/mp4", {"X-Filename": "unassigned.mp4"})
        self.assertEqual(status, 201)
        self.assertEqual(self.call("/api/posts", "POST", {"clip_id": unassigned["clip"]["id"], "destination": "Oslo", "caption": "A city trip"})[0], 400)
        self.assertNotIn("email", feed["posts"][0])
        self.assertEqual(self.call(f"/api/posts/{post_id}/video", client=other)[1], b"public-travel-video")
        self.assertEqual(self.call(f"/api/clips/{clip_id}/video", client=other)[0], 401)
        self.assertEqual(self.call("/api/register", "POST", {"name": "Sam", "email": "sam@example.test", "password": "tripPass123"}, client=other)[0], 200)
        self.assertEqual(self.call(f"/api/posts/{post_id}/like", "POST", client=other)[1]["count"], 1)
        self.assertEqual(self.call(f"/api/posts/{post_id}/save", "POST", client=other)[1]["active"], True)
        saved = self.call("/api/posts?sort=saved", client=other)[1]["posts"]
        self.assertEqual([post["id"] for post in saved], [post_id])
        self.assertEqual(self.call(f"/api/posts/{post_id}/save", "POST", client=other)[1]["active"], False)
        self.assertEqual(self.call("/api/posts?sort=saved", client=other)[1]["posts"], [])
        self.assertEqual(self.call(f"/api/posts/{post_id}/comments", "POST", {"body": "When should I go?"}, client=other)[0], 201)
        comment = self.call(f"/api/posts/{post_id}/comments", client=self.client)[1]["comments"][0]
        self.assertEqual(comment["body"], "When should I go?")
        self.assertEqual(comment["author_username"], "sam")
        self.assertEqual(self.call(f"/api/posts/{post_id}", "DELETE", client=other)[0], 404)
        self.assertEqual(self.call(f"/api/posts/{post_id}", "DELETE")[0], 200)
        self.assertEqual(self.call(f"/api/posts/{post_id}/video", client=other)[0], 404)
        self.assertEqual(self.call(f"/api/clips/{clip_id}/video")[0], 200)
        self.assertFalse(self.call(f"/api/clips?feed={first_feed}")[1]["clips"][0]["is_published"])

    def test_shareable_profiles_list_only_published_trips(self):
        status, registered = self.call("/api/register", "POST", {"name": "Mina Journeys", "email": "mina@example.test", "password": "tripPass123"})
        self.assertEqual(status, 200)
        user = registered["user"]
        self.assertRegex(user["public_id"], r"^[0-9a-f]{16}$")
        self.assertEqual(user["username"], "mina_journeys")
        feed_id = next(iter(self.call("/api/feeds")[1]["feeds"]))
        details = {"destination": "Kyoto", "dates": "April", "summary": "A spring trip.", "highlights": "The old town"}
        self.assertEqual(self.call(f"/api/feeds/{feed_id}/details", "PUT", details)[0], 200)
        _, clip = self.call("/api/clips", "POST", b"public", "video/mp4", {"X-Filename": "kyoto.mp4", "X-Feed": feed_id})
        _, second_clip = self.call("/api/clips", "POST", b"public again", "video/mp4", {"X-Filename": "kyoto-evening.mp4", "X-Feed": feed_id})
        _, private_clip = self.call("/api/clips", "POST", b"private", "video/mp4", {"X-Filename": "private.mp4", "X-Feed": str(int(feed_id) + 1)})
        self.assertEqual(self.call("/api/posts", "POST", {"clip_id": clip["clip"]["id"], "destination": "Kyoto", "caption": "A spring trip.", "tip": "Highlights: The old town"})[0], 201)
        self.assertEqual(self.call("/api/posts", "POST", {"clip_id": second_clip["clip"]["id"], "destination": "Kyoto", "caption": "Evening walk.", "tip": ""})[0], 201)
        public = self.call(f"/api/profiles/{user['username']}")[1]["profile"]
        by_id = self.call(f"/api/profiles/{user['public_id']}")[1]["profile"]
        self.assertEqual(public, by_id)
        self.assertEqual(public["video_count"], 2)
        self.assertEqual(public["trip_count"], 1)
        self.assertEqual(public["trips"][0]["name"], "Feed 01")
        self.assertEqual(public["trips"][0]["posts"][0]["clip_name"], "kyoto.mp4")
        self.assertEqual([post["clip_name"] for post in public["trips"][0]["posts"]], ["kyoto.mp4", "kyoto-evening.mp4"])
        self.assertNotIn("email", public)
        self.assertNotIn(private_clip["clip"]["id"], str(public))
        stranger = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.assertEqual(self.call(f"/api/profiles/{user['public_id']}", client=stranger)[0], 200)
        with urllib.request.urlopen(self.base + f"/api/profiles/{user['public_id']}") as response:
            self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertEqual(self.call("/api/profile", "PUT", {"name": "Mina", "username": "mina_travels", "bio": "Finding quiet corners."})[0], 200)
        updated = self.call("/api/profiles/mina_travels")[1]["profile"]
        self.assertEqual(updated["bio"], "Finding quiet corners.")
        self.assertEqual(updated["public_id"], user["public_id"])
        self.assertEqual(self.call(f"/api/profiles/{user['username']}")[0], 404)
        self.assertEqual(self.call("/api/profile", "PUT", {"name": "Mina", "username": "x", "bio": ""})[0], 400)
        self.assertEqual(self.call("/api/profile", "PUT", {"name": "Mina", "username": "mina_travels", "bio": ""}, client=stranger)[0], 401)
        self.assertEqual(self.call("/api/register", "POST", {"name": "Other", "email": "othermina@example.test", "password": "tripPass123"}, client=stranger)[0], 200)
        self.assertEqual(self.call("/api/profile", "PUT", {"name": "Other", "username": "mina_travels", "bio": ""}, client=stranger)[0], 409)

    def test_existing_accounts_receive_stable_public_identity(self):
        original = (server.DATA, server.UPLOADS, server.DB)
        try:
            with tempfile.TemporaryDirectory() as directory:
                server.DATA = Path(directory)
                server.UPLOADS = server.DATA / "uploads"
                server.DB = server.DATA / "legacy.sqlite3"
                with server.db() as connection:
                    connection.execute("""CREATE TABLE users (
                        id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
                        salt BLOB NOT NULL, password_hash BLOB NOT NULL, created_at INTEGER NOT NULL
                    )""")
                    connection.execute("INSERT INTO users VALUES (1, ?, ?, ?, ?, ?)", ("legacy@example.test", "Legacy Traveller", b"salt", b"hash", 100))
                server.init()
                with server.db() as connection:
                    first = dict(connection.execute("SELECT public_id, username, bio FROM users WHERE id=1").fetchone())
                server.init()
                with server.db() as connection:
                    second = connection.execute("SELECT public_id, username, bio FROM users WHERE id=1").fetchone()
                self.assertRegex(first["public_id"], r"^[0-9a-f]{16}$")
                self.assertEqual(first["username"], "legacy_traveller")
                self.assertEqual(first["public_id"], second["public_id"])
        finally:
            server.DATA, server.UPLOADS, server.DB = original

    def test_feed_assignment_and_private_notes(self):
        self.assertEqual(self.call("/api/register", "POST", {"name": "Creator", "email": "creator@example.test", "password": "tripPass123"})[0], 200)
        feeds = self.call("/api/feeds")[1]["feeds"]
        first_feed, second_feed, third_feed = (int(feed_id) for feed_id in list(feeds)[:3])
        status, first = self.call("/api/clips", "POST", b"first-video", "video/mp4", {"X-Filename": "paris.mp4", "X-Feed": str(second_feed)})
        self.assertEqual(status, 201)
        clip_id = first["clip"]["id"]
        self.assertEqual(len(self.call(f"/api/clips?feed={second_feed}")[1]["clips"]), 1)
        self.assertEqual(self.call(f"/api/clips?feed={first_feed}")[1]["clips"], [])
        self.assertEqual(self.call(f"/api/clips/{clip_id}/feed", "PUT", {"feed_id": third_feed})[0], 200)
        self.assertEqual(len(self.call(f"/api/clips?feed={third_feed}")[1]["clips"]), 1)
        self.assertEqual(self.call(f"/api/feeds/{third_feed}/notes", "POST", {"body": "Meet at the station at nine."})[0], 201)
        self.assertEqual(self.call(f"/api/feeds/{third_feed}/notes")[1]["notes"][0]["body"], "Meet at the station at nine.")
        stranger = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.assertEqual(self.call(f"/api/feeds/{third_feed}/notes", client=stranger)[0], 401)
        self.assertEqual(self.call(f"/api/clips?feed={third_feed}", client=stranger)[0], 401)

    def test_trip_details_are_saved_per_feed_and_account(self):
        self.assertEqual(self.call("/api/register", "POST", {"name": "Explorer", "email": "explorer@example.test", "password": "tripPass123"})[0], 200)
        feed_ids = list(self.call("/api/feeds")[1]["feeds"])
        first_feed, second_feed = feed_ids[:2]
        details = {"destination": "Lisbon", "dates": "June 2027", "summary": "A long weekend by the sea.", "highlights": "Tram 28 and the waterfront"}
        self.assertEqual(self.call(f"/api/feeds/{second_feed}/details", "PUT", details)[0], 200)
        saved = self.call(f"/api/feeds/{second_feed}/details")[1]["details"]
        self.assertEqual(saved["destination"], "Lisbon")
        self.assertNotIn('highlights', saved)
        self.assertNotIn('dates', saved)
        self.assertEqual(self.call(f"/api/feeds/{first_feed}/details")[1]["details"]["destination"], "")
        self.assertEqual(self.call(f"/api/feeds/{second_feed}/details", "PUT", {**details, "summary": "x" * 1001})[0], 400)
        stranger = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.assertEqual(self.call(f"/api/feeds/{second_feed}/details", client=stranger)[0], 401)
        self.assertEqual(self.call(f"/api/feeds/{second_feed}/details", "PUT", details, client=stranger)[0], 401)
        self.assertEqual(self.call("/api/logout", "POST")[0], 200)
        self.assertEqual(self.call("/api/login", "POST", {"email": "explorer@example.test", "password": "tripPass123"})[0], 200)
        self.assertEqual(self.call(f"/api/feeds/{second_feed}/details")[1]["details"]["destination"], "Lisbon")

    def test_feed_names_and_saved_uploads_survive_login(self):
        self.assertEqual(self.call("/api/register", "POST", {"name": "Renamer", "email": "renamer@example.test", "password": "tripPass123"})[0], 200)
        feeds = self.call("/api/feeds")[1]["feeds"]
        feed_id = list(feeds)[3]
        self.assertEqual(self.call(f"/api/feeds/{feed_id}/name", "PUT", {"name": "Tokyo with friends"})[1]["name"], "Tokyo with friends")
        self.assertEqual(self.call("/api/feeds")[1]["feeds"][feed_id], "Tokyo with friends")
        status, saved = self.call("/api/clips", "POST", b"feed-four-video", "video/mp4", {"X-Filename": "tokyo.mp4", "X-Feed": feed_id})
        self.assertEqual(status, 201)
        self.assertEqual(saved["clip"]["feed_id"], int(feed_id))
        self.assertEqual(self.call(f"/api/feeds/{feed_id}/name", "PUT", {"name": " "})[0], 400)
        other = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.assertEqual(self.call("/api/feeds", client=other)[0], 401)
        self.assertEqual(self.call(f"/api/feeds/{feed_id}/name", "PUT", {"name": "Nope"}, client=other)[0], 401)
        self.assertEqual(self.call("/api/logout", "POST")[0], 200)
        self.assertEqual(self.call("/api/login", "POST", {"email": "renamer@example.test", "password": "tripPass123"})[0], 200)
        self.assertEqual(self.call("/api/feeds")[1]["feeds"][feed_id], "Tokyo with friends")
        self.assertEqual(self.call(f"/api/clips?feed={feed_id}")[1]["clips"][0]["id"], saved["clip"]["id"])

    def test_unlimited_named_feeds_are_owned_and_assignable(self):
        self.assertEqual(self.call("/api/register", "POST", {"name": "Organizer", "email": "organizer@example.test", "password": "tripPass123"})[0], 200)
        feeds = self.call("/api/feeds")[1]["feeds"]
        created_ids = []
        for index in range(8):
            status, result = self.call("/api/feeds", "POST", {"name": f"Journey {index + 1}"})
            self.assertEqual(status, 201)
            created_ids.append(str(result["feed"]["id"]))
        all_feeds = self.call("/api/feeds")[1]["feeds"]
        self.assertEqual(len(all_feeds), len(feeds) + 8)
        self.assertEqual(all_feeds[created_ids[-1]], "Journey 8")
        status, saved = self.call("/api/clips", "POST", b"new-trip-video", "video/mp4", {"X-Filename": "journey.mp4", "X-Feed": created_ids[-1]})
        self.assertEqual(status, 201)
        self.assertEqual(saved["clip"]["feed_id"], int(created_ids[-1]))
        self.assertEqual(len(self.call(f"/api/clips?feed={created_ids[-1]}")[1]["clips"]), 1)
        self.assertEqual(self.call("/api/posts", "POST", {
            "clip_id": saved["clip"]["id"],
            "destination": "Journey destination",
            "caption": "A story from a newly created trip.",
        })[0], 201)
        self.assertEqual(self.call(f"/api/posts?feed={created_ids[-1]}")[1]["posts"][0]["feed_name"], "Journey 8")
        self.assertEqual(self.call(f"/api/public-feeds/{created_ids[-1]}")[1]["feed"]["name"], "Journey 8")
        stranger = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.assertEqual(self.call("/api/register", "POST", {"name": "Other", "email": "other@example.test", "password": "tripPass123"}, client=stranger)[0], 200)
        self.assertEqual(self.call("/api/feeds", "POST", {"name": "Not yours"}, client=stranger)[0], 201)
        self.assertEqual(self.call(f"/api/feeds/{created_ids[-1]}/name", "PUT", {"name": "Hijacked"}, client=stranger)[0], 404)
        self.assertEqual(self.call(f"/api/clips/{saved['clip']['id']}/feed", "PUT", {"feed_id": int(created_ids[-1])}, client=stranger)[0], 404)

    def test_legacy_feed_data_migrates_to_unique_owner_ids(self):
        original = (server.DATA, server.UPLOADS, server.DB)
        with tempfile.TemporaryDirectory() as temp:
            try:
                server.DATA = Path(temp)
                server.UPLOADS = server.DATA / "uploads"
                server.DB = server.DATA / "legacy.sqlite3"
                server.init()
                with server.db() as connection:
                    users = []
                    for index in range(2):
                        cursor = connection.execute(
                            "INSERT INTO users(email,name,salt,password_hash,created_at) VALUES (?,?,?,?,?)",
                            (f"legacy{index}@example.test", f"Legacy {index}", b"salt", b"hash", 1),
                        )
                        users.append(cursor.lastrowid)
                    connection.execute("DELETE FROM user_feeds")
                    connection.execute("DELETE FROM app_migrations WHERE name='global-user-feeds'")
                    connection.execute("INSERT INTO feed_names(user_id,feed_id,name) VALUES (?,?,?)", (users[0], 1, "First owner's trip"))
                    connection.execute("INSERT INTO feed_details(user_id,feed_id,destination,dates,summary,highlights,updated_at) VALUES (?,?,?,?,?,?,?)", (users[0], 1, "Osaka", "May", "Story", "Food", 1))
                    connection.execute("INSERT INTO feed_notes(user_id,feed_id,body,created_at) VALUES (?,?,?,?)", (users[1], 1, "Private note", 1))
                    connection.execute("INSERT INTO clips(id,user_id,original_name,mime,size,created_at,feed_id) VALUES (?,?,?,?,?,?,?)", ("a" * 32, users[0], "osaka.mp4", "video/mp4", 5, 1, 1))
                    connection.execute("INSERT INTO clips(id,user_id,original_name,mime,size,created_at,feed_id) VALUES (?,?,?,?,?,?,?)", ("b" * 32, users[1], "other.mp4", "video/mp4", 5, 1, 1))
                server.init()
                with server.db() as connection:
                    first = connection.execute("SELECT id,name FROM user_feeds WHERE user_id=? AND name='First owner''s trip'", (users[0],)).fetchone()
                    second = connection.execute("SELECT id FROM user_feeds WHERE user_id=? AND name='Feed 01'", (users[1],)).fetchone()
                    self.assertIsNotNone(first)
                    self.assertIsNotNone(second)
                    self.assertNotEqual(first["id"], second["id"])
                    self.assertEqual(connection.execute("SELECT feed_id FROM clips WHERE id=?", ("a" * 32,)).fetchone()["feed_id"], first["id"])
                    self.assertEqual(connection.execute("SELECT feed_id FROM clips WHERE id=?", ("b" * 32,)).fetchone()["feed_id"], second["id"])
                    self.assertEqual(connection.execute("SELECT destination FROM feed_details WHERE user_id=?", (users[0],)).fetchone()["destination"], "Osaka")
                    self.assertEqual(connection.execute("SELECT feed_id FROM feed_notes WHERE user_id=?", (users[1],)).fetchone()["feed_id"], second["id"])
            finally:
                server.DATA, server.UPLOADS, server.DB = original


if __name__ == "__main__":
    unittest.main()
