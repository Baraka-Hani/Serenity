"""Messaging integration tests use synthetic accounts and a disposable database."""
import http.cookiejar
import secrets
import time
import unittest
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import test_server as fixtures
import server


class MessagingFlow(unittest.TestCase):
    setUpClass = classmethod(fixtures.BackendFlow.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.BackendFlow.tearDownClass.__func__)
    setUp = fixtures.BackendFlow.setUp
    call = fixtures.BackendFlow.call

    def account(self, name):
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        status, result = self.call('/api/register', 'POST', {'name': name, 'email': f'{secrets.token_hex(6)}@example.test', 'password': 'tripPass123'}, client=client)
        self.assertEqual(status, 200)
        return client, result['user']

    def send(self, client, recipient, body='How do I get there?', **extra):
        return self.call('/api/messages/send', 'POST', {'recipient': recipient['public_id'], 'body': body, 'client_key': secrets.token_hex(16), **extra}, client=client)

    def test_private_persistent_two_way_and_read_positions(self):
        alice, a = self.account('DM Alice')
        bob, b = self.account('DM Bob')
        eve, e = self.account('DM Eve')
        anonymous = urllib.request.build_opener()
        for path in ('/api/messages/inbox', '/api/messages/users?q=dm', f"/api/messages/with/{a['public_id']}"):
            self.assertEqual(self.call(path, client=anonymous)[0], 401)
        self.assertEqual(self.send(anonymous, a)[0], 401)
        status, sent = self.send(alice, b, sender_id=e['id'])
        self.assertEqual(status, 201)
        self.assertTrue(sent['message']['is_mine'])
        thread_id, message_id = sent['thread']['id'], sent['message']['id']
        inbox = self.call('/api/messages/inbox', client=bob)[1]['threads']
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0]['unread_count'], 1)
        self.assertEqual(inbox[0]['participant']['public_id'], a['public_id'])
        self.assertNotIn('email', inbox[0]['participant'])
        self.assertNotIn('sender_id', inbox[0]['last_message'])
        self.assertEqual(self.call('/api/messages/inbox', client=eve)[1]['threads'], [])
        self.assertEqual(self.call(f"/api/messages/with/{a['public_id']}", client=eve)[1]['messages'], [])
        self.assertEqual(self.call(f'/api/messages/{thread_id}/read', 'POST', {'through': message_id}, client=eve)[0], 404)
        self.assertEqual(self.call(f'/api/messages/{thread_id}/block', 'POST', {'blocked': True}, client=eve)[0], 404)
        # New incoming messages after the read cursor must remain unread.
        _, second = self.send(alice, b, 'Is the walk difficult?')
        self.assertEqual(self.call(f'/api/messages/{thread_id}/read', 'POST', {'through': message_id}, client=bob)[0], 200)
        self.assertEqual(self.call('/api/messages/inbox', client=bob)[1]['threads'][0]['unread_count'], 1)
        self.assertEqual(self.call(f'/api/messages/{thread_id}/read', 'POST', {'through': second['message']['id']}, client=bob)[0], 200)
        self.assertEqual(self.call('/api/messages/inbox', client=bob)[1]['threads'][0]['unread_count'], 0)
        _, reply = self.send(bob, a, 'Take the coastal path from the station.')
        self.assertEqual(reply['thread']['id'], thread_id)
        self.assertEqual(self.call('/api/messages/inbox', client=alice)[1]['threads'][0]['unread_count'], 1)
        self.call('/api/logout', 'POST', client=bob)
        self.assertEqual(self.call(f"/api/messages/with/{a['public_id']}", client=bob)[0], 401)
        self.call('/api/login', 'POST', {'email': b['email'], 'password': 'tripPass123'}, client=bob)
        conversation = self.call(f"/api/messages/with/{a['public_id']}", client=bob)[1]
        self.assertEqual(len(conversation['messages']), 3)
        self.assertEqual(conversation['messages'][0]['body'], 'How do I get there?')
        self.assertFalse(conversation['messages'][0]['is_mine'])
        # Public APIs never expose the private question.
        self.assertNotIn('How do I get there?', str(self.call(f"/api/profiles/{a['public_id']}", client=anonymous)[1]))
        self.assertNotIn('How do I get there?', str(self.call('/api/posts', client=anonymous)[1]))
        with bob.open(self.base + '/api/messages/inbox') as response:
            self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_retry_is_atomic_and_idempotent(self):
        alice, a = self.account('Retry Alice')
        bob, b = self.account('Retry Bob')
        key = secrets.token_hex(16)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.send(alice, b, client_key=key), range(2)))
        self.assertEqual(sorted(item[0] for item in results), [200, 201])
        self.assertEqual(results[0][1]['message']['id'], results[1][1]['message']['id'])
        self.assertEqual(len(self.call(f"/api/messages/with/{a['public_id']}", client=bob)[1]['messages']), 1)
        self.assertEqual(self.send(alice, b, 'Different message', client_key=key)[0], 409)

    def test_context_must_be_public_and_owned_by_recipient(self):
        creator, c = self.account('Video Creator')
        visitor, v = self.account('Video Visitor')
        other, o = self.account('Another Creator')
        feed = next(iter(self.call('/api/feeds', client=creator)[1]['feeds']))
        _, clip = self.call('/api/clips', 'POST', b'video', 'video/mp4', {'X-Filename': 'coast.mp4', 'X-Feed': feed}, client=creator)
        _, published = self.call('/api/posts', 'POST', {'clip_id': clip['clip']['id'], 'destination': 'Lisbon', 'caption': 'Coastal path'}, client=creator)
        post_id = published['post']['id']
        self.assertEqual(self.send(visitor, o, post_id=post_id)[0], 404)
        _, sent = self.send(visitor, c, post_id=post_id)
        self.assertEqual(sent['message']['context']['destination'], 'Lisbon')
        thread_id = sent['thread']['id']
        self.call(f'/api/feeds/{feed}/visibility', 'PUT', {'visibility': 'private'}, client=creator)
        self.assertEqual(self.send(visitor, c, post_id=post_id)[0], 404)
        hidden = self.call(f"/api/messages/with/{c['public_id']}", client=visitor)[1]['messages'][0]
        self.assertTrue(hidden['has_context'])
        self.assertIsNone(hidden['context'])
        self.assertEqual(self.send(visitor, c, 'A regular message still works.')[0], 201)
        self.call(f'/api/feeds/{feed}/visibility', 'PUT', {'visibility': 'public'}, client=creator)
        self.call(f'/api/posts/{post_id}', 'DELETE', client=creator)
        deleted = self.call(f"/api/messages/with/{v['public_id']}", client=creator)[1]
        self.assertEqual(deleted['thread']['id'], thread_id)
        self.assertIsNone(deleted['messages'][0]['context'])
        self.assertEqual(len(deleted['messages']), 2)

    def test_block_prevents_both_sides_sending_and_is_reversible(self):
        alice, a = self.account('Block Alice')
        bob, b = self.account('Block Bob')
        _, sent = self.send(alice, b)
        route = f"/api/messages/{sent['thread']['id']}/block"
        self.assertTrue(self.call(route, 'POST', {'blocked': True}, client=bob)[1]['thread']['blocked'])
        self.assertEqual(self.send(alice, b)[0], 403)
        self.assertEqual(self.send(bob, a)[0], 403)
        self.assertEqual(self.call(route, 'POST', {'blocked': 'false'}, client=bob)[0], 400)
        self.call(route, 'POST', {'blocked': False}, client=bob)
        self.assertEqual(self.send(alice, b)[0], 201)

    def test_validation_pagination_and_rate_limits(self):
        alice, a = self.account('Paging Alice')
        bob, b = self.account('Paging Bob')
        for body in ('', '  ', 'x' * 2001, ['invalid']):
            self.assertEqual(self.send(alice, b, body)[0], 400)
        self.assertEqual(self.send(alice, a)[0], 400)
        self.assertEqual(self.send(alice, b, post_id=123)[0], 400)
        self.assertEqual(self.send(alice, b, '🌊' * 2000)[0], 201)
        _, sent = self.send(alice, b)
        thread_id = sent['thread']['id']
        with server.db() as connection:
            for index in range(55):
                result = connection.execute('INSERT INTO dm_messages(thread_id,sender_id,body,client_key,created_at) VALUES (?,?,?,?,?)',
                                            (thread_id, a['id'], f'Message {index}', secrets.token_hex(16), int(time.time())))
            connection.execute('UPDATE dm_threads SET last_message_id=? WHERE id=?', (result.lastrowid, thread_id))
        route = f"/api/messages/with/{a['public_id']}"
        latest = self.call(route, client=bob)[1]
        self.assertEqual(len(latest['messages']), 40)
        self.assertTrue(latest['has_more'])
        older = self.call(route + f"?before={latest['messages'][0]['id']}", client=bob)[1]
        self.assertEqual(len(older['messages']), 17)
        self.assertFalse(older['has_more'])
        after = self.call(route + f"?after={older['messages'][-1]['id']}", client=bob)[1]
        self.assertEqual(after['messages'], latest['messages'])
        self.assertEqual(self.call(route + '?before=-1', client=bob)[0], 400)
        self.assertEqual(self.send(alice, b)[0], 429)

    def test_people_search_is_authenticated_and_never_exposes_email(self):
        alice, a = self.account('Find Unique Alice')
        bob, b = self.account('Find Unique Bob')
        prefix = b['username'][:15]
        found = self.call('/api/messages/users?q=' + prefix, client=alice)[1]['users']
        self.assertIn(b['public_id'], [item['public_id'] for item in found])
        self.assertNotIn(a['public_id'], [item['public_id'] for item in found])
        self.assertTrue(all(set(item) == {'name', 'username', 'public_id'} for item in found))
        self.assertEqual(self.call('/api/messages/users?q=%25%25', client=alice)[0], 400)
        self.assertEqual(self.call('/api/messages/users?q=a', client=alice)[0], 400)


if __name__ == '__main__':
    unittest.main()
